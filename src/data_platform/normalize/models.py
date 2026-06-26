"""Stage 2 normalization models — T2.1 STUB (red TDD checkpoint).

These declare the Stage 2 model SURFACE — field names and types — so the T2.1 test
module is import-clean and type-checks under mypy strict. They DELIBERATELY omit the
behavioural guarantees the tests assert: ``_NormalizedModel`` is not yet ``frozen`` or
``strict``, so the immutability and no-coercion tests are RED. Wiring those guarantees
(and any defaults/validators) is the green commit ``feat(stage2): …``. Do not implement
behaviour here until the test design is reviewed.

Decisions baked into these shapes (locked at review — see tasks/stage2-todo.md):
* Q1 — a coercion failure nulls the CELL and is flagged on that column in
  :class:`NormalizationLineage`; it is NOT a row quarantine. Hence
  :class:`NormalizationQuarantineReason` carries only WHOLE-ROW reasons.
* Q3 — :class:`DedupeLineage` records the collapse COUNT + collapsed row indexes only,
  never the dropped values (row-atomic dedupe, single-row provenance preserved).
* Q6 — cleaned cells are ``int`` for counts and ``Decimal`` for money/rate; identifiers
  (``state_code``/``district_code``) stay ``str`` (Q4).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

from data_platform.ingest.landing import DriftFlag, PullCompleteness

# A cleaned + typed cell value. No ``float`` (money/rate become ``Decimal``, counts ``int``;
# Q6) and no ``bool`` (no boolean columns in the flagship schema); ``None`` is null (≠ 0).
CleanCell = str | int | Decimal | date | None

# A verbatim landing cell value (as preserved by Stage 1) — kept on a quarantined whole row.
RawCell = str | int | float | bool | None


class _NormalizedModel(BaseModel):
    """Base for Stage 2 models.

    T2.1 STUB: no ``model_config`` yet — NOT frozen, NOT strict — so the behavioural tests
    are RED. The green commit sets ``model_config = ConfigDict(strict=True, frozen=True)``.
    """


class NormalizationQuarantineReason(StrEnum):
    """Typed reason a WHOLE row is quarantined in Stage 2 (kept, never silently dropped).

    NOTE for review: post the R2-TYPE-01 amendment (Q1), a coercion failure nulls the *cell*
    and is flagged in ``normalization_rules`` — it is NOT a row quarantine. The single
    whole-row Stage 2 failure seeded here is a row that cannot be keyed to the grain (its
    source-level dedupe-key columns are all missing), which R2-DEDUP-01 needs to group rows.
    Confirm/rename/extend this set in review.
    """

    MISSING_DEDUP_KEY = "missing_dedup_key"


class NormalizationLineage(_NormalizedModel):
    """Per-column record of which Stage 2 rules fired (DATA_CONTRACT §4 ``normalization_rules``).

    ``per_column`` maps a source column name to the ordered rule-ids applied to it, with
    detail, e.g. ``{"Total_Exp": ["R2-FMT-01", "R2-TYPE-01:long→decimal"]}``. A column with
    a coercion failure (Q1) carries ``"R2-TYPE-01:coercion_failed"``.
    """

    per_column: dict[str, list[str]]


class DedupeLineage(_NormalizedModel):
    """Batch-level snapshot-dedupe summary (DATA_CONTRACT §4 ``dedupe``).

    Q3 (row-atomic dedupe): records the collapse COUNT and the collapsed row indexes ONLY —
    never the dropped values. ``tie_break_rule_id`` is the config-carried active strategy id
    (DATA_CONTRACT §6 item 6; default ``R2-DEDUP-TB-01``).
    """

    duplicates_collapsed: int
    collapsed_row_indexes: list[int]
    tie_break_rule_id: str


class NormalizationFailure(_NormalizedModel):
    """A row quarantined WHOLE in Stage 2, preserved as-seen with a typed reason."""

    row_index: int
    raw: dict[str, RawCell]
    reason: NormalizationQuarantineReason


class NormalizedRecord(_NormalizedModel):
    """One source row after Stage 2 cleanup: cells cleaned + typed, lineage attached.

    Source column names are preserved (no canonical-metric mapping — that is Stage 3/4).
    """

    row_index: int
    cells: dict[str, CleanCell]
    normalization: NormalizationLineage


class NormalizedBatch(_NormalizedModel):
    """Stage 2 output for one batch: provenance carried from landing + typed records + lineage."""

    source_id: str
    resource_id: str
    ingested_at: datetime
    source_as_of: datetime | None
    schema_version: str
    source_grain: str
    pull_completeness: PullCompleteness
    column_names: list[str]
    records: list[NormalizedRecord]
    quarantined: list[NormalizationFailure]
    dedupe: DedupeLineage
    drift: DriftFlag | None = None
