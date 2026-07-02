"""R4-REC — cross-source value reconciliation for one canonical key.

Given the values several sources report for the same (scheme, geo, period, metric), produce ONE
canonical value with the rule recorded — resolving conservatively (CLAUDE.md philosophy):

* **R4-REC-04** — one source only: take it; ``sources_seen`` has one entry, no disagreement.
* **R4-REC-01** — multiple sources within tolerance: they agree; take the most authoritative
  (lowest ``authority_rank``); no disagreement recorded.
* **R4-REC-02** — multiple sources disagree beyond tolerance: still take the most authoritative
  (a grounded source-priority rule adjudicates — DATA_CONTRACT §3), but RECORD the disagreement
  (max pairwise %, the rejected sources) in lineage. The rejected values are never discarded.

Tolerance is config-carried (``config.tolerance_for``); ``None`` means exact equality is required
(pure counts). Pure and deterministic — no I/O.
"""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.config import tolerance_for
from data_platform.harmonize.models import Disagreement, Reconciliation, SourceValue


def reconcile(values: list[SourceValue], *, metric: str) -> Reconciliation | None:
    """Reconcile the per-source values for one canonical key into a single outcome (or None)."""
    if not values:
        return None

    # Most authoritative source wins (lowest rank); ties broken by the latest as-of, then id, so
    # the choice is deterministic. This holds for both agreement and recorded disagreement.
    winner = min(values, key=_authority_key)

    if len(values) == 1:
        return Reconciliation(
            canonical_value=winner.value,
            source_id=winner.source_id,
            sources_seen=list(values),
            disagreement=None,
            resolution_rule_id="R4-REC-04",
        )

    tolerance = tolerance_for(metric)
    others = [v for v in values if v is not winner]
    worst_pct = max(_pct_diff(winner.value, other.value) for other in others)
    rejected = [
        other.source_id for other in others if not _agrees(winner.value, other.value, tolerance)
    ]

    if not rejected:  # every other source agrees with the winner
        return Reconciliation(
            canonical_value=winner.value,
            source_id=winner.source_id,
            sources_seen=list(values),
            disagreement=None,
            resolution_rule_id="R4-REC-01",
        )

    return Reconciliation(
        canonical_value=winner.value,
        source_id=winner.source_id,
        sources_seen=list(values),
        disagreement=Disagreement(pct=worst_pct, rejected_sources=rejected, rule_id="R4-REC-02"),
        resolution_rule_id="R4-REC-02",
    )


def _authority_key(value: SourceValue) -> tuple[int, float, str]:
    """Deterministic ordering: authority rank, then latest as-of, then source id."""
    # Negative timestamp so a LATER as_of sorts first (min-selection picks the winner).
    as_of = -value.source_as_of.timestamp() if value.source_as_of is not None else 0.0
    return (value.authority_rank, as_of, value.source_id)


def _pct_diff(winner: Decimal, other: Decimal) -> Decimal:
    """Absolute percentage difference of ``other`` from the winning value.

    When the winner is zero, an equal (zero) other is 0% apart; a non-zero other cannot be
    expressed as a finite percentage, so it is reported as the difference's own magnitude in
    percent (a large number) — enough to fall outside any tolerance and be recorded.
    """
    if winner == 0:
        return Decimal(0) if other == 0 else abs(other) * 100
    return abs(winner - other) / abs(winner) * 100


def _agrees(winner: Decimal, other: Decimal, tolerance: Decimal | None) -> bool:
    """Two values agree if equal, or (when a % band applies) within that band."""
    if winner == other:
        return True
    if tolerance is None:  # exact match required (pure counts)
        return False
    return _pct_diff(winner, other) <= tolerance
