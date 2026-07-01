"""Stage 2 orchestrator — ``normalize_batch``.

Pure, deterministic transform: a Stage 1 ``RawLandingBatch`` in, a :class:`NormalizedBatch` out.
Per-resource config (keyed by ``resource_id``) drives the locked rule order:

0. **reshape (Stage 3.5)** — wide/single-period sources are melted / period-or-geo-injected into
   long one-fact-per-row form (a no-op for the flagship and other already-long tables). Recorded
   in lineage on the synthesized columns.
1. **R2-FMT-01** on every cell of every (reshaped) row (strip commas, NA/blank/"-" → null).
2. **R2-DEDUP-01** on the FMT-cleaned grain keys — collapse snapshot duplicates row-atomically
   and quarantine identity-less rows (MISSING_GRAIN_KEY). Runs BEFORE coercion so a coercion
   failure is never charged to a row about to be dropped, and null-token keys are seen as missing.
3. **R2-TYPE-01 / R2-DATE-01** on surviving rows, dispatched per the config column-type spec.

Every per-cell transformation, the reshape applied, and the dedupe summary are recorded in lineage.
"""

from __future__ import annotations

from data_platform.ingest.landing import RawLandingBatch
from data_platform.normalize.coerce import coerce_cell
from data_platform.normalize.config import (
    DEDUPE_TIE_BREAK_RULE_ID,
    DEFAULT_COLUMN_TYPE,
    NORMALIZE_CONFIG,
    ColumnType,
    ResourceNormalizeConfig,
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
from data_platform.normalize.reshape import Row, apply_reshape, reshape_notes


def normalize_batch(
    batch: RawLandingBatch, config: ResourceNormalizeConfig | None = None
) -> NormalizedBatch:
    """Normalize one landing batch into a reshaped, typed, de-duplicated, lineage-stamped batch.

    ``config`` defaults to the per-resource entry looked up by ``batch.resource_id``; it may be
    passed explicitly (dependency injection) to normalize a resource whose config the caller holds.
    """
    if config is None:
        config = NORMALIZE_CONFIG.get(batch.resource_id)
    if config is None:
        raise ValueError(f"no Stage 2 config for resource {batch.resource_id!r}")

    # 0. Reshape wide/single-period rows into long form (no-op for already-long tables).
    raw_rows: list[Row] = [record.raw for record in batch.records]
    rows, column_names = apply_reshape(raw_rows, batch.column_names, config.reshape)
    synth_notes = reshape_notes(config.reshape)

    # 1. R2-FMT-01 every cell of every (reshaped) row, cached by row index.
    fmt_by_row: dict[int, dict[str, FmtOutcome]] = {
        index: {col: apply_fmt(row.get(col)) for col in column_names}
        for index, row in enumerate(rows)
    }

    # 2. R2-DEDUP-01 on FMT-cleaned grain keys.
    candidates = [
        DedupeCandidate(
            row_index=index,
            raw=rows[index],
            key=tuple(fmt_by_row[index][col].value for col in config.grain_key_columns),
            source_as_of=batch.source_as_of,
        )
        for index in range(len(rows))
    ]
    deduped = dedupe(candidates, tie_break_rule_id=DEDUPE_TIE_BREAK_RULE_ID)

    # 3. R2-TYPE-01 / R2-DATE-01 on the surviving rows.
    records = [
        _build_record(index, fmt_by_row[index], column_names, config.column_types, synth_notes)
        for index in deduped.surviving_row_indexes
    ]

    return NormalizedBatch(
        source_id=batch.source_id,
        resource_id=batch.resource_id,
        ingested_at=batch.ingested_at,
        source_as_of=batch.source_as_of,
        schema_version=batch.schema_version,
        source_grain=batch.source_grain,
        pull_completeness=batch.pull_completeness,
        column_names=column_names,
        records=records,
        quarantined=deduped.quarantined,
        dedupe=deduped.lineage,
    )


def _build_record(
    row_index: int,
    fmt_cells: dict[str, FmtOutcome],
    column_names: list[str],
    column_types: dict[str, ColumnType],
    synth_notes: dict[str, str],
) -> NormalizedRecord:
    cells: dict[str, CleanCell] = {}
    per_column: dict[str, list[str]] = {}
    for col in column_names:
        fmt = fmt_cells[col]
        value, typed_note = _apply_type(fmt.value, column_types.get(col, DEFAULT_COLUMN_TYPE))
        # A reshape note leads the column's lineage (the value was synthesized before FMT/TYPE ran).
        reshape_note = synth_notes.get(col)
        notes = [n for n in (reshape_note, fmt.note, typed_note) if n is not None]
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
