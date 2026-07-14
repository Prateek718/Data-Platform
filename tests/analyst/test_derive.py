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


def test_to_billions_is_a_declared_operation_not_prose_rounding() -> None:
    """A presentation form is a DERIVATION the verifier recomputes, not the drafter rounding."""
    assert derive.compute(derive.TO_BILLIONS, [Decimal("3881318918")]) == Decimal("3.88")


def test_to_millions() -> None:
    assert derive.compute(derive.TO_MILLIONS, [Decimal("75500579")]) == Decimal("75.50")


def test_lakh_to_crore() -> None:
    """Indian money units: 1 crore = 100 lakh."""
    assert derive.compute(derive.LAKH_TO_CRORE, [Decimal("10999798.601773694")]) == Decimal(
        "109997.99"
    )


def test_lakh_to_lakh_crore() -> None:
    """1 lakh crore = 10,000,000 lakh. The peak year's spend reads as Rs 1.10 lakh crore."""
    assert derive.compute(derive.LAKH_TO_LAKH_CRORE, [Decimal("10999798.601773694")]) == Decimal(
        "1.10"
    )


def test_round_sigfig_3() -> None:
    assert derive.compute(derive.ROUND_SIGFIG_3, [Decimal("905054000")]) == Decimal("905000000")
    assert derive.compute(derive.ROUND_SIGFIG_3, [Decimal("3.14159")]) == Decimal("3.14")


@pytest.mark.parametrize(
    "operation",
    [derive.TO_MILLIONS, derive.TO_BILLIONS, derive.LAKH_TO_CRORE, derive.ROUND_SIGFIG_3],
)
def test_presentation_operations_are_unary(operation: str) -> None:
    with pytest.raises(ValueError, match="exactly 1 input"):
        derive.compute(operation, [Decimal("1"), Decimal("2")])


def test_round_2dp_is_a_declared_rounding() -> None:
    """383.782169313422 INR reads as 383.78 in prose — because code rounded it, not the drafter."""
    assert derive.compute(derive.ROUND_2DP, [Decimal("383.782169313422")]) == Decimal("383.78")
    assert derive.ROUND_2DP in derive.PRESENTATION_OPERATIONS
