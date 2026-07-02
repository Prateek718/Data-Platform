"""R4-Q-01 — a negative value for a non-negative metric is impossible and quarantined."""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.validate import HarmonizeQuarantineReason, impossible_reason


def test_negative_value_is_impossible() -> None:
    assert impossible_reason(Decimal("-1")) is HarmonizeQuarantineReason.NEGATIVE_VALUE
    assert impossible_reason(-5) is HarmonizeQuarantineReason.NEGATIVE_VALUE


def test_zero_and_positive_are_admissible() -> None:
    assert impossible_reason(Decimal("0")) is None
    assert impossible_reason(Decimal("94004")) is None


def test_missing_value_is_not_impossible() -> None:
    # null is honest absence, not an impossible value (null != 0).
    assert impossible_reason(None) is None
