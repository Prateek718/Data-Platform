"""T2.6 — normalize_batch orchestrator + golden end-to-end (tests first, red checkpoint).

End-to-end over real Stage-0 flagship fixtures (via the Stage 1 adapter): R2-FMT-01 ->
R2-DEDUP-01 -> R2-TYPE-01/R2-DATE-01, with full lineage. Asserts the locked decisions on real
data: row-atomic dedupe (Q3), Decimal/int typing (Q6), identifiers str (Q4), FY/month strings
(Q2), NA -> null (R2-FMT-01), MISSING_GRAIN_KEY quarantine. Every invariant is a guarding test.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from data_platform.ingest.adapters.base import SourcePayload
from data_platform.ingest.adapters.flagship import FlagshipAdapter
from data_platform.ingest.landing import RawLandingBatch, build_batch
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.models import (
    NormalizationQuarantineReason,
    NormalizedBatch,
)
from data_platform.normalize.pipeline import normalize_batch

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FETCHED = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
PERSONDAYS = "Persondays_of_Central_Liability_so_far"


def _flagship_batch(fixture: str) -> RawLandingBatch:
    env = json.loads((FIXTURES / fixture).read_text())
    payload = SourcePayload(
        resource_id=FLAGSHIP_RESOURCE_ID,
        fetched_at=FETCHED,
        source_as_of=datetime.fromisoformat(env["updated_date"]),
        raw=env,
    )
    return FlagshipAdapter().parse(payload)


def test_golden_duplicate_snapshot_collapses_and_types() -> None:
    out = normalize_batch(_flagship_batch("flagship/duplicate_snapshot.json"))
    assert isinstance(out, NormalizedBatch)

    # provenance carried from landing
    assert out.source_id == SRC_FLAGSHIP
    assert out.source_grain == "district+monthly"

    # R2-DEDUP-01: two snapshot rows (same key, same as_of) collapse to the last-in-file row.
    assert len(out.records) == 1
    rec = out.records[0]
    assert rec.row_index == 1
    assert out.dedupe.duplicates_collapsed == 1
    assert out.dedupe.collapsed_row_indexes == [0]
    assert out.dedupe.tie_break_rule_id == "R2-DEDUP-TB-01"
    assert out.quarantined == []

    # R2-TYPE-01 / R2-DATE-01 / R2-FMT-01 on the survivor (row 1 -> persondays 34102)
    assert rec.cells[PERSONDAYS] == 34102
    assert isinstance(rec.cells[PERSONDAYS], int)
    assert rec.cells["Total_Exp"] == Decimal("165.53913")
    assert isinstance(rec.cells["Total_Exp"], Decimal)
    assert rec.cells["Average_Wage_rate_per_day_per_person"] == Decimal("397.314743793074")
    assert rec.cells["state_code"] == "10"  # identifier stays str (Q4)
    assert isinstance(rec.cells["state_code"], str)
    assert rec.cells["fin_year"] == "2022-23"  # Q2
    assert rec.cells["month"] == "01"  # Q2
    assert rec.cells["Remarks"] is None  # NA -> null

    # lineage notes (normalization_rules, §4)
    pc = rec.normalization.per_column
    assert "R2-DATE-01:2022-2023→2022-23" in pc["fin_year"]
    assert "R2-DATE-01:Jan→01" in pc["month"]
    assert "R2-FMT-01:NA→null" in pc["Remarks"]
    assert pc["Total_Exp"] == ["R2-TYPE-01:str→decimal"]
    assert pc[PERSONDAYS] == ["R2-TYPE-01:str→int"]


def test_goa_fixture_no_dedupe_all_typed() -> None:
    out = normalize_batch(_flagship_batch("flagship/goa_2022_2023.json"))

    assert len(out.records) == 4  # 4 distinct (district, month) rows — nothing collapses
    assert out.dedupe.duplicates_collapsed == 0
    assert out.dedupe.collapsed_row_indexes == []
    assert out.quarantined == []

    by_key = {(r.cells["district_name"], r.cells["month"]): r for r in out.records}
    north_march = by_key[("NORTH GOA", "03")]
    assert north_march.cells[PERSONDAYS] == 42253
    assert north_march.cells["Total_Exp"] == Decimal("196.74055")
    assert north_march.cells["fin_year"] == "2022-23"
    assert north_march.cells["Remarks"] is None
    assert by_key[("SOUTH GOA", "04")].cells[PERSONDAYS] == 3300

    # a column outside the type spec is FMT-cleaned but left as a string (deferred typing)
    assert isinstance(north_march.cells["Wages"], str)


def test_unconfigured_source_raises() -> None:
    batch = build_batch(
        source_id="SRC_UNKNOWN",
        resource_id="x",
        ingested_at=FETCHED,
        source_as_of=None,
        schema_version="sv",
        source_grain="g",
        column_names=["a"],
        rows=[{"a": "1"}],
    )
    with pytest.raises(ValueError, match="Stage 2 config"):
        normalize_batch(batch)


def test_all_null_grain_key_row_quarantined_others_survive() -> None:
    cols = ["state_code", "district_code", "fin_year", "month", "Total_Exp"]
    rows = [
        {"Total_Exp": "100"},  # all grain-key columns absent -> null -> MISSING_GRAIN_KEY
        {
            "state_code": "10",
            "district_code": "1001",
            "fin_year": "2022-2023",
            "month": "Jan",
            "Total_Exp": "200",
        },
    ]
    batch = build_batch(
        source_id=SRC_FLAGSHIP,
        resource_id=FLAGSHIP_RESOURCE_ID,
        ingested_at=FETCHED,
        source_as_of=None,
        schema_version="sv",
        source_grain="district+monthly",
        column_names=cols,
        rows=rows,
    )
    out = normalize_batch(batch)

    assert [r.row_index for r in out.records] == [1]
    assert out.records[0].cells["Total_Exp"] == Decimal("200")
    assert len(out.quarantined) == 1
    assert out.quarantined[0].row_index == 0
    assert out.quarantined[0].reason is NormalizationQuarantineReason.MISSING_GRAIN_KEY
