"""R4-Q-01 — impossible values quarantined: negative single values, and cross-metric implausible
person-days (person-days above the active-workers × days-in-year ceiling)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.config import ACTIVE_WORKERS, PERSONDAYS_GENERATED
from data_platform.harmonize.models import (
    CanonicalFact,
    CanonicalKey,
    Reconciliation,
    SourceValue,
)
from data_platform.harmonize.validate import (
    HarmonizeQuarantineReason,
    flag_implausible_persondays,
    impossible_reason,
)
from data_platform.resolve.models import GeoLevel


def test_negative_value_is_impossible() -> None:
    assert impossible_reason(Decimal("-1")) is HarmonizeQuarantineReason.NEGATIVE_VALUE
    assert impossible_reason(-5) is HarmonizeQuarantineReason.NEGATIVE_VALUE


def test_zero_and_positive_are_admissible() -> None:
    assert impossible_reason(Decimal("0")) is None
    assert impossible_reason(Decimal("94004")) is None


def test_missing_value_is_not_impossible() -> None:
    # null is honest absence, not an impossible value (null != 0).
    assert impossible_reason(None) is None


def _fact(metric: str, value: Decimal) -> CanonicalFact:
    key = CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code="30",
        district_code=None,
        fin_year="2022-23",
        month=None,
        metric=metric,
    )
    sv = SourceValue(
        source_id="SRC_FLAGSHIP",
        value=value,
        original_unit="x",
        source_as_of=datetime(2025, 3, 7, tzinfo=UTC),
        authority_rank=0,
    )
    rec = Reconciliation(
        canonical_value=value,
        source_id="SRC_FLAGSHIP",
        sources_seen=[sv],
        disagreement=None,
        resolution_rule_id="R4-REC-04",
        adjudicated=True,
    )
    return CanonicalFact(
        key=key,
        value=value,
        unit="x",
        reconciliation=rec,
        quarantined=False,
        quarantine_reason=None,
    )


def test_persondays_above_worker_ceiling_is_quarantined() -> None:
    # 1000 workers × 366 days = 366,000 max person-days; 400,000 is impossible.
    facts = [_fact(PERSONDAYS_GENERATED, Decimal("400000")), _fact(ACTIVE_WORKERS, Decimal("1000"))]
    out = flag_implausible_persondays(facts)
    pd = next(f for f in out if f.key.metric == PERSONDAYS_GENERATED)
    assert pd.quarantined is True
    assert pd.quarantine_reason == "implausible_persondays"
    # the workers fact is untouched
    aw = next(f for f in out if f.key.metric == ACTIVE_WORKERS)
    assert aw.quarantined is False


def test_plausible_persondays_passes_through() -> None:
    facts = [_fact(PERSONDAYS_GENERATED, Decimal("40000")), _fact(ACTIVE_WORKERS, Decimal("1000"))]
    out = flag_implausible_persondays(facts)
    assert all(not f.quarantined for f in out)


def test_no_workers_fact_means_no_cross_metric_check() -> None:
    facts = [_fact(PERSONDAYS_GENERATED, Decimal("400000"))]  # workers absent → cannot check
    out = flag_implausible_persondays(facts)
    assert out[0].quarantined is False
