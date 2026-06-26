"""T1.2 — source adapters (tests written first, per strict TDD).

Behavioral tests (RED until ``parse`` is implemented):
  * flagship keeps all 36 source columns verbatim; duplicate snapshot rows survive un-deduped;
  * the two RS resources yield ONE batch each (own ``source_as_of``), never merged;
  * the synthetic RS ``Total`` row is quarantined as ``SYNTHETIC_TOTAL_ROW`` — kept, not dropped.

Architectural guards (GREEN by construction — invariants, not behavior):
  * a brand-new source satisfies the contract via the ``SourceAdapter`` ABC alone,
    without subclassing or importing flagship/RS;
  * the ``adapters`` package imports no network library and does no file I/O —
    ``transport.py`` is the only impure module.

All fixtures are trimmed real Stage-0 payloads under ``tests/fixtures/`` — hermetic, offline.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import data_platform.ingest.adapters as adapters_pkg
import data_platform.ingest.transport as transport_mod
from data_platform.ingest.adapters.base import SourceAdapter, SourcePayload
from data_platform.ingest.adapters.flagship import FlagshipAdapter
from data_platform.ingest.adapters.rajya_sabha import RajyaSabhaAdapter
from data_platform.ingest.landing import ParseFailureReason, RawLandingBatch, build_batch
from data_platform.ingest.registry import (
    FLAGSHIP_RESOURCE_ID,
    RS_RESOURCE_IDS,
    SRC_FLAGSHIP,
    SRC_RS,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FETCHED = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
RS_TABLE1_ID, RS_TABLE2_ID = RS_RESOURCE_IDS

# The flagship verbatim contract: all 36 columns, in source order (Stage 0, verbatim).
# NB: docs/notes/sources.md prose says "all 35" but its own list — and the live payload —
# carry 36. The real number is 36; the doc miscounted by one. This list is the contract.
FLAGSHIP_COLUMNS = [
    "fin_year",
    "month",
    "state_code",
    "state_name",
    "district_code",
    "district_name",
    "Approved_Labour_Budget",
    "Average_Wage_rate_per_day_per_person",
    "Average_days_of_employment_provided_per_Household",
    "Differently_abled_persons_worked",
    "Material_and_skilled_Wages",
    "Number_of_Completed_Works",
    "Number_of_GPs_with_NIL_exp",
    "Number_of_Ongoing_Works",
    "Persondays_of_Central_Liability_so_far",
    "SC_persondays",
    "SC_workers_against_active_workers",
    "ST_persondays",
    "ST_workers_against_active_workers",
    "Total_Adm_Expenditure",
    "Total_Exp",
    "Total_Households_Worked",
    "Total_Individuals_Worked",
    "Total_No_of_Active_Job_Cards",
    "Total_No_of_Active_Workers",
    "Total_No_of_HHs_completed_100_Days_of_Wage_Employment",
    "Total_No_of_JobCards_issued",
    "Total_No_of_Workers",
    "Total_No_of_Works_Takenup",
    "Wages",
    "Women_Persondays",
    "percent_of_Category_B_Works",
    "percent_of_Expenditure_on_Agriculture_Allied_Works",
    "percent_of_NRM_Expenditure",
    "percentage_payments_gererated_within_15_days",
    "Remarks",
]


def _payload(fixture: str, resource_id: str) -> SourcePayload:
    """Build a SourcePayload from a fixture, mirroring what transport will do offline.

    Test-side file reads are fine (tests are not adapters). ``source_as_of`` is pulled
    from the ENVELOPE-level ``updated_date`` — the single batch-wide value Stage 0 found.
    """
    env = json.loads((FIXTURES / fixture).read_text())
    return SourcePayload(
        resource_id=resource_id,
        fetched_at=FETCHED,
        source_as_of=datetime.fromisoformat(env["updated_date"]),
        raw=env,
    )


# --------------------------------------------------------------------------------------
# 1. ADAPTER SEAM — a brand-new source needs only the ABC (no flagship/RS involvement)
# --------------------------------------------------------------------------------------
class _LedgerAdapter(SourceAdapter):
    """A wholly independent fake source, defined inline, with its OWN payload shape.

    Implements :class:`SourceAdapter` directly. It does not subclass FlagshipAdapter or
    RajyaSabhaAdapter and reuses none of their parsing — only the shared ``build_batch``
    primitive. Existence-and-correctness of this class IS the source-agnostic proof.
    """

    source_id = "SRC_FAKE_LEDGER"
    resource_ids = ["ledger-001"]
    source_grain = "place+annual"

    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        body = payload.raw  # our own made-up shape: {"cols": [...], "rows": [{...}, ...]}
        return build_batch(
            source_id=self.source_id,
            resource_id=payload.resource_id,
            ingested_at=payload.fetched_at,
            source_as_of=payload.source_as_of,
            schema_version="fake-sv1",
            source_grain=self.source_grain,
            column_names=list(body["cols"]),
            rows=body["rows"],
        )


def test_new_source_satisfies_contract_without_touching_existing_adapters() -> None:
    payload = SourcePayload(
        resource_id="ledger-001",
        fetched_at=FETCHED,
        source_as_of=datetime(2025, 1, 1, tzinfo=UTC),
        raw={
            "cols": ["place", "widgets"],
            "rows": [
                {"place": "Zembla", "widgets": "7"},
                {"place": "Ruritania", "widgets": "NA"},
            ],
        },
    )

    adapter = _LedgerAdapter()
    batch = adapter.parse(payload)

    assert isinstance(batch, RawLandingBatch)
    assert batch.source_id == "SRC_FAKE_LEDGER"
    assert batch.source_grain == "place+annual"
    assert batch.source_as_of == datetime(2025, 1, 1, tzinfo=UTC)
    assert [r.raw["place"] for r in batch.records] == ["Zembla", "Ruritania"]
    assert batch.records[1].raw["widgets"] == "NA"  # verbatim, not coerced to null

    # The seam claim, made explicit and WITHOUT importing flagship/rajya_sabha: a new
    # source is a new SourceAdapter, not a subclass of an existing adapter.
    assert isinstance(adapter, SourceAdapter)
    mro_names = {cls.__name__ for cls in type(adapter).__mro__}
    assert "FlagshipAdapter" not in mro_names
    assert "RajyaSabhaAdapter" not in mro_names


# --------------------------------------------------------------------------------------
# 2. PURITY / NO-I/O — adapters are pure; transport.py is the only impure module
# --------------------------------------------------------------------------------------
ADAPTERS_DIR = Path(adapters_pkg.__file__).resolve().parent
TRANSPORT_FILE = Path(transport_mod.__file__).resolve()
FORBIDDEN_NET = {"httpx", "requests", "urllib", "urllib3", "aiohttp", "socket", "http"}
# pathlib/file method names that mean a module is touching disk. ``.open`` covers the
# ``Path(...).open(...)`` form; the builtin ``open()`` (an ast.Name call) is caught
# separately. Reads AND writes are both file I/O — adapters do neither.
FORBIDDEN_IO_ATTRS = {"read_text", "read_bytes", "write_text", "write_bytes", "open"}


def _top_imports(pyfile: Path) -> set[str]:
    """Top-level package names imported by a module (``import a.b`` -> ``a``)."""
    tree = ast.parse(pyfile.read_text())
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


def _imported_dotted(pyfile: Path) -> set[str]:
    """Full dotted module names referenced by import statements."""
    tree = ast.parse(pyfile.read_text())
    dotted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dotted.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            dotted.add(node.module)
    return dotted


def _file_io_offenders(pyfile: Path) -> set[str]:
    """Tokens proving a module touches disk: the builtin ``open()``, any pathlib
    read/write/open method (``Path(...).read_text()``, ``p.read_bytes()``,
    ``p.open(...)``, …), or a ``pathlib`` import. Adapters must be pure in-memory
    transforms, so any of these in an adapter file is a bug.
    """
    tree = ast.parse(pyfile.read_text())
    offenders: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ):
            offenders.add("open()")  # builtin open(...)
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_IO_ATTRS:
            offenders.add(f".{node.attr}")  # e.g. Path(...).read_text / p.open(...)
    if "pathlib" in _top_imports(pyfile):
        offenders.add("import pathlib")
    return offenders


def _adapter_files() -> list[Path]:
    return sorted(ADAPTERS_DIR.glob("*.py"))


def test_adapters_import_no_network_library() -> None:
    for pyfile in _adapter_files():
        leaked = _top_imports(pyfile) & FORBIDDEN_NET
        assert not leaked, f"{pyfile.name} imports a network library: {sorted(leaked)}"


def test_adapters_do_no_file_io_and_never_reach_into_transport() -> None:
    for pyfile in _adapter_files():
        io = _file_io_offenders(pyfile)
        assert not io, f"{pyfile.name} does file I/O ({sorted(io)}); adapters are pure in-memory"
        reaches = any("transport" in mod for mod in _imported_dotted(pyfile))
        assert not reaches, f"{pyfile.name} imports transport — adapters must stay pure"


def test_transport_is_the_single_impure_module() -> None:
    # The contrast that makes the purity claim meaningful: httpx lives in transport.py
    # (allowed there) and in no adapter file.
    assert "httpx" in _top_imports(TRANSPORT_FILE)


# --------------------------------------------------------------------------------------
# 3. RS TWO-RESOURCE — one batch per resource_id, own as-of, never merged
# --------------------------------------------------------------------------------------
def test_two_rs_resources_yield_one_batch_each_never_merged() -> None:
    b1 = RajyaSabhaAdapter(RS_TABLE1_ID).parse(
        _payload("rajya_sabha/table1_cea6ee41.json", RS_TABLE1_ID)
    )
    b2 = RajyaSabhaAdapter(RS_TABLE2_ID).parse(
        _payload("rajya_sabha/table2_e289a8fe.json", RS_TABLE2_ID)
    )

    # two distinct batches, each tagged with its OWN resource_id and as-of date
    assert b1.resource_id == RS_TABLE1_ID
    assert b2.resource_id == RS_TABLE2_ID
    assert b1.resource_id != b2.resource_id
    assert b1.source_as_of == datetime(2025, 3, 7, 5, 53, 39, tzinfo=UTC)
    assert b2.source_as_of == datetime(2024, 11, 2, 17, 56, 25, tzinfo=UTC)
    assert b1.source_as_of != b2.source_as_of  # the as-of dates are NOT collapsed together

    # same source + grain, but emphatically two separate batches (never merged into one)
    assert b1.source_id == b2.source_id == SRC_RS
    assert b1.source_grain == b2.source_grain == "state+annual"
    assert b1 is not b2


# --------------------------------------------------------------------------------------
# 4. SYNTHETIC TOTAL ROW — quarantined (kept), not dropped, not passed through
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("fixture", "resource_id", "label_col"),
    [
        ("rajya_sabha/table1_cea6ee41.json", RS_TABLE1_ID, "state_ut_wise"),
        ("rajya_sabha/table2_e289a8fe.json", RS_TABLE2_ID, "state_uts"),
    ],
)
def test_rs_total_row_quarantined_not_dropped_not_passed_through(
    fixture: str, resource_id: str, label_col: str
) -> None:
    batch = RajyaSabhaAdapter(resource_id).parse(_payload(fixture, resource_id))

    # the 4 real states pass through as records; 'Total' is NOT among them (not passed through)
    labels = [r.raw[label_col] for r in batch.records]
    assert "Total" not in labels
    assert {"Andhra Pradesh", "Arunachal Pradesh", "Assam", "Goa"} <= set(labels)
    assert len(batch.records) == 4

    # 'Total' is quarantined (not dropped), with the existing typed reason, preserved as-seen
    total_failures = [
        f for f in batch.parse_failures if f.reason is ParseFailureReason.SYNTHETIC_TOTAL_ROW
    ]
    assert len(total_failures) == 1
    assert total_failures[0].raw[label_col] == "Total"


# --------------------------------------------------------------------------------------
# 5. FLAGSHIP VERBATIM — all 36 columns kept; duplicate snapshot rows preserved
# --------------------------------------------------------------------------------------
def test_flagship_preserves_all_36_columns_verbatim() -> None:
    batch = FlagshipAdapter().parse(_payload("flagship/goa_2022_2023.json", FLAGSHIP_RESOURCE_ID))

    assert batch.source_id == SRC_FLAGSHIP
    assert batch.source_grain == "district+monthly"
    assert batch.resource_id == FLAGSHIP_RESOURCE_ID

    # all 36 source columns observed at batch level (set), and verbatim per record (order)
    assert len(FLAGSHIP_COLUMNS) == 36
    assert set(batch.column_names) == set(FLAGSHIP_COLUMNS)

    march = next(
        r
        for r in batch.records
        if r.raw["district_name"] == "NORTH GOA" and r.raw["month"] == "March"
    )
    assert list(march.raw.keys()) == FLAGSHIP_COLUMNS  # every column, in source order
    # values kept exactly as the flagship emits them — all strings, "NA" not nulled
    assert march.raw["Persondays_of_Central_Liability_so_far"] == "42253"  # str, not int 42253
    assert march.raw["Remarks"] == "NA"  # preserved verbatim, not coerced to null


def test_flagship_preserves_duplicate_snapshot_rows_not_deduped() -> None:
    batch = FlagshipAdapter().parse(
        _payload("flagship/duplicate_snapshot.json", FLAGSHIP_RESOURCE_ID)
    )

    # two rows share (district_name, month) = (NORTH GOA, Jan); BOTH survive verbatim
    assert batch.parse_failures == []
    assert len(batch.records) == 2
    keys = [(r.raw["district_name"], r.raw["month"]) for r in batch.records]
    assert keys == [("NORTH GOA", "Jan"), ("NORTH GOA", "Jan")]
    # the two snapshots carry different person-day values; neither is dropped (dedupe is Stage 2)
    persondays = {r.raw["Persondays_of_Central_Liability_so_far"] for r in batch.records}
    assert persondays == {"34679", "34102"}
