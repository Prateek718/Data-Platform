"""Single source of truth for the served schema (Stage 7 decision #7).

The metric names and canonical units are REUSED from :mod:`data_platform.harmonize.config` and the
column lists from :mod:`data_platform.export.records` — this module never re-copies them, so it
cannot drift from what the export writes. What it *adds* are the facts that previously lived only in
``DATA_DICTIONARY.md`` prose: the unit-class of each metric, per-column and per-metric descriptions,
each table's grain, and the null semantics. Both ``get_schema`` and any future doc generation read
from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from data_platform.export.records import (
    DISTRICT_COLUMNS,
    NATIONAL_COLUMNS,
    STATE_COLUMNS,
)
from data_platform.harmonize import config as hconfig

JOIN_KEY: Final = "fact_id"


class UnitClass(StrEnum):
    """The dimensional class of a metric's canonical unit (drives materiality reads in lineage)."""

    COUNT = "count"
    MONEY = "money"
    PERSON_DAYS = "person-days"
    RATE = "rate"


# Canonical unit string (from harmonize.config) -> its dimensional class.
_UNIT_CLASS_BY_UNIT: Final[dict[str, UnitClass]] = {
    "count": UnitClass.COUNT,
    "INR lakh": UnitClass.MONEY,
    "person-days": UnitClass.PERSON_DAYS,
    "INR": UnitClass.RATE,
}

# The eight spine metrics (state + national) and the district-only wage rate — names reused from
# harmonize.config so the canonical set is defined in exactly one place.
_SPINE_METRICS: Final[tuple[str, ...]] = (
    hconfig.HOUSEHOLDS_EMPLOYED,
    hconfig.HOUSEHOLDS_COMPLETED_100_DAYS,
    hconfig.ACTIVE_WORKERS,
    hconfig.PERSONDAYS_GENERATED,
    hconfig.WAGES_EXPENDITURE,
    hconfig.MATERIAL_SKILLED_EXPENDITURE,
    hconfig.ADMIN_EXPENDITURE,
    hconfig.TOTAL_EXPENDITURE,
)
_DISTRICT_METRICS: Final[tuple[str, ...]] = (*_SPINE_METRICS, hconfig.AVG_WAGE_RATE_PER_DAY)

_METRIC_DESCRIPTIONS: Final[dict[str, str]] = {
    hconfig.HOUSEHOLDS_EMPLOYED: "Households provided employment under the scheme in the year.",
    hconfig.HOUSEHOLDS_COMPLETED_100_DAYS: (
        "Households that completed the 100 days of wage employment the Act guarantees."
    ),
    hconfig.ACTIVE_WORKERS: "Workers classed as active. Flagship-era (FY 2018-19 onward) only.",
    hconfig.PERSONDAYS_GENERATED: (
        "Person-days of employment generated (Central-liability), corrected from cumulative "
        "year-to-date to the financial-year-final figure."
    ),
    hconfig.WAGES_EXPENDITURE: "Expenditure on wages.",
    hconfig.MATERIAL_SKILLED_EXPENDITURE: "Expenditure on material and skilled wages.",
    hconfig.ADMIN_EXPENDITURE: "Administrative expenditure.",
    hconfig.TOTAL_EXPENDITURE: (
        "Total expenditure, derived as wages + material/skilled + admin; any source-stated total "
        "is compared and the gap recorded in lineage."
    ),
    hconfig.AVG_WAGE_RATE_PER_DAY: (
        "Average wage rate per day per person at district-annual grain: the financial-year-final "
        "value of a cumulative-YTD ratio, a true annual rate only for a complete year. "
        "District-only; a rate, so never summed into a spine."
    ),
}


@dataclass(frozen=True)
class MetricDef:
    """A canonical metric: its name, canonical unit, unit-class, and description."""

    name: str
    unit: str
    unit_class: UnitClass
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "unit": self.unit,
            "unit_class": self.unit_class.value,
            "description": self.description,
        }


def _metric_def(name: str) -> MetricDef:
    unit = hconfig.CANONICAL_UNIT[name]
    return MetricDef(
        name=name,
        unit=unit,
        unit_class=_UNIT_CLASS_BY_UNIT[unit],
        description=_METRIC_DESCRIPTIONS[name],
    )


METRICS: Final[dict[str, MetricDef]] = {name: _metric_def(name) for name in hconfig.CANONICAL_UNIT}


