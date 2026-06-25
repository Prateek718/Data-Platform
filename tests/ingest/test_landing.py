"""T1.1 — raw landing record model (tests written first, per strict TDD).

Covers the approved-plan cases:
1. well-formed row parses, provenance is BATCH-level (not on the record);
2. "NA" preserved verbatim (no coercion);
3. absent declared column -> None (null, never 0);
4. malformed row -> ParseFailure(malformed_row), batch keeps the good rows;
plus: empty mapping -> empty_row; quarantine predicate -> synthetic_total_row; records frozen.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from data_platform.ingest.landing import (
    ParseFailureReason,
    RawLandingBatch,
    RawLandingRecord,
    build_batch,
)

INGESTED = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
AS_OF = datetime(2026, 6, 22, 17, 0, tzinfo=UTC)


def _batch(rows: list[Any], column_names: list[str], **overrides: Any) -> RawLandingBatch:
    kwargs: dict[str, Any] = {
        "source_id": "SRC_FLAGSHIP",
        "resource_id": "ee03643a-ee4c-48c2-ac30-9f2ff26ab722",
        "ingested_at": INGESTED,
        "source_as_of": AS_OF,
        "schema_version": "sv1",
        "source_grain": "district+monthly",
        "column_names": column_names,
        "rows": rows,
    }
    kwargs.update(overrides)
    return build_batch(**kwargs)


def test_wellformed_row_parses_with_batch_level_breadcrumbs() -> None:
    rows = [
        {
            "state_name": "GOA",
            "month": "Apr",
            "Persondays_of_Central_Liability_so_far": "2523",
        }
    ]
    cols = ["state_name", "month", "Persondays_of_Central_Liability_so_far"]

    batch = _batch(rows, cols)

    assert isinstance(batch, RawLandingBatch)
    assert len(batch.records) == 1
    assert batch.parse_failures == []

    rec = batch.records[0]
    assert isinstance(rec, RawLandingRecord)
    assert rec.row_index == 0
    assert rec.raw == rows[0]  # verbatim, unchanged

    # provenance lives on the BATCH, never denormalized onto the record
    assert batch.source_id == "SRC_FLAGSHIP"
    assert batch.resource_id == "ee03643a-ee4c-48c2-ac30-9f2ff26ab722"
    assert batch.ingested_at == INGESTED
    assert batch.source_as_of == AS_OF
    assert batch.schema_version == "sv1"
    assert batch.source_grain == "district+monthly"
    assert not hasattr(rec, "source_id")
    assert not hasattr(rec, "ingested_at")


def test_na_string_preserved_verbatim_not_coerced() -> None:
    rows = [{"Remarks": "NA", "Total_Exp": "3884.10"}]
    cols = ["Remarks", "Total_Exp"]

    rec = _batch(rows, cols).records[0]

    assert rec.raw["Remarks"] == "NA"  # not None, not ""
    assert rec.raw["Total_Exp"] == "3884.10"  # still a string, not float 3884.1


def test_absent_declared_column_becomes_null_never_zero() -> None:
    rows = [{"state_name": "GOA"}]  # 'month' column absent from this row
    cols = ["state_name", "month"]

    rec = _batch(rows, cols).records[0]

    assert rec.raw["month"] is None  # null...
    assert rec.raw["month"] != 0  # ...explicitly not zero
    assert rec.raw["month"] != "0"


def test_malformed_row_quarantined_not_dropped_batch_survives() -> None:
    rows = [
        {"state_name": "GOA", "month": "Apr"},  # good
        ["this", "is", "not", "a", "mapping"],  # malformed
        {"state_name": "BIHAR", "month": "May"},  # good
    ]
    cols = ["state_name", "month"]

    batch = _batch(rows, cols)

    assert len(batch.records) == 2  # good rows survive
    assert [r.row_index for r in batch.records] == [0, 2]
    assert len(batch.parse_failures) == 1  # malformed captured, not dropped, no crash

    pf = batch.parse_failures[0]
    assert pf.reason == ParseFailureReason.MALFORMED_ROW
    assert pf.row_index == 1
    assert pf.raw == ["this", "is", "not", "a", "mapping"]  # original preserved


def test_empty_mapping_quarantined_as_empty_row() -> None:
    batch = _batch([{}], ["state_name", "month"])

    assert batch.records == []
    assert len(batch.parse_failures) == 1
    assert batch.parse_failures[0].reason == ParseFailureReason.EMPTY_ROW


def test_quarantine_predicate_flags_synthetic_total_row() -> None:
    rows = [
        {"state": "Goa", "value": "0.94"},
        {"state": "Total", "value": "100.0"},
    ]
    cols = ["state", "value"]

    def is_total(row: dict[str, Any]) -> ParseFailureReason | None:
        if row.get("state") == "Total":
            return ParseFailureReason.SYNTHETIC_TOTAL_ROW
        return None

    batch = _batch(rows, cols, quarantine=is_total)

    assert len(batch.records) == 1
    assert batch.records[0].raw["state"] == "Goa"
    assert len(batch.parse_failures) == 1
    assert batch.parse_failures[0].reason == ParseFailureReason.SYNTHETIC_TOTAL_ROW
    assert batch.parse_failures[0].row_index == 1


def test_records_are_immutable() -> None:
    rec = _batch([{"a": "1"}], ["a"]).records[0]
    with pytest.raises(ValidationError):
        rec.row_index = 5
