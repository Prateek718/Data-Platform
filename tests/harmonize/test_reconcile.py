"""R4-REC — cross-source reconciliation: agree, disagree-and-record, single-source, exact counts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.models import AggregateCoverage, SourceValue
from data_platform.harmonize.reconcile import reconcile

_AS_OF = datetime(2025, 3, 7, tzinfo=UTC)


def _sv(
    source_id: str,
    value: str,
    rank: int,
    *,
    epsilon: str = "0",
    coverage: AggregateCoverage | None = None,
) -> SourceValue:
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit="lakh",
        source_as_of=_AS_OF,
        authority_rank=rank,
        rounding_epsilon=Decimal(epsilon),
        aggregate_coverage=coverage,
    )


def test_no_values_returns_none() -> None:
    assert reconcile([], metric="persondays_generated") is None


def test_single_source_is_taken_with_no_disagreement() -> None:
    out = reconcile([_sv("SRC_FLAGSHIP", "94004", 0)], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("94004")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.disagreement is None
    assert len(out.sources_seen) == 1
    assert out.resolution_rule_id == "R4-REC-04"


def test_within_tolerance_agrees_and_takes_authoritative() -> None:
    # 94,004 vs 94,000 = 0.004% < 0.5% → agree; flagship (rank 0) wins over RS (rank 1).
    flagship = _sv("SRC_FLAGSHIP", "94004", 0)
    rs = _sv("SRC_RS", "94000", 1)
    out = reconcile([rs, flagship], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("94004")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.disagreement is None
    assert out.resolution_rule_id == "R4-REC-01"
    assert {s.source_id for s in out.sources_seen} == {"SRC_FLAGSHIP", "SRC_RS"}


def test_beyond_tolerance_records_disagreement_but_keeps_authoritative() -> None:
    # 100 vs 130 = 30% > 0.5% → disagree; authoritative flagship value still chosen, RS recorded.
    flagship = _sv("SRC_FLAGSHIP", "100", 0)
    rs = _sv("SRC_RS", "130", 1)
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("100")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.disagreement is not None
    assert out.disagreement.pct == Decimal("30")
    assert out.disagreement.rejected_sources == ["SRC_RS"]


def test_pure_count_requires_exact_equality() -> None:
    # active_workers is a pure count: a 1-unit difference is a disagreement, not agreement.
    a = _sv("SRC_FLAGSHIP", "1000", 0)
    b = _sv("SRC_RS", "1001", 1)
    out = reconcile([a, b], metric="active_workers")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.disagreement is not None


def test_pure_count_exact_match_agrees() -> None:
    a = _sv("SRC_FLAGSHIP", "1000", 0)
    b = _sv("SRC_RS", "1000", 1)
    out = reconcile([a, b], metric="active_workers")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-01"
    assert out.disagreement is None


def test_within_rounding_epsilon_agrees_even_beyond_percentage_band() -> None:
    # 719 vs 1000 is 39% apart (way beyond 0.5%), but RS's ±500 rounding slack covers it → agree.
    flagship = _sv("SRC_FLAGSHIP", "719", 0)
    rs = _sv("SRC_RS", "1000", 1, epsilon="500")
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-01"
    assert out.disagreement is None


def _coverage(summed: int, universe: int, lgd: int) -> AggregateCoverage:
    return AggregateCoverage(
        units_summed=summed, units_in_source_universe=universe, units_in_lgd=lgd
    )


def test_structural_gap_aggregate_vs_native_peer_is_unadjudicated() -> None:
    # Flagship rollup covers only 34 of 36 LGD districts (structural gap) and disagrees with a
    # whole-state RS peer → no winner is picked; the divergence is published (R4-REC-05).
    flagship = _sv("SRC_FLAGSHIP", "71123421", 0, coverage=_coverage(34, 34, 36))
    rs = _sv("SRC_RS", "82530000", 1)  # native whole-state, no aggregate_coverage
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-05"
    assert out.adjudicated is False
    assert out.canonical_value is None
    assert out.source_id is None
    assert len(out.sources_seen) == 2  # both still published


def test_complete_aggregate_disagreement_is_still_adjudicated() -> None:
    # A COMPLETE flagship rollup (all districts) that disagrees is a genuine revision → R4-REC-02.
    flagship = _sv("SRC_FLAGSHIP", "193524566", 0, coverage=_coverage(30, 30, 30))
    rs = _sv("SRC_RS", "197763000", 1)
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.adjudicated is True
    assert out.canonical_value == Decimal("193524566")


def test_structural_gap_without_a_native_peer_stays_adjudicated() -> None:
    # If the only peer is ALSO an aggregate (no whole-geography reference), there is nothing better
    # to defer to — keep the authoritative value and record the disagreement (not R4-REC-05).
    a = _sv("SRC_FLAGSHIP", "71123421", 0, coverage=_coverage(34, 34, 36))
    b = _sv("SRC_OTHER", "82530000", 1, coverage=_coverage(20, 20, 36))
    out = reconcile([a, b], metric="persondays_generated")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.adjudicated is True


def test_coverage_status_classification() -> None:
    from data_platform.harmonize.models import CoverageStatus

    assert _coverage(30, 30, 30).status is CoverageStatus.COMPLETE
    assert _coverage(34, 34, 36).status is CoverageStatus.STRUCTURAL_GAP  # universe < lgd
    assert _coverage(28, 33, 33).status is CoverageStatus.YEAR_GAP  # summed < universe