_COLUMN_DESCRIPTIONS: Final[dict[str, str]] = {
    "state_lgd_code": "State/UT LGD code — the canonical geographic identity.",
    "state_name": "State/UT current LGD English name.",
    "district_lgd_code": "District LGD code.",
    "district_name": "District current LGD English name.",
    "financial_year": "Indian financial year (April to March), e.g. 2019-20.",
    "metric": "Canonical metric name (see the metrics list).",
    "value": (
        "Reconciled value in the metric's canonical unit; empty means null "
        "(unknown / unadjudicated / withheld), never zero."
    ),
    "unit": "Canonical unit for the metric.",
    "era_basis": (
        "flagship-rollup (FY 2018-19 onward, from the district-monthly flagship) or historical "
        "(pre-2018 sources, or a flagship-era peer)."
    ),
    "grain": "Grain of the row; district_flagship is single-grain district-annual.",
    "confidence": (
        "How the value is supported or why it was withheld (e.g. cross-publisher, single-source, "
        "flagged-disagreement, unadjudicated, partial-period-only)."
    ),
    "sources_seen_count": (
        "Number of source values seen for this fact (including superseded editions and rejected "
        "peers — nothing is dropped from the count)."
    ),
    "contributing_resource_ids": (
        "Distinct data.gov.in resource ids that carried a value for this fact, ';'-separated."
    ),
    "fact_id": "Stable id for this fact — the join key to lineage (call get_lineage).",
    "record": "The full provenance object for the fact; query it via get_lineage.",
}

NULL_SEMANTICS: Final[dict[str, object]] = {
    "principle": (
        "An empty value is null (unknown, unreported, unadjudicated, or a withheld partial) and is "
        "never coerced to 0; a genuine reported zero is written as 0."
    ),
    "null_reasons": {
        "partial-period-only": (
            "The only reading was an edition's terminal-year mid-year partial; withheld rather "
            "than published as an annual."
        ),
        "unadjudicated": (
            "A structurally-incomplete aggregate materially disagrees with a whole-geography peer; "
            "value withheld."
        ),
        "single-publisher divergence": (
            "One publisher's vintages disagree with no groundable edition order; value withheld "
            "(national tier)."
        ),
    },
    "note": "A null cell is DATA carrying its reason (via get_lineage), not a refusal.",
}

# The confidence states under which a value column is null, mapped to the null reason get_lineage
# reports. Kept here so get_schema (which documents the reasons) and get_lineage (which reports
# them) share one definition.
NULL_REASON_BY_CONFIDENCE: Final[dict[str, str]] = {
    "partial-period-only": "partial-period-only",
    "unadjudicated": "unadjudicated",
    "single-publisher divergence": "single-publisher divergence",
}


@dataclass(frozen=True)
class TableDef:
    """A served table: its name, grain, ordered columns, valid metrics, and FY-column presence."""

    name: str
    grain: str
    columns: tuple[str, ...]
    metrics: tuple[str, ...]
    has_financial_year: bool


TABLES: Final[dict[str, TableDef]] = {
    "state_annual_series": TableDef(
        "state_annual_series", "state-annual", tuple(STATE_COLUMNS), _SPINE_METRICS, True
    ),
    "national_annual_series": TableDef(
        "national_annual_series", "national-annual", tuple(NATIONAL_COLUMNS), _SPINE_METRICS, True
    ),
    "district_flagship": TableDef(
        "district_flagship", "district-annual", tuple(DISTRICT_COLUMNS), _DISTRICT_METRICS, True
    ),
    # lineage is per-fact provenance, not a metric table: it advertises no metrics.
    "lineage": TableDef("lineage", "per-fact provenance", ("fact_id", "record"), (), False),
}

DATA_TABLES: Final[tuple[str, ...]] = (
    "state_annual_series",
    "national_annual_series",
    "district_flagship",
)

# Semantic coverage window of the sealed series (financial years sort lexically, so string
# comparison is chronological). The ceiling is shared: the scheme was repealed 30 June 2026, so the
# series ends at FY 2026-27. Each table has a structural coverage floor; a query wholly below a
# table's floor refuses (a structural boundary of the record, not an empty match).
FISCAL_CEILING: Final = "2026-27"
FISCAL_FLOOR: Final[dict[str, str]] = {
    "state_annual_series": "2010-11",
    "national_annual_series": "2006-07",
    "district_flagship": "2018-19",
}


def column_type(column: str) -> str:
    """The served type of a column: number (value), integer (sources_seen_count), json, or string.

    Mirrors the export Parquet writer's typing; a drift-guard test asserts the agreement.
    """
    if column == "value":
        return "number"
    if column == "sources_seen_count":
        return "integer"
    if column == "record":
        return "json"
    return "string"


def column_def(column: str) -> dict[str, object]:
    return {
        "name": column,
        "type": column_type(column),
        "description": _COLUMN_DESCRIPTIONS[column],
    }
