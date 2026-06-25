"""Raw landing-zone models for Stage 1 ingestion.

DELIBERATE DESIGN — verbatim, NO coercion
------------------------------------------
Pydantic's default posture is to parse/coerce values at the model boundary
(e.g. ``"3884.10"`` -> ``float``, ``12`` -> ``"12"``, ``"NA"`` left as-is only by
accident). We deliberately DISABLE that here: every landing model runs in
``strict=True`` so Pydantic never coerces, and each source cell is stored exactly
as the source emitted it (a string, or ``None`` for a declared column absent from
that row).

This is intentional, not an oversight. Lineage (DATA_CONTRACT §4) requires that
every transformation of a value be recorded; coercing at ingest would silently
mutate source bytes with no lineage entry. So all coercion (``"NA"`` -> null,
comma-stripping, ``lakh`` -> ``crore``, date parsing) is DEFERRED to later stages
(2 normalize / 4 harmonize) that log each step. The ONLY null introduced at
landing is for a declared column missing from a row — recording absence as null,
never 0 (``null != 0``; CLAUDE.md TIER 1).

PROVENANCE IS BATCH-LEVEL
-------------------------
``source_id``, ``resource_id``, ``ingested_at``, ``source_as_of``,
``schema_version`` and ``source_grain`` live on :class:`RawLandingBatch`, NOT on
each :class:`RawLandingRecord` (which carries only ``row_index`` + ``raw``).
Denormalizing identical breadcrumbs across thousands of rows invites drift and
inconsistency; per-record lineage is materialized later in the governed store.

NOTE: this module is currently a typed STUB — models are real (so types resolve
and tests collect) but :func:`build_batch` is not yet implemented (T1.1 TDD red).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ParseFailureReason(StrEnum):
    """Typed reason a row was quarantined at ingestion (kept, never silently dropped)."""

    MALFORMED_ROW = "malformed_row"  # not a mapping, or a non-string cell value
    EMPTY_ROW = "empty_row"  # mapping with no keys
    SYNTHETIC_TOTAL_ROW = "synthetic_total_row"  # e.g. the RS "Total" pseudo-row


class _Frozen(BaseModel):
    """Base for landing models: immutable and strict (no coercion at the boundary)."""

    model_config = ConfigDict(strict=True, frozen=True)


class RawLandingRecord(_Frozen):
    """One raw source row, verbatim. No breadcrumbs — provenance is batch-level."""

    row_index: int
    raw: dict[str, str | None]


class ParseFailure(_Frozen):
    """A row quarantined at ingestion, preserved as-seen with a typed reason."""

    row_index: int
    raw: Any
    reason: ParseFailureReason


class DriftFlag(_Frozen):
    """Schema-drift marker for a batch (populated in T1.3; detect-and-tag only)."""

    detected: bool
    previous_version: str | None
    new_version: str
    added: list[str]
    removed: list[str]


class RawLandingBatch(_Frozen):
    """The unit one adapter run emits. Carries all provenance breadcrumbs (§4)."""

    source_id: str
    resource_id: str
    ingested_at: datetime
    source_as_of: datetime | None
    schema_version: str
    source_grain: str
    column_names: list[str]
    records: list[RawLandingRecord]
    parse_failures: list[ParseFailure]
    drift: DriftFlag | None = None


def build_batch(
    *,
    source_id: str,
    resource_id: str,
    ingested_at: datetime,
    source_as_of: datetime | None,
    schema_version: str,
    source_grain: str,
    column_names: list[str],
    rows: list[Any],
    quarantine: Callable[[dict[str, Any]], ParseFailureReason | None] | None = None,
) -> RawLandingBatch:
    """Build a :class:`RawLandingBatch` from raw source rows.

    Pure (no I/O). Each row is classified into a :class:`RawLandingRecord` or a
    typed :class:`ParseFailure` (malformed/empty, or flagged by ``quarantine``).
    Absent declared columns are filled with ``None`` (null, never 0); present
    values are kept verbatim.

    STUB: behaviour not yet implemented (T1.1 TDD red).
    """
    raise NotImplementedError("T1.1: build_batch is not yet implemented")
