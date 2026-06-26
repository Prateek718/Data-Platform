"""R2-DEDUP-01 — intra-batch snapshot dedupe (T2.5 STUB — red checkpoint).

Row-atomic (Q3): collapse rows sharing a grain key to ONE winning row, kept WHOLE — no
cross-row cell merge. Winner per R2-DEDUP-TB-01: latest ``source_as_of``, ties → last
occurrence in file. A row whose grain key is entirely null is quarantined ``MISSING_GRAIN_KEY``
(no identity); a partial key passes through (Stage 5's concern, Q5 intra-batch only).
Lineage records the collapse count + collapsed row indexes only — never dropped values.
Implemented in the green commit ``feat(stage2): …``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple

from data_platform.normalize.models import (
    CleanCell,
    DedupeLineage,
    NormalizationFailure,
    RawCell,
)


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


def dedupe(candidates: Sequence[DedupeCandidate], *, tie_break_rule_id: str) -> DedupeResult:
    """Collapse duplicate-grain-key rows. STUB — raises until the green commit."""
    raise NotImplementedError("T2.5 R2-DEDUP-01 — implemented in the green commit")
