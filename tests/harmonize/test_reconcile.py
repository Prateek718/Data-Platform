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
    # 100,000 vs 130,000 = 30% > 0.5% and a material 30,000 spread → disagree; authoritative
    # flagship value still chosen, RS recorded (two distinct publishers → R4-REC-02).
    flagship = _sv("SRC_FLAGSHIP", "100000", 0)
    rs = _sv("SRC_RS", "130000", 1)
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("100000")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.disagreement is not None
    assert out.disagreement.pct == Decimal("30")
    assert out.disagreement.material is True
    assert out.disagreement.rejected_sources == ["SRC_RS"]


def test_pure_count_requires_exact_equality() -> None:
    # active_workers is a pure count: values that differ MATERIALLY (absolute + relative) do not
    # agree, and with two distinct publishers this records a disagreement (R4-REC-02).
    a = _sv("SRC_FLAGSHIP", "1000000", 0)
    b = _sv("SRC_RS", "1200000", 1)
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


# ---- R4-REC-06: literal-zero against a non-zero peer is coverage-absent, not a disagreement ----
def test_zero_against_nonzero_peer_is_coverage_absent_not_conflict() -> None:
    # A source reporting 0 for a cell where a peer reports 53,864 is a MISSING cell — excluded from
    # comparison and recorded, not flagged as a 5,000,000% disagreement.
    zero = _sv("SRC_MOSPI", "0", 10)
    real = _sv("SRC_MOSPI", "53864", 10)
    out = reconcile([zero, real], metric="households_completed_100_days")
    assert out is not None
    assert out.canonical_value == Decimal("53864")
    assert out.disagreement is None  # the 0 is absent, not a disagreeing peer
    assert out.resolution_rule_id == "R4-REC-06"
    assert [s.value for s in out.coverage_absent] == [Decimal("0")]
    assert len(out.sources_seen) == 2  # the 0 is still published


def test_all_zero_is_a_genuine_agreed_zero() -> None:
    a = _sv("SRC_MOSPI", "0", 10)
    b = _sv("SRC_RS", "0", 10)
    out = reconcile([a, b], metric="households_completed_100_days")
    assert out is not None
    assert out.canonical_value == Decimal("0")
    assert out.coverage_absent == []
    assert out.disagreement is None


# ---- R4-REC-07: a value that is a corroborated cluster / 10^k is a dropped-digit scale error ----
def test_ten_x_low_value_against_cross_publisher_cluster_is_quarantined() -> None:
    # RS and MoSPI corroborate ~539,000; a 53,890 (=/10) value is a dropped-digit scale error →
    # quarantined, not averaged/flagged in. Winner is the corroborated value.
    rs = _sv("SRC_RS", "539000", 10, epsilon="500")
    mospi = _sv("SRC_MOSPI", "539223", 10)
    bad_a = _sv("SRC_MOSPI", "53890", 10)
    bad_b = _sv("SRC_MOSPI", "53890", 10)
    out = reconcile([rs, mospi, bad_a, bad_b], metric="households_employed")
    assert out is not None
    assert out.canonical_value in (Decimal("539000"), Decimal("539223"))
    assert out.resolution_rule_id == "R4-REC-07"
    assert sorted(s.value for s in out.scale_quarantined) == [Decimal("53890"), Decimal("53890")]
    assert out.disagreement is None  # the survivors corroborate


def test_scale_quarantine_needs_two_distinct_publishers_anchor() -> None:
    # Same-publisher-only cluster does NOT anchor a scale quarantine (could be the wrong side).
    a = _sv("SRC_MOSPI", "539000", 10)
    b = _sv("SRC_MOSPI", "539223", 10)
    bad = _sv("SRC_MOSPI", "53890", 10)
    out = reconcile([a, b, bad], metric="households_employed")
    assert out is not None
    assert out.scale_quarantined == []  # not quarantined — no independent anchor


