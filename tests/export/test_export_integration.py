"""End-to-end export over the real archive — the deterministic-artifact proof.

Builds the full series, writes the deliverables, and asserts: the documented row counts
(state 4,216 / national 148); the CSV↔lineage join on fact_id; byte-identical repeated runs
(CSV + JSONL + Parquet); the district-annual decomposition (Σ district = state spine, structural-gap
cells checked not skipped); and the headline reconciliation facts (4 genuine cross-publisher
disagreements, 3 unadjudicated national persondays, 472 edition-superseded, null≠0).

Skips when the gitignored archive snapshot is absent; parquet assertions skip if pyarrow is absent.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from data_platform.export.build import ExportBundle, build_export
from data_platform.export.records import DISTRICT_COLUMNS, NATIONAL_COLUMNS, STATE_COLUMNS
from data_platform.export.write import write_all
from data_platform.harmonize.models import CoverageStatus
from data_platform.harmonize.series import Confidence, SeriesFact
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID
from data_platform.resolve.models import GeoLevel

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
_Written = tuple[Path, Path, dict[str, int]]

pytestmark = pytest.mark.skipif(
    not (ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json").exists(),
    reason="local archive snapshot not present",
)

_ADDITIVE = {
    "households_employed",
    "households_completed_100_days",
    "active_workers",
    "persondays_generated",
    "wages_expenditure",
    "material_skilled_expenditure",
    "admin_expenditure",
    "total_expenditure",
}


@pytest.fixture(scope="module")
def bundle() -> ExportBundle:
    return build_export(ARCHIVE)


@pytest.fixture(scope="module")
def written(bundle: ExportBundle, tmp_path_factory: pytest.TempPathFactory) -> _Written:
    d1 = tmp_path_factory.mktemp("dist_a")
    d2 = tmp_path_factory.mktemp("dist_b")
    counts = write_all(d1, bundle)
    write_all(d2, bundle)
    return d1, d2, counts


def _name_to_code(bundle: ExportBundle) -> dict[str, str]:
    return {name: code for code, name in bundle.state_names.items()}


# --- documented row counts ----------------------------------------------------------------------


def test_state_spine_matches_documented_shape(bundle: ExportBundle) -> None:
    metrics = {f.key.metric for f in bundle.state_facts}
    years = {f.key.fin_year for f in bundle.state_facts}
    states = {f.key.state_code for f in bundle.state_facts}
    assert len(bundle.state_facts) == 4216
    assert metrics == _ADDITIVE
    assert min(years) == "2010-11" and max(years) == "2026-27"
    assert len(states) == 35


def test_national_spine_matches_documented_shape(bundle: ExportBundle) -> None:
    assert len(bundle.national_facts) == 148
    years = sorted(f.key.fin_year for f in bundle.national_facts)
    assert years[0] == "2006-07" and years[-1] == "2026-27"
    for f in bundle.national_facts:
        assert f.key.geo_level is GeoLevel.NATIONAL
        assert f.key.state_code is None and f.key.district_code is None
    exp_years = sorted(
        f.key.fin_year for f in bundle.national_facts if f.key.metric == "wages_expenditure"
    )
    assert exp_years[0] == "2008-09"  # national financial sources begin 2008-09


def test_district_drilldown_has_annual_and_native_monthly_wage(bundle: ExportBundle) -> None:
    annual = [f for f in bundle.district_facts if f.key.month is None]
    monthly = [f for f in bundle.district_facts if f.key.month is not None]
    assert {f.key.metric for f in annual} == _ADDITIVE  # 8 additive metrics, district-annual
    assert {f.key.metric for f in monthly} == {"avg_wage_rate_per_day"}  # only the rate is monthly
    assert len(annual) == 51536 and len(monthly) == 69188
    # the rate is NOT forced into the state spine (it does not sum to a state annual)
    assert "avg_wage_rate_per_day" not in {f.key.metric for f in bundle.state_facts}


# --- files, join, determinism -------------------------------------------------------------------


def test_csv_row_counts_match_assembled_series(written: _Written) -> None:
    d1, _d2, counts = written
    assert counts["state_annual_series"] == 4216
    assert counts["national_annual_series"] == 148
    assert counts["district_flagship"] == 120724
    assert counts["lineage"] == 4216 + 148 + 120724

    def data_rows(path: Path) -> int:
        return len(path.read_text().splitlines()) - 1  # minus header

    assert data_rows(d1 / "state_annual_series.csv") == 4216
    assert data_rows(d1 / "national_annual_series.csv") == 148
    assert data_rows(d1 / "district_flagship.csv") == 120724


def test_every_fact_id_joins_csv_to_lineage_exactly_once(written: _Written) -> None:
    d1, _d2, _counts = written
    lineage_ids = [
        json.loads(line)["fact_id"] for line in (d1 / "lineage.jsonl").read_text().splitlines()
    ]
    assert len(lineage_ids) == len(set(lineage_ids)) == 125088  # unique, one per exported fact

    csv_ids: set[str] = set()
    for name, columns in (
        ("state_annual_series.csv", STATE_COLUMNS),
        ("national_annual_series.csv", NATIONAL_COLUMNS),
        ("district_flagship.csv", DISTRICT_COLUMNS),
    ):
        idx = columns.index("fact_id")
        rows = (d1 / name).read_text().splitlines()[1:]
        csv_ids |= {r.split(",")[idx] for r in rows}
    assert csv_ids == set(lineage_ids)  # exact CSV↔lineage correspondence


def test_repeated_runs_are_byte_identical(written: _Written) -> None:
    d1, d2, _counts = written
    names = [
        "state_annual_series.csv",
        "national_annual_series.csv",
        "district_flagship.csv",
        "lineage.jsonl",
    ]
    if (d1 / "state_annual_series.parquet").exists():  # pyarrow installed
        names += [
            "state_annual_series.parquet",
            "national_annual_series.parquet",
            "district_flagship.parquet",
        ]
    for name in names:
        assert (d1 / name).read_bytes() == (d2 / name).read_bytes(), f"non-deterministic: {name}"


# --- decomposition (district-annual sums to the state spine) ------------------------------------


def test_district_annual_decomposes_the_state_spine(bundle: ExportBundle) -> None:
    dsum: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal(0))
    for f in bundle.district_facts:
        if f.key.month is None and f.value is not None:
            dsum[(f.key.state_code or "", f.key.fin_year, f.key.metric)] += f.value

    checked = 0
    structural_gap = 0
    for f in bundle.state_facts:
        if f.key.fin_year < "2018" or f.key.metric not in _ADDITIVE:
            continue
        flagship = next(s for s in f.reconciliation.sources_seen if s.source_id == "SRC_FLAGSHIP")
        # every 2018+ additive cell exposes its coverage descriptor (never silently absent)
        assert flagship.aggregate_coverage is not None
        # single-source flagship is always adjudicated: no 2018+ additive cell is null-skipped
        assert f.value is not None
        checked += 1
        got = dsum[(f.key.state_code or "", f.key.fin_year, f.key.metric)]
        assert abs(float(f.value) - float(got)) <= 1.0, f"{f.key} state={f.value} Σdistrict={got}"
        if flagship.aggregate_coverage.status is CoverageStatus.STRUCTURAL_GAP:
            structural_gap += 1
    assert checked == 2432
    assert structural_gap == 632  # structurally-incomplete cells still decompose exactly


# --- headline reconciliation facts (verified, at scope) -----------------------------------------


def test_exactly_four_genuine_cross_publisher_disagreements(bundle: ExportBundle) -> None:
    name = dict(bundle.state_names)
    flagged = [
        (name.get(f.key.state_code or "", f.key.state_code), f.key.fin_year, f.key.metric)
        for f in bundle.state_facts
        if f.key.fin_year < "2018" and f.confidence is Confidence.FLAGGED_DISAGREEMENT
    ]
    assert len(flagged) == 4
    assert {m for _s, _y, m in flagged} == {"households_employed"}
    assert set(flagged) == {
        ("Bihar", "2015-16", "households_employed"),
        ("Mizoram", "2013-14", "households_employed"),
        ("Telangana", "2014-15", "households_employed"),
        ("Andaman And Nicobar Islands", "2014-15", "households_employed"),
    }
    # the documented divergence percentages (DATA_DICTIONARY §8 / README) are pinned here
    pct: dict[tuple[str | None, str], Decimal] = {}
    for f in bundle.state_facts:
        if f.key.fin_year >= "2018" or f.confidence is not Confidence.FLAGGED_DISAGREEMENT:
            continue
        disagreement = f.reconciliation.disagreement
        assert disagreement is not None
        cell = (name.get(f.key.state_code or "", f.key.state_code), f.key.fin_year)
        pct[cell] = disagreement.pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    assert pct == {
        ("Bihar", "2015-16"): Decimal("4.2"),
        ("Mizoram", "2013-14"): Decimal("3.1"),
        ("Telangana", "2014-15"): Decimal("1.3"),
        ("Andaman And Nicobar Islands", "2014-15"): Decimal("7.7"),
    }
    for f in bundle.state_facts:
        if f.key.fin_year < "2018" and f.confidence is Confidence.FLAGGED_DISAGREEMENT:
            publishers = {s.source_id for s in f.reconciliation.sources_seen}
            assert {"SRC_MOSPI", "SRC_RS"} <= publishers  # genuinely two independent publishers


def test_three_national_persondays_cells_unadjudicated(bundle: ExportBundle) -> None:
    unadjudicated = [
        f
        for f in bundle.national_facts
        if f.key.metric == "persondays_generated" and f.value is None
    ]
    assert {f.key.fin_year for f in unadjudicated} == {"2012-13", "2013-14", "2014-15"}
    for f in unadjudicated:
        assert f.reconciliation.resolution_rule_id == "R4-REC-09"  # single-publisher divergence
        assert f.confidence is Confidence.SINGLE_PUBLISHER_DIVERGENCE


def test_edition_supersession_labels_472_state_cells(bundle: ExportBundle) -> None:
    superseded = [f for f in bundle.state_facts if f.confidence is Confidence.EDITION_SUPERSEDED]
    assert len(superseded) == 472


def test_active_workers_has_no_pre_2018_value(bundle: ExportBundle) -> None:
    for facts in (bundle.state_facts, bundle.national_facts):
        assert not [
            f for f in facts if f.key.metric == "active_workers" and f.key.fin_year < "2018"
        ]


def test_goa_2022_23_persondays_spot_value(bundle: ExportBundle) -> None:
    code = _name_to_code(bundle)["Goa"]
    goa: list[SeriesFact] = [
        f
        for f in bundle.state_facts
        if f.key.state_code == code
        and f.key.fin_year == "2022-23"
        and f.key.metric == "persondays_generated"
    ]
    assert len(goa) == 1
    assert goa[0].value == Decimal("94004")  # FY-final rollup, not the 6.31× naive monthly sum


def test_unadjudicated_national_cells_export_null_not_zero(written: _Written) -> None:
    d1, _d2, _counts = written
    value_idx = NATIONAL_COLUMNS.index("value")
    fy_idx = NATIONAL_COLUMNS.index("financial_year")
    metric_idx = NATIONAL_COLUMNS.index("metric")
    rows = (d1 / "national_annual_series.csv").read_text().splitlines()[1:]
    persondays_2013 = [
        r.split(",")
        for r in rows
        if r.split(",")[metric_idx] == "persondays_generated" and r.split(",")[fy_idx] == "2013-14"
    ]
    assert len(persondays_2013) == 1
    assert persondays_2013[0][value_idx] == ""  # empty (null), never "0"
