"""R4-REC — cross-source value reconciliation for one canonical key.

Given the values several sources report for the same (scheme, geo, period, metric), produce ONE
canonical value with the rule recorded — resolving conservatively (CLAUDE.md philosophy):

* **R4-REC-04** — one source only: take it; ``sources_seen`` has one entry, no disagreement.
* **R4-REC-01** — multiple sources agree: take the most authoritative (lowest ``authority_rank``);
  no disagreement. Agreement is within the config-carried percentage band OR within the coarser
  source's published rounding (its ``rounding_epsilon``) — so rounding a tiny value to the nearest
  lakh is not mistaken for a conflict (R4-REC-01a).
* **R4-REC-02** — multiple sources disagree beyond tolerance AND the authoritative source is a
  whole-geography value (or a COMPLETE aggregate): take it (a grounded source-priority rule
  adjudicates — DATA_CONTRACT §3), but RECORD the disagreement (max pairwise %, rejected sources).
* **R4-REC-05** — disagreement where the authoritative source is a STRUCTURALLY-INCOMPLETE
  aggregate (its unit universe is smaller than the geography's, so its rolled-up total is a partial
  sum) AND a natively whole-geography peer exists: the authority premise is void, so DO NOT pick a
  winner — the outcome is UNADJUDICATED (no canonical value), the divergence published instead.

Pure and deterministic — no I/O.
"""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.config import tolerance_for
from data_platform.harmonize.models import (
    CoverageStatus,
    Disagreement,
    Reconciliation,
    SourceValue,
)


def reconcile(values: list[SourceValue], *, metric: str) -> Reconciliation | None:
    """Reconcile the per-source values for one canonical key into a single outcome (or None)."""
    if not values:
        return None

    # Most authoritative source wins (lowest rank); ties broken by latest as-of, then id.
    winner = min(values, key=_authority_key)

    if len(values) == 1:
        return _adjudicated(winner, list(values), None, "R4-REC-04")

    tolerance = tolerance_for(metric)
    others = [v for v in values if v is not winner]
    worst_pct = max(_pct_diff(winner.value, other.value) for other in others)
    rejected = [other.source_id for other in others if not _agrees(winner, other, tolerance)]

    if not rejected:  # every other source agrees with the winner
        return _adjudicated(winner, list(values), None, "R4-REC-01")

    disagreement_r2 = Disagreement(pct=worst_pct, rejected_sources=rejected, rule_id="R4-REC-02")
    if _is_structurally_incomplete_aggregate(winner) and _has_native_peer(others):
        # R4-REC-05: the authoritative value is a partial (structurally-incomplete) rollup and a
        # whole-geography peer disagrees — do not canonicalize the partial sum; publish divergence.
        return Reconciliation(
            canonical_value=None,
            source_id=None,
            sources_seen=list(values),
            disagreement=Disagreement(
                pct=worst_pct, rejected_sources=rejected, rule_id="R4-REC-05"
            ),
            resolution_rule_id="R4-REC-05",
            adjudicated=False,
        )
    return Reconciliation(
        canonical_value=winner.value,
        source_id=winner.source_id,
        sources_seen=list(values),
        disagreement=disagreement_r2,
        resolution_rule_id="R4-REC-02",
        adjudicated=True,
    )


def _adjudicated(
    winner: SourceValue,
    sources_seen: list[SourceValue],
    disagreement: Disagreement | None,
    rule_id: str,
) -> Reconciliation:
    return Reconciliation(
        canonical_value=winner.value,
        source_id=winner.source_id,
        sources_seen=sources_seen,
        disagreement=disagreement,
        resolution_rule_id=rule_id,
        adjudicated=True,
    )


def _is_structurally_incomplete_aggregate(value: SourceValue) -> bool:
    coverage = value.aggregate_coverage
    return coverage is not None and coverage.status is CoverageStatus.STRUCTURAL_GAP


def _has_native_peer(others: list[SourceValue]) -> bool:
    """True if some peer is a natively whole-geography value (not itself an aggregate)."""
    return any(other.aggregate_coverage is None for other in others)


def _authority_key(value: SourceValue) -> tuple[int, float, str]:
    """Deterministic ordering: authority rank, then latest as-of, then source id."""
    as_of = -value.source_as_of.timestamp() if value.source_as_of is not None else 0.0
    return (value.authority_rank, as_of, value.source_id)


def _pct_diff(winner: Decimal, other: Decimal) -> Decimal:
    """Absolute percentage difference of ``other`` from the winning value (0-winner handled)."""
    if winner == 0:
        return Decimal(0) if other == 0 else abs(other) * 100
    return abs(winner - other) / abs(winner) * 100


def _agrees(winner: SourceValue, other: SourceValue, tolerance: Decimal | None) -> bool:
    """Two values agree if equal, within the coarser source's rounding, or within the % band."""
    if winner.value == other.value:
        return True
    # R4-REC-01a: within the coarser source's published rounding granularity → agreement.
    epsilon = max(winner.rounding_epsilon, other.rounding_epsilon)
    if epsilon > 0 and abs(winner.value - other.value) <= epsilon:
        return True
    if tolerance is None:  # exact match required (pure counts) and not within epsilon
        return False
    return _pct_diff(winner.value, other.value) <= tolerance
