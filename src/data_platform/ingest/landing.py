"""Raw landing-zone models for Stage 1 ingestion.

DELIBERATE DESIGN — verbatim, NO coercion
------------------------------------------
Pydantic's default posture is to parse/coerce values at the model boundary
(e.g. ``"3884.10"`` -> ``float``, ``12`` -> ``"12"``, ``"NA"`` left as-is only by
accident). We deliberately DISABLE that here: every landing model runs in
``strict=True`` so Pydantic never coerces, and each source cell is stored exactly
as the source emitted it — a string, a numeric scalar (``int``/``float``), a
boolean, or ``None`` for a declared column absent from that row — with its
original type intact (in particular a JSON ``true`` stays ``True``, never ``1``).

The flagship API's type metadata is unreliable and a cell that is "really" a
string may arrive as a bare number. We keep that number verbatim-typed rather
than discarding the row: stringifying even losslessly (``12`` -> ``"12"``) would
mutate the source representation at ingest with no lineage entry, and dropping the
row over one typed cell would lose its other (good) columns — silent data loss,
the opposite of this pipeline's thesis. Type normalization is DEFERRED to Stage 2.

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

QUARANTINE, NOT DROP
--------------------
A row that cannot become a clean :class:`RawLandingRecord` is never silently
dropped: it is captured as a :class:`ParseFailure` with a typed
:class:`ParseFailureReason`, so the batch survives and the loss is auditable.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class ParseFailureReason(StrEnum):
    """Typed reason a row was quarantined at ingestion (kept, never silently dropped)."""

    MALFORMED_ROW = "malformed_row"  # not a mapping, or a cell value that is not a verbatim scalar
    EMPTY_ROW = "empty_row"  # mapping with no keys
    SYNTHETIC_TOTAL_ROW = "synthetic_total_row"  # e.g. the RS "Total" pseudo-row


class _Frozen(BaseModel):
    """Base for landing models: immutable and strict (no coercion at the boundary)."""

    model_config = ConfigDict(strict=True, frozen=True)


class RawLandingRecord(_Frozen):
    """One raw source row, verbatim. No breadcrumbs — provenance is batch-level."""

    row_index: int
    raw: dict[str, str | int | float | bool | None]


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

    Pure (no I/O), deterministic. Each row, in source order, is classified into a
    :class:`RawLandingRecord` or a typed :class:`ParseFailure`:

    * non-mapping row (e.g. a list) -> ``MALFORMED_ROW``;
    * empty mapping -> ``EMPTY_ROW``;
    * mapping flagged by the optional ``quarantine`` predicate -> its reason
      (e.g. ``SYNTHETIC_TOTAL_ROW``); when ``quarantine`` is omitted nothing is
      flagged by it;
    * otherwise a record is built. Declared columns absent from the row surface as
      ``None`` (null, never 0); present cells are kept verbatim with their original
      type (``str``/``int``/``float``/``bool``) — a bare numeric or boolean cell
      from unreliable upstream type metadata is preserved, not stringified and not
      dropped. Only a cell that is not a verbatim scalar (e.g. a nested list/dict)
      fails strict construction and is captured as ``MALFORMED_ROW``.

    Good rows always survive even when sibling rows in the batch are quarantined.
    Provenance is recorded once on the batch, never denormalized onto records.
    """
    records: list[RawLandingRecord] = []
    parse_failures: list[ParseFailure] = []

    for row_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            parse_failures.append(
                ParseFailure(row_index=row_index, raw=row, reason=ParseFailureReason.MALFORMED_ROW)
            )
            continue

        if len(row) == 0:
            parse_failures.append(
                ParseFailure(row_index=row_index, raw=row, reason=ParseFailureReason.EMPTY_ROW)
            )
            continue

        if quarantine is not None:
            reason = quarantine(dict(row))
            if reason is not None:
                parse_failures.append(ParseFailure(row_index=row_index, raw=row, reason=reason))
                continue

        # Verbatim copy, then fill declared-but-absent columns with null (never 0).
        raw: dict[str, Any] = dict(row)
        for column in column_names:
            if column not in raw:
                raw[column] = None

        try:
            record = RawLandingRecord(row_index=row_index, raw=raw)
        except ValidationError:
            # A cell value that is not a verbatim scalar (str|int|float|bool|None) —
            # e.g. a nested container: keep it, flag it, don't coerce.
            parse_failures.append(
                ParseFailure(row_index=row_index, raw=row, reason=ParseFailureReason.MALFORMED_ROW)
            )
            continue

        records.append(record)

    return RawLandingBatch(
        source_id=source_id,
        resource_id=resource_id,
        ingested_at=ingested_at,
        source_as_of=source_as_of,
        schema_version=schema_version,
        source_grain=source_grain,
        column_names=column_names,
        records=records,
        parse_failures=parse_failures,
    )
