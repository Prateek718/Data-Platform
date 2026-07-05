"""Cumulative-YTD → financial-year-final rollup.

A metric published as a running year-to-date total (the flagship persondays/expenditure fields,
named ``…_so_far``) has its ANNUAL value as the **period-final** figure — the value at the last
month of the financial year — NOT the sum of the monthly rows. Summing the monthly cumulatives
inflates the annual figure massively (the divergence check measured a 6.31× over-count on Goa
2022-23), so this transform takes the final value and never sums.

The Indian financial year runs **April → March**, so the final month is **March ("03")**, which is
*not* the largest calendar-month key ("12"). Ordering is therefore by position within the FY, not
by month number — a naive ``max(month)`` would wrongly pick December.
"""

from __future__ import annotations

from collections.abc import Mapping

# Position of each canonical month ("01".."12") within an April-start financial year: April is
# first (0), March is last (11). Used to find the FY-final month present in a cumulative series.
_FY_MONTH_ORDER: dict[str, int] = {
    f"{month:02d}": position
    for position, month in enumerate([4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3])
}


def fy_final_of_cumulative[T](monthly: Mapping[str, T | None]) -> tuple[str, T] | None:
    """Return ``(final_month, value)`` for a cumulative-YTD series, or ``None`` if it is empty.

    ``monthly`` maps canonical month ("01".."12") → the cumulative value at that month. The result
    is the value at the latest month PRESENT in financial-year order (March if present, else the
    latest available month) — the correct annual figure for a year-to-date metric. Months with a
    null value, or keys outside "01".."12", are ignored. Never sums (see module docstring).
    """
    present = [
        (month, value)
        for month, value in monthly.items()
        if month in _FY_MONTH_ORDER and value is not None
    ]
    if not present:
        return None
    final_month, value = max(present, key=lambda item: _FY_MONTH_ORDER[item[0]])
    return final_month, value
