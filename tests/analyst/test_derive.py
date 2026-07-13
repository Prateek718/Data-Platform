"""Derived figures are exact, named, and never guessed."""

from __future__ import annotations

from decimal import Decimal

import pytest

from data_platform.analyst import derive


def test_sum_is_exact() -> None:
    assert derive.compute(derive.SUM, [Decimal("42253"), Decimal("51751")]) == Decimal("94004")


def test_sum_of_decimals_does_not_drift() -> None:
    """Binary float would make this 422.18067470000004; a report figure must reconcile exactly."""
    parts = [Decimal("196.74055"), Decimal("225.4401247")]
    assert derive.compute(derive.SUM, parts) == Decimal("422.1806747")


def test_difference() -> None:
    assert derive.compute(derive.DIFFERENCE, [Decimal("94004"), Decimal("94004")]) == Decimal("0")


def test_ratio() -> None:
    ratio = derive.compute(derive.RATIO, [Decimal("300000"), Decimal("1000000")])
    assert ratio == Decimal("0.3")


def test_unknown_operation_is_an_error_not_a_guess() -> None:
    with pytest.raises(ValueError, match="unknown operation"):
        derive.compute("average", [Decimal("1")])


def test_ratio_rejects_a_zero_denominator() -> None:
    with pytest.raises(ValueError, match="zero denominator"):
        derive.compute(derive.RATIO, [Decimal("1"), Decimal("0")])


@pytest.mark.parametrize("operation", [derive.DIFFERENCE, derive.RATIO])
def test_binary_operations_reject_wrong_arity(operation: str) -> None:
    with pytest.raises(ValueError, match="exactly 2 inputs"):
        derive.compute(operation, [Decimal("1"), Decimal("2"), Decimal("3")])


def test_ratio_2dp_rounds_in_the_operation_not_in_the_prose() -> None:
    """A 28-digit ratio is precision the claim does not have; rounding is a DECLARED step here."""
    exact = derive.compute(derive.RATIO, [Decimal("3881318918"), Decimal("905054000")])
    assert str(exact).startswith("4.28849429757782408563466931")
    assert derive.compute(derive.RATIO_2DP, [Decimal("3881318918"), Decimal("905054000")]) == (
        Decimal("4.29")
    )
