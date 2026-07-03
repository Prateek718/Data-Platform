"""Series classification — basis + confidence derived from a reconciled outcome."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.models import Disagreement, Reconciliation, SourceValue
from data_platform.harmonize.series import Basis, Confidence, classify

_FLAGSHIP = "SRC_FLAGSHIP"


def _sv(source_id: str, value: str, rank: int) -> SourceValue:
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit="x",
        source_as_of=datetime(2025, 3, 7, tzinfo=UTC),
        authority_rank=rank,
    )


def _rec(
    sources: list[SourceValue],
    *,
    winner: SourceValue | None,
    disagreement: Disagreement | None = None,
    adjudicated: bool = True,
    rule: str = "R4-REC-01",
) -> Reconciliation:
    return Reconciliation(
        canonical_value=winner.value if winner else None,
        source_id=winner.source_id if winner else None,
        sources_seen=sources,
        disagreement=disagreement,
        resolution_rule_id=rule,
        adjudicated=adjudicated,
    )


def test_flagship_source_gives_flagship_rollup_basis() -> None:
    fl = _sv(_FLAGSHIP, "100", 0)
    basis, conf = classify(_rec([fl], winner=fl, rule="R4-REC-04"), flagship_source_id=_FLAGSHIP)
    assert basis is Basis.FLAGSHIP_ROLLUP
    assert conf is Confidence.SINGLE_SOURCE


def test_pre2018_multi_source_agreement_is_historical_multi_corroborated() -> None:
    a = _sv("SRC_MOSPI", "100", 10)
    b = _sv("SRC_RS", "100", 20)
    basis, conf = classify(_rec([a, b], winner=a), flagship_source_id=_FLAGSHIP)
    assert basis is Basis.HISTORICAL_MULTI
    assert conf is Confidence.CORROBORATED


def test_pre2018_single_source_is_historical_single() -> None:
    a = _sv("SRC_MOSPI", "100", 10)
    basis, conf = classify(_rec([a], winner=a, rule="R4-REC-04"), flagship_source_id=_FLAGSHIP)
    assert basis is Basis.HISTORICAL_SINGLE
    assert conf is Confidence.SINGLE_SOURCE


def test_disagreement_is_flagged() -> None:
    a = _sv("SRC_MOSPI", "100", 10)
    b = _sv("SRC_RS", "130", 20)
    d = Disagreement(pct=Decimal("30"), rejected_sources=["SRC_RS"], rule_id="R4-REC-02")
    basis, conf = classify(
        _rec([a, b], winner=a, disagreement=d, rule="R4-REC-02"), flagship_source_id=_FLAGSHIP
    )
    assert basis is Basis.HISTORICAL_MULTI
    assert conf is Confidence.FLAGGED_DISAGREEMENT


def test_unadjudicated_is_labelled_unadjudicated() -> None:
    fl = _sv(_FLAGSHIP, "100", 0)
    rs = _sv("SRC_RS", "130", 20)
    d = Disagreement(pct=Decimal("30"), rejected_sources=["SRC_RS"], rule_id="R4-REC-05")
    basis, conf = classify(
        _rec([fl, rs], winner=None, disagreement=d, adjudicated=False, rule="R4-REC-05"),
        flagship_source_id=_FLAGSHIP,
    )
    assert basis is Basis.FLAGSHIP_ROLLUP  # flagship is present, even though unadjudicated
    assert conf is Confidence.UNADJUDICATED


def test_coverage_summary_counts_eras_and_confidence() -> None:
    from data_platform.harmonize.config import WAGES_EXPENDITURE
    from data_platform.harmonize.models import CanonicalFact, CanonicalKey
    from data_platform.harmonize.series import series_coverage_summary, to_series_fact
    from data_platform.resolve.models import GeoLevel

    def fact(fy: str, sources: list[SourceValue]) -> CanonicalFact:
        key = CanonicalKey(
            scheme="MGNREGA",
            geo_level=GeoLevel.STATE,
            state_code="30",
            district_code=None,
            fin_year=fy,
            month=None,
            metric=WAGES_EXPENDITURE,
        )
        rec = Reconciliation(
            canonical_value=sources[0].value,
            source_id=sources[0].source_id,
            sources_seen=sources,
            disagreement=None,
            resolution_rule_id="R4-REC-01",
            adjudicated=True,
        )
        return CanonicalFact(
            key=key,
            value=sources[0].value,
            unit="INR lakh",
            reconciliation=rec,
            quarantined=False,
            quarantine_reason=None,
        )

    facts = [
        to_series_fact(
            fact("2015-16", [_sv("SRC_MOSPI", "10", 10), _sv("SRC_RS", "10", 20)]),
            flagship_source_id=_FLAGSHIP,
        ),
        to_series_fact(fact("2019-20", [_sv(_FLAGSHIP, "12", 0)]), flagship_source_id=_FLAGSHIP),
    ]
    s = series_coverage_summary(facts)[WAGES_EXPENDITURE]
    assert s["pre_2018"] == 1 and s["y2018_plus"] == 1
    assert s["corroborated"] == 1 and s["single_source"] == 1
