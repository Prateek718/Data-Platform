"""R4-DEF-01 — total_expenditure derived from components, compared to any source-provided total."""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.definition import derive_and_compare

_TOL = Decimal("0.5")


def test_derived_is_sum_of_components() -> None:
    derived, disc = derive_and_compare(
        [Decimal("100"), Decimal("50"), Decimal("10")], None, tolerance=_TOL
    )
    assert derived == Decimal("160")
    assert disc is None  # no source total to compare


def test_source_total_within_tolerance_records_no_discrepancy() -> None:
    derived, disc = derive_and_compare(
        [Decimal("100"), Decimal("50"), Decimal("10")], Decimal("160.5"), tolerance=_TOL
    )
    assert derived == Decimal("160")
    assert disc is None


def test_source_total_beyond_tolerance_records_discrepancy_but_keeps_derived() -> None:
    derived, disc = derive_and_compare(
        [Decimal("100"), Decimal("50"), Decimal("10")], Decimal("200"), tolerance=_TOL
    )
    assert derived == Decimal("160")  # canonical is still the derived value
    assert disc is not None
    assert disc.source_provided == Decimal("200")
    assert disc.derived == Decimal("160")
    assert disc.rule_id == "R4-DEF-01"
    assert disc.pct == Decimal("25")  # |160-200|/160 * 100


def test_zero_derived_with_nonzero_source_is_a_discrepancy() -> None:
    derived, disc = derive_and_compare([Decimal("0")], Decimal("5"), tolerance=_TOL)
    assert derived == Decimal("0")
    assert disc is not None
