"""T2.1 — Stage 2 normalization models (tests written first, strict TDD red checkpoint).

Scope (locked): model SHAPES, FROZEN immutability, and lineage fields present + correctly
typed — for NormalizedRecord, NormalizedBatch, NormalizationFailure +
NormalizationQuarantineReason, NormalizationLineage, DedupeLineage. No pipeline logic here
(that is T2.2+). The fixtures encode the locked review decisions: Q1 (coercion failure flagged
per-column, not a row quarantine), Q2 (FY "YYYY-YY", month "01".."12"), Q3 (dedupe lineage =
count + indexes only), Q6 (Decimal money / int counts; identifiers stay str per Q4).

RED at this checkpoint: the *_is_frozen tests and the strict-no-coercion test fail because the
stub base is not yet frozen/strict; the green commit adds ConfigDict(strict=True, frozen=True).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from data_platform.normalize.models import (
    DedupeLineage,
    NormalizationFailure,
    NormalizationLineage,
    NormalizationQuarantineReason,
    NormalizedBatch,
    NormalizedRecord,
    RawCell,
)

INGESTED = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
AS_OF = datetime(2026, 6, 22, 17, 0, tzinfo=UTC)


def _lineage() -> NormalizationLineage:
    return NormalizationLineage(
        per_column={
            "Total_Exp": ["R2-FMT-01", "R2-TYPE-01:long→decimal"],
            "Remarks": ["R2-FMT-01:NA→null"],
            "fin_year": ["R2-DATE-01:2022-2023→2022-23"],
        }
    )


def _record() -> NormalizedRecord:
    return NormalizedRecord(
        row_index=0,
        cells={
            "state_code": "10",  # identifier stays string (Q4)
            "Persondays_of_Central_Liability_so_far": 34679,  # count -> int (Q6)
            "Total_Exp": Decimal("165.53913"),  # money -> Decimal (Q6)
            "fin_year": "2022-23",  # canonical FY (Q2)
            "month": "01",  # zero-padded month (Q2)
            "Remarks": None,  # NA -> null (R2-FMT-01); null != 0
        },
        normalization=_lineage(),
    )


def _dedupe() -> DedupeLineage:
    return DedupeLineage(
        duplicates_collapsed=1,
        collapsed_row_indexes=[1],
        tie_break_rule_id="R2-DEDUP-TB-01",
    )


# --- NormalizedRecord -------------------------------------------------------------


def test_normalized_record_carries_typed_cells_and_lineage() -> None:
    rec = _record()
    assert rec.row_index == 0
    assert rec.cells["state_code"] == "10"
    assert isinstance(rec.cells["state_code"], str)
    assert rec.cells["Persondays_of_Central_Liability_so_far"] == 34679
    assert isinstance(rec.cells["Persondays_of_Central_Liability_so_far"], int)
    assert rec.cells["Total_Exp"] == Decimal("165.53913")
    assert isinstance(rec.cells["Total_Exp"], Decimal)
    assert rec.cells["Remarks"] is None  # null, never 0
    assert rec.cells["Remarks"] != 0
    assert rec.normalization.per_column["Total_Exp"] == ["R2-FMT-01", "R2-TYPE-01:long→decimal"]


def test_normalized_record_is_frozen() -> None:
    rec = _record()
    with pytest.raises(ValidationError):
        rec.row_index = 5


def test_normalized_record_cells_are_strict_no_coercion() -> None:
    # A money cell is declared Decimal: a bare float must be REJECTED, not silently coerced
    # to Decimal — strict mode keeps source representation honest. (float is not even a valid
    # CleanCell statically — the type:ignore proves the *runtime* guard, not the static one.)
    with pytest.raises(ValidationError):
        NormalizedRecord(
            row_index=0,
            cells={"Total_Exp": 165.53913},  # type: ignore[dict-item]
            normalization=_lineage(),
        )


# --- NormalizationLineage (normalization_rules, §4) -------------------------------


def test_normalization_lineage_maps_column_to_rule_ids() -> None:
    lin = _lineage()
    assert lin.per_column["Remarks"] == ["R2-FMT-01:NA→null"]
    assert lin.per_column["fin_year"] == ["R2-DATE-01:2022-2023→2022-23"]


def test_normalization_lineage_is_frozen() -> None:
    lin = _lineage()
    with pytest.raises(ValidationError):
        lin.per_column = {}


# --- DedupeLineage (dedupe, §4; Q3) ----------------------------------------------


def test_dedupe_lineage_records_count_indexes_and_rule_id_only() -> None:
    d = _dedupe()
    assert d.duplicates_collapsed == 1
    assert d.collapsed_row_indexes == [1]
    assert d.tie_break_rule_id == "R2-DEDUP-TB-01"
    # Q3: lineage stores no dropped values, only the collapse audit trail.
    assert not hasattr(d, "dropped_values")


def test_dedupe_lineage_is_frozen() -> None:
    d = _dedupe()
    with pytest.raises(ValidationError):
        d.duplicates_collapsed = 9


# --- NormalizationFailure + reason (whole-row quarantine) -------------------------


def test_normalization_quarantine_reason_is_str_enum() -> None:
    assert isinstance(NormalizationQuarantineReason.MISSING_GRAIN_KEY, str)
    assert NormalizationQuarantineReason.MISSING_GRAIN_KEY.value == "missing_grain_key"


def test_normalization_failure_preserves_row_and_typed_reason() -> None:
    # MISSING_GRAIN_KEY fires only when ALL grain-key columns are null (no identity).
    raw: dict[str, RawCell] = {
        "state_name": None,
        "district_name": None,
        "fin_year": None,
        "month": None,
    }
    fail = NormalizationFailure(
        row_index=7,
        raw=raw,
        reason=NormalizationQuarantineReason.MISSING_GRAIN_KEY,
    )
    assert fail.row_index == 7
    assert fail.raw == raw
    assert fail.reason is NormalizationQuarantineReason.MISSING_GRAIN_KEY


def test_normalization_failure_is_frozen() -> None:
    fail = NormalizationFailure(
        row_index=7, raw={"a": "1"}, reason=NormalizationQuarantineReason.MISSING_GRAIN_KEY
    )
    with pytest.raises(ValidationError):
        fail.row_index = 0


# --- NormalizedBatch (provenance carried from landing + Stage 2 outputs) ----------


def test_normalized_batch_carries_provenance_and_stage2_outputs() -> None:
    batch = NormalizedBatch(
        source_id="SRC_FLAGSHIP",
        resource_id="ee03643a-ee4c-48c2-ac30-9f2ff26ab722",
        ingested_at=INGESTED,
        source_as_of=AS_OF,
        schema_version="sha256:abc",
        source_grain="district+monthly",
        pull_completeness="full",
        column_names=["state_code", "Total_Exp"],
        records=[_record()],
        quarantined=[],
        dedupe=_dedupe(),
    )
    # provenance breadcrumbs carried from landing (DATA_CONTRACT §4)
    assert batch.source_id == "SRC_FLAGSHIP"
    assert batch.source_as_of == AS_OF
    assert batch.pull_completeness == "full"
    # Stage 2 outputs
    assert batch.records[0].cells["Total_Exp"] == Decimal("165.53913")
    assert batch.quarantined == []
    assert batch.dedupe.tie_break_rule_id == "R2-DEDUP-TB-01"


def test_normalized_batch_is_frozen() -> None:
    batch = NormalizedBatch(
        source_id="SRC_FLAGSHIP",
        resource_id="r",
        ingested_at=INGESTED,
        source_as_of=None,
        schema_version="sv",
        source_grain="district+monthly",
        pull_completeness="partial",
        column_names=[],
        records=[],
        quarantined=[],
        dedupe=_dedupe(),
    )
    with pytest.raises(ValidationError):
        batch.source_id = "X"
