"""First-class structured refusals.

A request the sealed record cannot honestly answer returns a :class:`Refusal` — never an empty
result, never an exception (CLAUDE.md TIER-1: consumers get structured, explainable outcomes). A
refusal is distinct from a null *data* cell: a null cell inside coverage is DATA carrying its
reason (served by ``get_lineage``), whereas a refusal says the question is out of the record scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Refusal codes (stable identifiers a caller can branch on).
UNKNOWN_TABLE: Final = "unknown_table"
UNKNOWN_METRIC: Final = "unknown_metric"
UNKNOWN_GEOGRAPHY: Final = "unknown_geography"
RECORD_SEALED: Final = "record_sealed"
MONTHLY_WAGE_UNAVAILABLE: Final = "monthly_wage_unavailable"
STATE_SERIES_FLOOR: Final = "state_series_floor"
DISTRICT_SERIES_FLOOR: Final = "district_series_floor"
NATIONAL_SERIES_FLOOR: Final = "national_series_floor"
ROW_CAP_EXCEEDED: Final = "row_cap_exceeded"


@dataclass(frozen=True)
class Refusal:
    """A structured refusal. ``refused`` is always ``True`` so callers can detect it uniformly."""

    code: str
    reason: str
    options: tuple[str, ...] | None = None
    pointer: str | None = None

    @property
    def refused(self) -> bool:
        return True

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"refused": True, "code": self.code, "reason": self.reason}
        if self.options is not None:
            payload["options"] = list(self.options)
        if self.pointer is not None:
            payload["pointer"] = self.pointer
        return payload


def unknown_table(table: str, valid_tables: tuple[str, ...]) -> Refusal:
    return Refusal(
        code=UNKNOWN_TABLE,
        reason=f"Unknown table {table!r}. Call list_datasets for the available tables.",
        options=valid_tables,
    )


def lineage_not_queryable(data_tables: tuple[str, ...]) -> Refusal:
    return Refusal(
        code=UNKNOWN_TABLE,
        reason=(
            "The lineage table is not queryable via query(); it is per-fact provenance. "
            "Use get_lineage(fact_id) instead."
        ),
        options=data_tables,
        pointer="get_lineage",
    )


def record_sealed(fy_from: str) -> Refusal:
    return Refusal(
        code=RECORD_SEALED,
        reason=(
            f"No data on or after {fy_from}: MGNREGA was repealed effective 30 June 2026, so the "
            "canonical series ends at FY 2026-27 and this is a closed historical record."
        ),
    )


def monthly_wage() -> Refusal:
    return Refusal(
        code=MONTHLY_WAGE_UNAVAILABLE,
        reason=(
            "The series is annual-grain only; monthly figures are not served. In particular, "
            "monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid "
            "monthly rates — the wage rate is published only as the financial-year-final annual "
            "value at district-annual grain. Remove 'month' to query the annual series."
        ),
    )


def state_series_floor(floor_fy: str) -> Refusal:
    return Refusal(
        code=STATE_SERIES_FLOOR,
        reason=(
            f"The state series starts at FY {floor_fy}; no state-grain data exists before it. "
            "The national series covers FY 2006-07 onward — query national_annual_series instead."
        ),
        pointer="national_annual_series",
    )


def district_series_floor(floor_fy: str) -> Refusal:
    return Refusal(
        code=DISTRICT_SERIES_FLOOR,
        reason=(
            f"The district drill-down starts at FY {floor_fy} (the flagship era); no district-"
            "level data exists before it. Use the state or national series for earlier years."
        ),
        pointer="state_annual_series",
    )


def national_series_floor(floor_fy: str) -> Refusal:
    return Refusal(
        code=NATIONAL_SERIES_FLOOR,
        reason=f"The record starts at FY {floor_fy}; no data exists before it.",
    )


def unknown_metric(
    metric: str, valid_metrics: tuple[str, ...], *, pointer: str | None = None
) -> Refusal:
    reason = f"Unknown metric {metric!r} for this table."
    if pointer is not None:
        reason = (
            f"Metric {metric!r} is not available at this grain; it lives in {pointer}. "
            "Call get_schema for a table's metrics."
        )
    return Refusal(code=UNKNOWN_METRIC, reason=reason, options=valid_metrics, pointer=pointer)


def unknown_geography(
    reason: str, *, options: tuple[str, ...] | None = None, pointer: str | None = None
) -> Refusal:
    return Refusal(code=UNKNOWN_GEOGRAPHY, reason=reason, options=options, pointer=pointer)


def row_cap_exceeded(row_count: int, cap: int) -> Refusal:
    return Refusal(
        code=ROW_CAP_EXCEEDED,
        reason=(
            f"The query matches {row_count} rows, above the {cap}-row cap. Narrow your filters "
            "(fewer metrics, specific states/districts, or a tighter financial-year range)."
        ),
    )
