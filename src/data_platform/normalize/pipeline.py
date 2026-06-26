"""Stage 2 orchestrator — ``normalize_batch``.

Pure, deterministic transform: a Stage 1 ``RawLandingBatch`` in, a :class:`NormalizedBatch` out.
Composes the Stage 2 rules in the locked order:

1. **R2-FMT-01** on every cell of every row (strip commas, NA/blank/"-" → null).
2. **R2-DEDUP-01** on the FMT-cleaned grain keys — collapse snapshot duplicates row-atomically
   (Q3) and quarantine identity-less rows (MISSING_GRAIN_KEY). Runs BEFORE coercion so a
   coercion failure is never charged to a row that is about to be dropped, and so null-token
   keys (``"NA"`` → null) are seen as missing.
3. **R2-TYPE-01 / R2-DATE-01** on the surviving rows, dispatched per the config column-type spec
   (counts→int, money/rate→Decimal, FY/month→canonical strings; unspec'd columns stay strings).

Every per-cell transformation and the dedupe summary are recorded in lineage (DATA_CONTRACT §4).
"""

from __future__ import annotations

from data_platform.ingest.landing import RawLandingBatch
from data_platform.normalize.coerce import coerce_cell
from data_platform.normalize.config import (
    COLUMN_TYPES,
    DEDUPE_TIE_BREAK_RULE_ID,
    DEFAULT_COLUMN_TYPE,
    GRAIN_KEY_COLUMNS,
    ColumnType,
)
from data_platform.normalize.dates import normalize_fy, normalize_month
from data_platform.normalize.dedupe import DedupeCandidate, dedupe
from data_platform.normalize.fmt import FmtOutcome, apply_fmt
from data_platform.normalize.models import (
    CleanCell,
    NormalizationLineage,
    NormalizedBatch,
    NormalizedRecord,
    RawCell,
)


def normalize_batch(batch: RawLandingBatch) -> NormalizedBatch:
    """Normalize one landing batch into a typed, de-duplicated, lineage-stamped batch."""
    column_types = COLUMN_TYPES.get(batch.source_id)
    grain_key_columns = GRAIN_KEY_COLUMNS.get(batch.source_id)
    if column_types is None or grain_key_columns is None:
        raise ValueError(f"no Stage 2 config for source {batch.source_id!r}")

    # 1. R2-FMT-01 every cell, cached per row (reused for keys and for surviving rows).
    fmt_by_row: dict[int, dict[str, FmtOutcome]] = {
        record.row_index: {col: apply_fmt(record.raw.get(col)) for col in batch.column_names}
        for record in batch.records
    }

    # 2. R2-DEDUP-01 on FMT-cleaned grain keys.
    candidates = [
        DedupeCandidate(
            row_index=record.row_index,
            raw=record.raw,
            key=tuple(fmt_by_row[record.row_index][col].value for col in grain_key_columns),
            source_as_of=batch.source_as_of,
        )
        for record in batch.records
    ]
    deduped = dedupe(candidates, tie_break_rule_id=DEDUPE_TIE_BREAK_RULE_ID)

    # 3. R2-TYPE-01 / R2-DATE-01 on the surviving rows.
    records = [
        _build_record(row_index, fmt_by_row[row_index], batch.column_names, column_types)
        for row_index in deduped.surviving_row_indexes
    ]

    return NormalizedBatch(
        source_id=batch.source_id,
        resource_id=batch.resource_id,
        ingested_at=batch.ingested_at,
        source_as_of=batch.source_as_of,
        schema_version=batch.schema_version,
        source_grain=batch.source_grain,
        pull_completeness=batch.pull_completeness,
        column_names=batch.column_names,
        records=records,
        quarantined=deduped.quarantined,
        dedupe=deduped.lineage,
        drift=batch.drift,
    )


def _build_record(
    row_index: int,
    fmt_cells: dict[str, FmtOutcome],
    column_names: list[str],
    column_types: dict[str, ColumnType],
) -> NormalizedRecord:
    cells: dict[str, CleanCell] = {}
    per_column: dict[str, list[str]] = {}
    for col in column_names:
        fmt = fmt_cells[col]
        value, typed_note = _apply_type(fmt.value, column_types.get(col, DEFAULT_COLUMN_TYPE))
        notes = [note for note in (fmt.note, typed_note) if note is not None]
        cells[col] = value
        if notes:
            per_column[col] = notes
    return NormalizedRecord(
        row_index=row_index,
        cells=cells,
        normalization=NormalizationLineage(per_column=per_column),
    )


def _apply_type(value: RawCell, column_type: ColumnType) -> tuple[CleanCell, str | None]:
    """Dispatch one cleaned cell to R2-DATE-01 (FY/MONTH) or R2-TYPE-01 (STRING/INT/DECIMAL)."""
    if column_type is ColumnType.FY:
        fy = normalize_fy(value)
        return fy.value, fy.note
    if column_type is ColumnType.MONTH:
        month = normalize_month(value)
        return month.value, month.note
    coerced = coerce_cell(value, column_type)
    return coerced.value, coerced.note
