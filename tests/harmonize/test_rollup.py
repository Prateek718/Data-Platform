"""Cumulative-YTD → FY-final rollup: take the financial-year-final value, never sum monthlies."""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.rollup import fy_final_of_cumulative


def test_takes_march_final_not_the_sum() -> None:
    # A full FY of monotonically-rising cumulative values: annual = March value, not the sum.
    monthly = {
        "04": 2523,
        "05": 6389,
        "12": 39224,
        "01": 40100,
        "02": 41200,
        "03": 42253,
    }
    assert fy_final_of_cumulative(monthly) == ("03", 42253)


def test_final_month_is_fy_ordered_not_calendar_max() -> None:
    # December ("12") is the largest month number but NOT the FY-final; February ("02") is later
    # in an April-start year, so it wins when March is absent.
    assert fy_final_of_cumulative({"11": 900, "12": 950, "01": 980, "02": 1000}) == ("02", 1000)


def test_partial_year_returns_latest_present_month() -> None:
    assert fy_final_of_cumulative({"04": 100, "05": 250}) == ("05", 250)


def test_null_values_and_unknown_keys_are_ignored() -> None:
    assert fy_final_of_cumulative({"03": None, "02": Decimal("5"), "xx": Decimal("9")}) == (
        "02",
        Decimal("5"),
    )


def test_empty_or_all_null_returns_none() -> None:
    assert fy_final_of_cumulative({}) is None
    assert fy_final_of_cumulative({"03": None, "04": None}) is None