# ---- R4-REC-08: an absolute spread below the materiality floor is a non-material swing ----
def test_near_zero_swing_is_immaterial() -> None:
    # 77 vs 174 completers = 126% but a 97-hh spread (< 1,000 floor) → recorded, not material.
    a = _sv("SRC_MOSPI", "77", 10)
    b = _sv("SRC_MOSPI", "174", 10)
    out = reconcile([a, b], metric="households_completed_100_days")
    assert out is not None
    assert out.disagreement is not None
    assert out.disagreement.material is False
    assert out.resolution_rule_id == "R4-REC-08"
    assert out.canonical_value is not None  # a value is still kept (not suppressed)


def test_large_base_tiny_percent_disagreement_is_immaterial() -> None:
    # 2,174,000 vs 2,176,000: a 2,000 spread clears the 1,000 absolute floor but is 0.09% (< 1%) on
    # a 2.1M base — a rounding-level split between lakh vintages, not a material conflict.
    a = _sv("SRC_MOSPI", "2174000", 10)
    b = _sv("SRC_RS", "2176000", 10)
    out = reconcile([a, b], metric="households_employed")
    assert out is not None
    assert out.disagreement is not None
    assert out.disagreement.material is False
    assert out.resolution_rule_id == "R4-REC-08"


# ---- R4-REC-09: a material disagreement among ONE publisher's vintages is unadjudicated ----
def test_single_publisher_material_divergence_is_unadjudicated() -> None:
    # Two MoSPI vintages disagree materially (7,512 vs 69,264); no independent publisher to
    # adjudicate → no winner invented, divergence published.
    a = _sv("SRC_MOSPI", "7512", 10)
    b = _sv("SRC_MOSPI", "69264", 10)
    out = reconcile([a, b], metric="households_completed_100_days")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-09"
    assert out.adjudicated is False
    assert out.canonical_value is None
    assert out.disagreement is not None and out.disagreement.material is True
    assert len(out.sources_seen) == 2


def test_cross_publisher_material_divergence_still_flags_with_winner() -> None:
    # Two DISTINCT publishers disagree materially → genuine conflict: keep value + flag.
    a = _sv("SRC_MOSPI", "7512", 10)
    b = _sv("SRC_RS", "69264", 11)
    out = reconcile([a, b], metric="households_completed_100_days")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.adjudicated is True
    assert out.canonical_value is not None
    assert out.disagreement is not None and out.disagreement.material is True


def _ed(
    value: str, span_end: str, *, terminal: bool = False, source_id: str = "SRC_MOSPI"
) -> SourceValue:
    """A same-publisher EDITION value: same source_id, ranked by ``span_end`` (a later edition)."""
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit="lakh",
        source_as_of=None,  # edition files carry no as-of; ordering is span-end, not date
        authority_rank=10,
        edition_span_end=span_end,
        is_edition_terminal=terminal,
    )


# ---- R4-REC-10: a later edition of the same publisher's table supersedes earlier editions --------
def test_later_edition_supersedes_earlier_restated_finals() -> None:
    # Three MoSPI editions carry FY-final wages: the two earlier (span-ends 2014-15, 2015-16) agree
    # at 500000; the latest (2017-18) restated it to 508000 (>0.5% apart). The latest edition wins;
    # the two superseded editions are recorded (not a conflict, not rejected-in-disagreement).
    e16 = _ed("500000", "2014-15")
    e17 = _ed("500000", "2015-16")
    e18 = _ed("508000", "2017-18")
    out = reconcile([e16, e17, e18], metric="wages_expenditure")
    assert out is not None
    assert out.canonical_value == Decimal("508000")
    assert out.resolution_rule_id == "R4-REC-10"
    assert out.adjudicated is True
    assert out.disagreement is None  # superseded editions are not a disagreement
    assert sorted(s.value for s in out.edition_superseded) == [Decimal("500000"), Decimal("500000")]
    assert len(out.sources_seen) == 3  # every edition still published


