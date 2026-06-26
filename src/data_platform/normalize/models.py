"""Stage 2 normalization models — the typed surface Stage 2 transforms produce.

Parallel to the Stage 1 landing models (``ingest/landing.py``) and, like them, ``strict``
(no coercion at the boundary) and ``frozen`` (immutable): a normalized record is the audited
RESULT of Stage 2, never mutated in place. Stage 2 reads a ``RawLandingBatch`` and emits a
:class:`NormalizedBatch`; the raw batch stays the immutable upstream anchor of the lineage chain.

Decisions baked into these shapes (locked at review — see tasks/stage2-todo.md):
* Q1 — a coercion failure nulls the CELL and is flagged on that column in
  :class:`NormalizationLineage`; it is NOT a row quarantine. So
  :class:`NormalizationQuarantineReason` carries only WHOLE-ROW reasons.
* Q3 — :class:`DedupeLineage` records the collapse COUNT + collapsed row indexes only, never
  the dropped values (row-atomic dedupe; single-row provenance preserved). It is ALWAYS present
  on the batch (zeros/empty when nothing collapsed — absence of dedupe is itself trust signal).
* Q2/Q4/Q6 — cleaned cells are ``int`` for counts and ``Decimal`` for money/rate; identifiers
  (``state_code``/``district_code``) and the canonical FY ("2022-23") and month ("01") stay
  ``str`` (a financial year is a span, not a calendar date — never a ``date``).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from data_platform.ingest.landing import DriftFlag, PullCompleteness

# A cleaned + typed cell value. No ``float`` (money/rate become ``Decimal``, counts ``int``;
# Q6), no ``bool`` (no boolean columns in the flagship schema), and no ``date`` (FY and month
# are canonical STRINGS per Q2, not calendar dates); ``None`` is null (≠ 0).
CleanCell = str | int | Decimal | None

# A verbatim landing cell value (as preserved by Stage 1) — kept on a quarantined whole row.
RawCell = str | int | float | bool | None


class _NormalizedModel(BaseModel):
    """Base for Stage 2 models: immutable and strict (no coercion at the boundary)."""

    model_config = ConfigDict(strict=True, frozen=True)


class NormalizationQuarantineReason(StrEnum):
    """Typed reason a WHOLE row is quarantined in Stage 2 (kept, never silently dropped).

    Post the R2-TYPE-01 amendment (Q1), a coercion failure nulls the *cell* and is flagged in
    ``normalization_rules`` — it is NOT a row quarantine. The sole whole-row Stage 2 failure is
    a row with NO identity to place in the canonical grain: ALL grain-key columns (state,
    district, fin_year, month) are null. A PARTIAL-key row (some keys present) passes through
    un-quarantined — that is the validation gate's (Stage 5) concern, not Stage 2's.
    """

    MISSING_GRAIN_KEY = "missing_grain_key"


class NormalizationLineage(_NormalizedModel):
    """Per-column record of which Stage 2 rules fired (DATA_CONTRACT §4 ``normalization_rules``).

    ``per_column`` maps a source column name to the ordered rule-ids applied to it, with detail,
    e.g. ``{"Total_Exp": ["R2-FMT-01", "R2-TYPE-01:long→decimal"]}``. A column whose value could
    not be coerced (Q1) carries ``"R2-TYPE-01:coercion_failed"`` and its cell is null.
    """

    per_column: dict[str, list[str]]


class DedupeLineage(_NormalizedModel):
    """Batch-level snapshot-dedupe summary (DATA_CONTRACT §4 ``dedupe`` — ALWAYS present).

    Q3 (row-atomic dedupe): records the collapse COUNT and the collapsed row indexes ONLY —
    never the dropped values. ``tie_break_rule_id`` is the config-carried active strategy id
    (DATA_CONTRACT §6 item 6; default ``R2-DEDUP-TB-01``), recorded even when nothing collapsed.
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
