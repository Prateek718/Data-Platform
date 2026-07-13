"""Named, deterministic filters — the only way a cohort figure may select the facts it counts.

A cohort claim ("193 null cells", "34 flagged disagreements", "9 wage rates above ₹1,000/day") is a
count over the rows a query returned. The selection must be a NAMED filter from this registry, not
an arbitrary predicate: the verifier re-applies the same named filter to the re-executed query, so
the count is reproducible from the artifact alone. An unnamed lambda would be unverifiable.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Final

from data_platform.analyst.tools import Payload

# The implausibility floor for a daily wage rate. Not a magic number: RULES.md R4-DEF-03 uses
# ₹1,000/day as the marker for a rate that cannot be a real daily wage (MGNREGA wages are an order
# of magnitude lower), which is how the cumulative-YTD arrears artifact shows itself.
WAGE_IMPLAUSIBILITY_FLOOR: Final = Decimal("1000")

ALL: Final = "all"
VALUE_IS_NULL: Final = "value_is_null"
FLAGGED_DISAGREEMENT: Final = "confidence == flagged-disagreement"
PARTIAL_PERIOD_ONLY: Final = "confidence == partial-period-only"
UNADJUDICATED: Final = "confidence == unadjudicated"
SINGLE_PUBLISHER_DIVERGENCE: Final = "confidence == single-publisher divergence"
HISTORICAL_ERA: Final = "era_basis == historical"
FLAGSHIP_ERA: Final = "era_basis == flagship-rollup"
WAGE_ABOVE_IMPLAUSIBILITY_FLOOR: Final = "value > 1000 (implausible as a daily wage)"


def _confidence(expected: str) -> Callable[[Payload], bool]:
    return lambda row: row.get("confidence") == expected


def _era(expected: str) -> Callable[[Payload], bool]:
    return lambda row: row.get("era_basis") == expected


def _wage_above_floor(row: Payload) -> bool:
    value = row.get("value")
    return value is not None and Decimal(str(value)) > WAGE_IMPLAUSIBILITY_FLOOR


FILTERS: Final[dict[str, Callable[[Payload], bool]]] = {
    ALL: lambda _row: True,
    VALUE_IS_NULL: lambda row: row.get("value") is None,
    FLAGGED_DISAGREEMENT: _confidence("flagged-disagreement"),
    PARTIAL_PERIOD_ONLY: _confidence("partial-period-only"),
    UNADJUDICATED: _confidence("unadjudicated"),
    SINGLE_PUBLISHER_DIVERGENCE: _confidence("single-publisher divergence"),
    HISTORICAL_ERA: _era("historical"),
    FLAGSHIP_ERA: _era("flagship-rollup"),
    WAGE_ABOVE_IMPLAUSIBILITY_FLOOR: _wage_above_floor,
}


def select(rows: list[Payload], filter_name: str) -> list[Payload]:
    """Apply a named filter. An unknown name is an error — never an empty result."""
    predicate = FILTERS.get(filter_name)
    if predicate is None:
        raise ValueError(f"unknown filter {filter_name!r}; known: {sorted(FILTERS)}")
    return [row for row in rows if predicate(row)]