def test_agreeing_editions_are_corroboration_not_supersession() -> None:
    # Editions that AGREE are single-publisher corroboration, NOT a supersession: no R4-REC-10, no
    # superseded bucket — just the latest-edition value taken with the earlier one corroborating.
    early = _ed("500000", "2014-15")
    late = _ed("500000", "2017-18")
    out = reconcile([early, late], metric="wages_expenditure")
    assert out is not None
    assert out.canonical_value == Decimal("500000")
    assert out.resolution_rule_id == "R4-REC-01"
    assert out.edition_superseded == []
    assert out.disagreement is None


def test_edition_supersession_does_not_apply_without_markers() -> None:
    # Same publisher, no edition markers → NOT an edition family: a material divergence stays
    # R4-REC-09 (unadjudicated), never silently resolved by a fabricated latest-wins.
    a = _sv("SRC_MOSPI", "500000", 10)
    b = _sv("SRC_MOSPI", "508000", 10)
    out = reconcile([a, b], metric="wages_expenditure")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-09"
    assert out.edition_superseded == []


def test_edition_winner_then_cross_publisher_peer_agrees() -> None:
    # After the MoSPI editions collapse to the latest (508000), an independent RS peer agreeing at
    # 508000 is genuine cross-publisher corroboration; the superseded earlier edition stays lineage.
    e16 = _ed("500000", "2014-15")
    e18 = _ed("508000", "2017-18")
    rs = _sv("SRC_RS", "508000", 10)
    out = reconcile([e16, e18, rs], metric="wages_expenditure")
    assert out is not None
    assert out.canonical_value == Decimal("508000")
    assert out.resolution_rule_id == "R4-REC-10"
    assert out.disagreement is None
    assert [s.value for s in out.edition_superseded] == [Decimal("500000")]
    assert {s.source_id for s in out.sources_seen} == {"SRC_MOSPI", "SRC_RS"}


def test_edition_winner_still_flags_material_cross_publisher_conflict() -> None:
    # Collapse the MoSPI editions to the latest (508000); if the independent RS peer then disagrees
    # materially (620000), that residual cross-publisher conflict is flagged (R4-REC-02) — the
    # edition supersession is recorded alongside, not instead.
    e16 = _ed("500000", "2014-15")
    e18 = _ed("508000", "2017-18")
    rs = _sv("SRC_RS", "620000", 11)
    out = reconcile([e16, e18, rs], metric="wages_expenditure")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.canonical_value == Decimal("508000")  # latest edition beats RS on authority rank
    assert out.disagreement is not None and out.disagreement.material is True
    assert [s.value for s in out.edition_superseded] == [Decimal("500000")]


# ---- R4-REC-11: an edition's terminal-year mid-year partial is excluded when a later edition -----
#      carries that year in full.
def test_terminal_year_partial_excluded_when_later_edition_carries_it_full() -> None:
    # The 2014-15 cell: the SYB2016 edition's value (300000) is its terminal year — a documented
    # mid-year partial. The SYB2018 edition carries 2014-15 as a NON-terminal full year (345000).
    # The partial is excluded first (not compared, not flagged); the full-year edition stands.
    partial = _ed("300000", "2014-15", terminal=True)
    full = _ed("345000", "2017-18", terminal=False)
    out = reconcile([partial, full], metric="wages_expenditure")
    assert out is not None
    assert out.canonical_value == Decimal("345000")
    assert out.resolution_rule_id == "R4-REC-11"
    assert [s.value for s in out.partial_period] == [Decimal("300000")]
    assert out.disagreement is None
    assert len(out.sources_seen) == 2


def test_terminal_year_kept_when_no_later_edition_supersedes_it() -> None:
    # An edition's terminal year with NO later edition covering it (its own latest year) is the only
    # value there — kept as-is (single source), never excluded into nothing.
    only = _ed("400000", "2017-18", terminal=True)
    out = reconcile([only], metric="wages_expenditure")
    assert out is not None
    assert out.canonical_value == Decimal("400000")
    assert out.resolution_rule_id == "R4-REC-04"
    assert out.partial_period == []
