"""R2-DEDUP-01 — intra-batch snapshot dedupe.

Row-atomic (Q3): collapse rows sharing a grain key to ONE winning row, kept WHOLE — no
cross-row cell merge, so every surviving value still cites one coherent source row. Winner per
R2-DEDUP-TB-01: latest ``source_as_of``, ties → last occurrence in file (highest row index).
``source_as_of`` is batch-level (uniform intra-batch), so intra-batch the tie-break resolves on
file order; the as_of half is the cross-pull rule the governed store will reuse (Q5).

A row whose grain key is entirely null is quarantined ``MISSING_GRAIN_KEY`` (no identity to
place in the grain); a partial key passes through (Stage 5's concern). Lineage records the
collapse count + collapsed row indexes only — never the dropped values.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import NamedTuple

from data_platform.normalize.models import (
    CleanCell,
    DedupeLineage,
    NormalizationFailure,
    NormalizationQuarantineReason,
    RawCell,
)

# Sorts below any real (tz-aware) batch as_of, so a null as_of never out-ranks a dated row.
_MIN_AS_OF = datetime.min.replace(tzinfo=UTC)


class DedupeCandidate(NamedTuple):
    """One row offered to dedupe: its index, verbatim raw (for quarantine), cleaned grain key,
    and the batch ``source_as_of`` (uniform intra-batch; the tie-break's cross-pull half)."""

    row_index: int
    raw: dict[str, RawCell]
    key: tuple[CleanCell, ...]
    source_as_of: datetime | None


class DedupeResult(NamedTuple):
    """Surviving row indexes (ascending), missing-key quarantines, and the dedupe lineage."""

    surviving_row_indexes: list[int]
    quarantined: list[NormalizationFailure]
    lineage: DedupeLineage


def _rank(candidate: DedupeCandidate) -> tuple[datetime, int]:
    """R2-DEDUP-TB-01 ordering key: (source_as_of, row_index); the max wins."""
    return (candidate.source_as_of or _MIN_AS_OF, candidate.row_index)


def dedupe(candidates: Sequence[DedupeCandidate], *, tie_break_rule_id: str) -> DedupeResult:
    """Collapse duplicate-grain-key rows to one winner each; quarantine identity-less rows."""
    quarantined: list[NormalizationFailure] = []
    groups: dict[tuple[CleanCell, ...], list[DedupeCandidate]] = {}

    for candidate in candidates:
        if all(value is None for value in candidate.key):
            quarantined.append(
                NormalizationFailure(
                    row_index=candidate.row_index,
                    raw=candidate.raw,
                    reason=NormalizationQuarantineReason.MISSING_GRAIN_KEY,
                )
            )
            continue
        groups.setdefault(candidate.key, []).append(candidate)

    survivors: list[int] = []
    collapsed: list[int] = []
    for members in groups.values():
        winner = max(members, key=_rank)
        survivors.append(winner.row_index)
        collapsed.extend(member.row_index for member in members if member is not winner)

    return DedupeResult(
        surviving_row_indexes=sorted(survivors),
        quarantined=quarantined,
        lineage=DedupeLineage(
            duplicates_collapsed=len(collapsed),
            collapsed_row_indexes=sorted(collapsed),
            tie_break_rule_id=tie_break_rule_id,
        ),
    )
