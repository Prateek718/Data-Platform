"""R4-REC — cross-source value reconciliation for one canonical key.

Given the values several sources report for the same (scheme, geo, period, metric), produce ONE
canonical value with the rule recorded — resolving conservatively (CLAUDE.md philosophy). Before
adjudicating, two structural NON-PARTICIPANTS are removed (they are not disagreeing peers):

* **R4-REC-06** — coverage-absent: a source reporting ``0`` where a peer reports a non-zero value is
  a MISSING cell, not a disagreement — recorded in ``coverage_absent`` and excluded from comparison.
  (All sources reporting ``0`` is a genuine agreed zero.)
* **R4-REC-11** — documented-terminal-partial exclusion: within a same-publisher EDITION FAMILY, an
  edition's terminal-year value is a DOCUMENTED mid-year partial (the marker, not the value, is the
  trigger). It is excluded (``partial_period``) before comparison — whether a LATER edition
  carries that year in full, OR no edition does (a family-terminal with no successor: the cell is
  withheld, value ``None``, not published as an annual). A period mismatch, not a disagreement.
* **R4-REC-10** — edition supersession: among the remaining editions of the family, the LATEST
  (largest span end) is authoritative for a year it carries as final; any earlier edition it
  restated is recorded in ``edition_superseded`` (retained lineage, not a conflict, not rejected).
  Independent-publisher peers are untouched and still reconcile normally against the latest edition.
* **R4-REC-07** — scale-error quarantine: when ≥2 DISTINCT publishers corroborate a value and
  another contribution equals it ÷ 10^k, that contribution is a dropped-digit error — quarantined in
  ``scale_quarantined`` and excluded (never averaged in).

Then the survivors are adjudicated:

* **R4-REC-04 / R4-REC-01** — one survivor / all agree: take it, no disagreement.
* **R4-REC-08** — the survivors disagree but the largest ABSOLUTE spread is below the metric's
  materiality floor: a near-zero swing — the value is kept but the disagreement is marked
  ``material=False`` (not a real conflict).
* **R4-REC-02** — a MATERIAL disagreement across ≥2 publishers where the authoritative source is
  whole-geography: take it (source-priority) and record the disagreement.
* **R4-REC-05** — material disagreement where the authoritative source is a structurally-incomplete
  aggregate and a native peer exists: UNADJUDICATED (divergence published, no value).
* **R4-REC-09** — a MATERIAL disagreement among a SINGLE publisher's vintages (no independent peer):
  UNADJUDICATED — no winner is invented, the divergence is published.

Pure and deterministic — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from data_platform.harmonize.config import (
    DEFAULT_TOLERANCE_PCT,
    SCALE_ERROR_FACTORS,
    materiality_floor_for,
    materiality_rel_pct_for,
    tolerance_for,
)
from data_platform.harmonize.models import (
    CoverageStatus,
    Disagreement,
    Reconciliation,
    SourceValue,
)


@dataclass(frozen=True)
class _Buckets:
    """Contributions removed before adjudication — recorded in lineage, never silently discarded."""

    coverage_absent: list[SourceValue]
    scale_quarantined: list[SourceValue]
    edition_superseded: list[SourceValue]
    partial_period: list[SourceValue]


def reconcile(values: list[SourceValue], *, metric: str) -> Reconciliation | None:
    """Reconcile the per-source values for one canonical key into a single outcome (or None)."""
    if not values:
        return None
    values = list(values)
    tolerance = tolerance_for(metric)

    # R4-REC-06: a 0 against a non-zero peer is a missing cell, not a disagreeing value.
    nonzero = [v for v in values if v.value != 0]
    coverage_absent = (
        [v for v in values if v.value == 0] if nonzero and len(nonzero) < len(values) else []
    )
    absent_ids = {id(v) for v in coverage_absent}
    active = [v for v in values if id(v) not in absent_ids]

    # R4-REC-11 then R4-REC-10: exclude each edition's terminal-year partial that a later edition
    # carries in full, then let the latest edition supersede earlier editions it restated.
    active, edition_superseded, partial_period = _normalize_editions(active, tolerance)

    # R4-REC-07: a corroborated-cluster ÷ 10^k value is a dropped-digit scale error.
    scale_quarantined = _scale_errors(active, tolerance)
    quarantined_ids = {id(v) for v in scale_quarantined}
    adjudicable = [v for v in active if id(v) not in quarantined_ids]

    buckets = _Buckets(coverage_absent, scale_quarantined, edition_superseded, partial_period)
    pre_rule = (
        "R4-REC-10"
        if edition_superseded
        else "R4-REC-11"
        if partial_period
        else "R4-REC-06"
        if coverage_absent
        else "R4-REC-07"
        if scale_quarantined
        else None
    )

    if not adjudicable:
        # Everything was excluded — the only readings were documented terminal partials (R4-REC-11).
        # No defensible annual value exists: withhold it, keeping the partials in lineage.
        return _partial_only(values, buckets) if partial_period else None

    winner = min(adjudicable, key=_authority_key)

    if len(adjudicable) == 1:
        return _adjudicated(winner, values, None, pre_rule or "R4-REC-04", buckets)

    others = [v for v in adjudicable if v is not winner]
    worst_pct = max(_pct_diff(winner.value, other.value) for other in others)
    rejected = [other.source_id for other in others if not _agrees(winner, other, tolerance)]

    if not rejected:  # every survivor agrees with the winner
        return _adjudicated(winner, values, None, pre_rule or "R4-REC-01", buckets)

    # R4-REC-08: a disagreement significant in neither absolute NOR relative terms is immaterial —
    # a near-zero swing or a rounding-level split on a large base. Material only if it clears BOTH.
    spread = max(v.value for v in adjudicable) - min(v.value for v in adjudicable)
    if spread < materiality_floor_for(metric) or worst_pct < materiality_rel_pct_for(metric):
        immaterial = Disagreement(
            pct=worst_pct, rejected_sources=rejected, rule_id="R4-REC-08", material=False
        )
        return _adjudicated(winner, values, immaterial, "R4-REC-08", buckets)

    # R4-REC-05: authoritative value is a structurally-incomplete rollup with a native peer.
    if _is_structurally_incomplete_aggregate(winner) and _has_native_peer(others):
        return _unadjudicated(values, worst_pct, rejected, "R4-REC-05", buckets)

    # R4-REC-09: material disagreement among a SINGLE publisher's vintages with NO groundable
    # edition hierarchy — no independent peer to adjudicate (edition families resolved above).
    if len({v.source_id for v in adjudicable}) == 1:
        return _unadjudicated(values, worst_pct, rejected, "R4-REC-09", buckets)

    # R4-REC-02: material disagreement across ≥2 publishers — take authoritative value, record it.
    return Reconciliation(
        canonical_value=winner.value,
        source_id=winner.source_id,
        sources_seen=values,
        disagreement=Disagreement(pct=worst_pct, rejected_sources=rejected, rule_id="R4-REC-02"),
        resolution_rule_id="R4-REC-02",
        adjudicated=True,
        coverage_absent=buckets.coverage_absent,
        scale_quarantined=buckets.scale_quarantined,
        edition_superseded=buckets.edition_superseded,
        partial_period=buckets.partial_period,
    )


def _normalize_editions(
    values: list[SourceValue], tolerance: Decimal | None
) -> tuple[list[SourceValue], list[SourceValue], list[SourceValue]]:
    """Collapse a same-publisher edition family: exclude terminal partials (R4-REC-11), then let the
    latest surviving edition supersede earlier ones (R4-REC-10).

    A value carries ``edition_span_end`` iff it belongs to an edition family (successive dated
    editions of one publisher's table). (R4-REC-11) an edition's terminal-year value is a DOCUMENTED
    mid-year partial — excluded whether a later edition carries that year in full OR no edition does
    (a family-terminal with no successor: withheld rather than published as an annual). The terminal
    marker is the trigger, never the value. Then (R4-REC-10) among the surviving NON-terminal
    editions the latest (max span end) is authoritative, and any earlier-edition final it RESTATED
    (disagrees beyond tolerance) is superseded — earlier editions that AGREE stay as corroboration.
    Independent peers (``edition_span_end is None``) pass through untouched. Returns
    (survivors, superseded, partial)."""
    family = [v for v in values if v.edition_span_end is not None]
    if not family:
        return values, [], []
    partial = [v for v in family if v.is_edition_terminal]
    finals = [v for v in family if not v.is_edition_terminal]
    superseded: list[SourceValue] = []
    if finals:
        winner = max(finals, key=lambda v: v.edition_span_end or "")
        superseded = [v for v in finals if v is not winner and not _agrees(winner, v, tolerance)]
    dropped = {id(v) for v in partial} | {id(v) for v in superseded}
    survivors = [v for v in values if id(v) not in dropped]
    return survivors, superseded, partial


def _adjudicated(
    winner: SourceValue,
    sources_seen: list[SourceValue],
    disagreement: Disagreement | None,
    rule_id: str,
    buckets: _Buckets,
) -> Reconciliation:
    return Reconciliation(
        canonical_value=winner.value,
        source_id=winner.source_id,
        sources_seen=sources_seen,
        disagreement=disagreement,
        resolution_rule_id=rule_id,
        adjudicated=True,
        coverage_absent=buckets.coverage_absent,
        scale_quarantined=buckets.scale_quarantined,
        edition_superseded=buckets.edition_superseded,
        partial_period=buckets.partial_period,
    )


def _partial_only(sources_seen: list[SourceValue], buckets: _Buckets) -> Reconciliation:
    """No survivor after edition normalization — the only readings were documented terminal
    partials (R4-REC-11). Value withheld; the excluded partials are kept in lineage."""
    return Reconciliation(
        canonical_value=None,
        source_id=None,
        sources_seen=sources_seen,
        disagreement=None,
        resolution_rule_id="R4-REC-11",
        adjudicated=False,
        coverage_absent=buckets.coverage_absent,
        scale_quarantined=buckets.scale_quarantined,
        edition_superseded=buckets.edition_superseded,
        partial_period=buckets.partial_period,
    )


def _unadjudicated(
    sources_seen: list[SourceValue],
    worst_pct: Decimal,
    rejected: list[str],
    rule_id: str,
    buckets: _Buckets,
) -> Reconciliation:
    return Reconciliation(
        canonical_value=None,
        source_id=None,
        sources_seen=sources_seen,
        disagreement=Disagreement(pct=worst_pct, rejected_sources=rejected, rule_id=rule_id),
        resolution_rule_id=rule_id,
        adjudicated=False,
        coverage_absent=buckets.coverage_absent,
        scale_quarantined=buckets.scale_quarantined,
        edition_superseded=buckets.edition_superseded,
        partial_period=buckets.partial_period,
    )


def _scale_errors(active: list[SourceValue], tolerance: Decimal | None) -> list[SourceValue]:
    """Values that are a cross-publisher-corroborated cluster ÷ 10^k — dropped-digit scale errors.

    The anchor must be corroborated by ≥2 DISTINCT publishers (an independent cluster we can trust);
    then any active value equal to that cluster's value ÷/× a power of ten (and NOT itself agreeing)
    is a scale error. Same-publisher-only clusters do not anchor (they could be the wrong side).
    """
    for anchor in active:
        peers = [v for v in active if v is not anchor and _agrees(anchor, v, tolerance)]
        publishers = {anchor.source_id} | {p.source_id for p in peers}
        if not peers or len(publishers) < 2:
            continue
        errors = [
            v
            for v in active
            if not _agrees(v, anchor, tolerance) and _is_scale_multiple(v.value, anchor.value)
        ]
        if errors:
            return errors
    return []


def _is_scale_multiple(value: Decimal, anchor: Decimal) -> bool:
    """True if ``value`` is ``anchor`` off by a clean power of ten (a dropped/added digit)."""
    if value == 0 or anchor == 0:
        return False
    return any(
        _pct_diff(anchor, value * factor) <= DEFAULT_TOLERANCE_PCT
        or _pct_diff(anchor, value / factor) <= DEFAULT_TOLERANCE_PCT
        for factor in SCALE_ERROR_FACTORS
    )


def _is_structurally_incomplete_aggregate(value: SourceValue) -> bool:
    coverage = value.aggregate_coverage
    return coverage is not None and coverage.status is CoverageStatus.STRUCTURAL_GAP


def _has_native_peer(others: list[SourceValue]) -> bool:
    """True if some peer is a natively whole-geography value (not itself an aggregate)."""
    return any(other.aggregate_coverage is None for other in others)


def _authority_key(value: SourceValue) -> tuple[int, float, int, str]:
    """Deterministic ordering: authority rank, then latest as-of, then latest edition, then id.

    Edition files carry no as-of, so a same-publisher family is ordered by ``edition_span_end``
    (a later edition supersedes an earlier one); non-edition peers sort by id as before."""
    as_of = -value.source_as_of.timestamp() if value.source_as_of is not None else 0.0
    edition = -int(value.edition_span_end[:4]) if value.edition_span_end else 0
    return (value.authority_rank, as_of, edition, value.source_id)


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
