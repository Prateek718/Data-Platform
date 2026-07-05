"""Source-specific extraction of the starter metric (persondays) to a common canonical grain.

The flagship and the Rajya Sabha person-days tables meet only at **state + annual**: the flagship
is district + monthly and cumulative-YTD, the RS tables are state + annual in lakh. To compare
them, each is brought to state-annual raw person-days here, tagged with the canonical key and the
source's authority rank; the assembler then reconciles across sources. These extractors encode the
grounded per-source facts (which column holds the metric, its unit, its shape) for the starter
slice — the per-resource metric-mapping config, kept explicit.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from data_platform.harmonize.config import (
    ACTIVE_WORKERS,
    ADMIN_EXPENDITURE,
    AVG_WAGE_RATE_PER_DAY,
    CANONICAL_UNIT,
    DEFAULT_TOLERANCE_PCT,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    HOUSEHOLDS_EMPLOYED,
    MATERIAL_SKILLED_EXPENDITURE,
    PERSONDAYS_GENERATED,
    TOTAL_EXPENDITURE,
    WAGES_EXPENDITURE,
    tolerance_for,
)
from data_platform.harmonize.definition import derive_and_compare
from data_platform.harmonize.models import AggregateCoverage, CanonicalKey, SourceValue
from data_platform.harmonize.rollup import fy_final_of_cumulative
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch

# Grounded per-source facts (sources.md §3, divergence-findings): the flagship persondays column
# (cumulative-YTD, raw person-days) and the melted RS value column (state-annual, in lakh).
FLAGSHIP_PERSONDAYS_COLUMN = "Persondays_of_Central_Liability_so_far"
RS_VALUE_COLUMN = "_value"
_LAKH = Decimal(100_000)

# Flagship expenditure columns (cumulative-YTD, INR lakh). total_expenditure is derived from the
# three components; Total_Exp is the source's own total, compared to the derived one (R4-DEF-01).
FLAGSHIP_EXPENDITURE_COMPONENTS = ("Wages", "Material_and_skilled_Wages", "Total_Adm_Expenditure")
FLAGSHIP_TOTAL_EXP_COLUMN = "Total_Exp"

# The flagship average wage rate (INR per day per person) — a rate, taken at the native
# district-monthly grain (not summed, not rolled up); single-source, so no cross-source peer.
FLAGSHIP_WAGE_RATE_COLUMN = "Average_Wage_rate_per_day_per_person"

# Flagship cumulative-YTD columns rolled up to state-annual (FY-final per district, summed) — one
# per canonical metric. All single-source at this grain except persondays (RS cross-check peers).
FLAGSHIP_CUMULATIVE_COLUMNS: dict[str, str] = {
    PERSONDAYS_GENERATED: FLAGSHIP_PERSONDAYS_COLUMN,
    HOUSEHOLDS_EMPLOYED: "Total_Households_Worked",
    HOUSEHOLDS_COMPLETED_100_DAYS: "Total_No_of_HHs_completed_100_Days_of_Wage_Employment",
    ACTIVE_WORKERS: "Total_No_of_Active_Workers",
    WAGES_EXPENDITURE: "Wages",
    MATERIAL_SKILLED_EXPENDITURE: "Material_and_skilled_Wages",
    ADMIN_EXPENDITURE: "Total_Adm_Expenditure",
}

# Authority ranks (DATA_CONTRACT §3): the primary district-monthly flagship outranks the
# downstream state-annual RS summary for the periods the flagship covers.
FLAGSHIP_RANK = 0
RS_RANK = 1

# The RS tables publish person-days as lakh rounded to 2 decimals — a granularity of 0.01 lakh =
# 1,000 raw person-days, so a published figure is within ±500 of the true value (R4-REC-01a).
RS_ROUNDING_EPSILON = Decimal(500)

Cells = dict[int, dict[str, CleanCell]]


def _state_annual_key(state_code: str, fin_year: str, metric: str) -> CanonicalKey:
    return CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code=state_code,
        district_code=None,
        fin_year=fin_year,
        month=None,
        metric=metric,
    )


def _as_decimal(cell: CleanCell) -> Decimal | None:
    """Coerce a cleaned cell to Decimal for arithmetic. Flagship money components arrive as numeric
    strings (Stage 2 left them untyped); Total_Exp arrives already Decimal. Non-numeric → None."""
    if isinstance(cell, Decimal | int):
        return Decimal(cell)
    if isinstance(cell, str):
        try:
            return Decimal(cell)
        except ArithmeticError:
            return None
    return None


def flagship_state_annual_cumulative(
    resolved: ResolvedBatch,
    cells: Cells,
    *,
    metric: str,
    source_as_of: datetime | None,
    lgd_district_counts: dict[str, int],
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Roll one flagship district-monthly cumulative-YTD column up to state-annual for ``metric``.

    Per district-year, the annual figure is the FY-final cumulative value (never the sum of
    monthlies); the state-annual figure is the sum of those district finals. Each rolled-up value
    carries its :class:`AggregateCoverage` — districts summed this year, the flagship's own district
    universe for the state (all years), and the current LGD count — so R4-REC-05 can tell a complete
    state total from a structurally-partial one. ``lgd_district_counts``: LGD state code → count.
    """
    column = FLAGSHIP_CUMULATIVE_COLUMNS[metric]
    # (state, fin_year) -> district -> {month: cumulative value}
    monthly: dict[tuple[str, str], dict[str, dict[str, Decimal]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month = row.get("fin_year"), row.get("month")
        value = _as_decimal(row.get(column))
        if isinstance(fin_year, str) and isinstance(month, str) and value is not None:
            monthly[(record.state_canonical_id, fin_year)][record.district_canonical_id][month] = (
                value
            )

    # The flagship's own district universe per state = distinct districts it reports over all years.
    universe: dict[str, set[str]] = defaultdict(set)
    for (state_code, _fy), districts in monthly.items():
        universe[state_code].update(districts)

    out: list[tuple[CanonicalKey, SourceValue]] = []
    for (state_code, fin_year), districts in monthly.items():
        total = Decimal(0)
        summed = 0
        for district_series in districts.values():
            final = fy_final_of_cumulative(district_series)
            if final is not None:
                total += final[1]
                summed += 1
        if summed:
            coverage = AggregateCoverage(
                units_summed=summed,
                units_in_source_universe=len(universe[state_code]),
                units_in_lgd=lgd_district_counts.get(state_code, 0),
            )
            out.append(
                (
                    _state_annual_key(state_code, fin_year, metric),
                    SourceValue(
                        source_id=resolved.source_id,
                        value=total,
                        original_unit=CANONICAL_UNIT[metric],
                        source_as_of=source_as_of,
                        authority_rank=FLAGSHIP_RANK,
                        aggregate_coverage=coverage,
                    ),
                )
            )
    return out


def flagship_state_annual_persondays(
    resolved: ResolvedBatch,
    cells: Cells,
    *,
    source_as_of: datetime | None,
    lgd_district_counts: dict[str, int],
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Flagship state-annual persondays — the cumulative rollup for the persondays metric."""
    return flagship_state_annual_cumulative(
        resolved,
        cells,
        metric=PERSONDAYS_GENERATED,
        source_as_of=source_as_of,
        lgd_district_counts=lgd_district_counts,
    )


def rs_state_annual_persondays(
    resolved: ResolvedBatch, cells: Cells, *, source_as_of: datetime | None
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Convert the melted RS state-annual persondays (in lakh) to raw person-days."""
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.state_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, value = row.get("_fin_year"), row.get(RS_VALUE_COLUMN)
        if not isinstance(fin_year, str) or value is None:
            continue
        try:
            lakh = Decimal(str(value))
        except InvalidOperation:
            continue
        out.append(
            (
                _state_annual_key(record.state_canonical_id, fin_year, PERSONDAYS_GENERATED),
                SourceValue(
                    source_id=resolved.source_id,
                    value=lakh * _LAKH,
                    original_unit="lakh",
                    source_as_of=source_as_of,
                    authority_rank=RS_RANK,
                    rounding_epsilon=RS_ROUNDING_EPSILON,
                ),
            )
        )
    return out


def flagship_state_annual_total_expenditure(
    resolved: ResolvedBatch,
    cells: Cells,
    *,
    source_as_of: datetime | None,
    lgd_district_counts: dict[str, int],
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Derive state-annual total_expenditure and compare to the flagship's own total (R4-DEF-01).

    Per district-year, take the FY-final of each expenditure column; sum districts to state level.
    total_expenditure is DERIVED (wages + material/skilled + admin); the flagship's own Total_Exp is
    compared and any beyond-tolerance gap recorded as a definition discrepancy on the source value.
    """
    columns = (*FLAGSHIP_EXPENDITURE_COMPONENTS, FLAGSHIP_TOTAL_EXP_COLUMN)
    # (state, fin_year) -> district -> column -> {month: cumulative value}
    nested: dict[tuple[str, str], dict[str, dict[str, dict[str, Decimal]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month = row.get("fin_year"), row.get("month")
        if not (isinstance(fin_year, str) and isinstance(month, str)):
            continue
        for column in columns:
            value = _as_decimal(row.get(column))
            if value is not None:
                nested[(record.state_canonical_id, fin_year)][record.district_canonical_id][column][
                    month
                ] = value

    universe: dict[str, set[str]] = defaultdict(set)
    for (state_code, _fy), districts in nested.items():
        universe[state_code].update(districts)

    tolerance = tolerance_for(TOTAL_EXPENDITURE) or DEFAULT_TOLERANCE_PCT
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for (state_code, fin_year), districts in nested.items():
        sums = {column: Decimal(0) for column in columns}
        total_exp_present = False
        summed_districts = 0
        for column_series in districts.values():
            contributed = False
            for column in columns:
                final = fy_final_of_cumulative(column_series.get(column, {}))
                if final is not None:
                    sums[column] += final[1]
                    contributed = True
                    if column == FLAGSHIP_TOTAL_EXP_COLUMN:
                        total_exp_present = True
            if contributed:
                summed_districts += 1

        components = [sums[column] for column in FLAGSHIP_EXPENDITURE_COMPONENTS]
        source_total = sums[FLAGSHIP_TOTAL_EXP_COLUMN] if total_exp_present else None
        derived, discrepancy = derive_and_compare(components, source_total, tolerance=tolerance)
        coverage = AggregateCoverage(
            units_summed=summed_districts,
            units_in_source_universe=len(universe[state_code]),
            units_in_lgd=lgd_district_counts.get(state_code, 0),
        )
        out.append(
            (
                _state_annual_key(state_code, fin_year, TOTAL_EXPENDITURE),
                SourceValue(
                    source_id=resolved.source_id,
                    value=derived,
                    original_unit="lakh",
                    source_as_of=source_as_of,
                    authority_rank=FLAGSHIP_RANK,
                    aggregate_coverage=coverage,
                    definition_discrepancy=discrepancy,
                ),
            )
        )
    return out


def flagship_district_monthly_avg_wage(
    resolved: ResolvedBatch, cells: Cells, *, source_as_of: datetime | None
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Take the flagship average wage rate at its native district-monthly grain.

    A rate is neither summed nor cumulative-rolled: each resolved district-month row contributes one
    value directly, at the canonical district+monthly grain. Single-source (no RS wage peer), so
    these reconcile as R4-REC-04.
    """
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month, wage = (
            row.get("fin_year"),
            row.get("month"),
            row.get(FLAGSHIP_WAGE_RATE_COLUMN),
        )
        if isinstance(fin_year, str) and isinstance(month, str) and isinstance(wage, Decimal):
            key = CanonicalKey(
                scheme="MGNREGA",
                geo_level=GeoLevel.DISTRICT,
                state_code=record.state_canonical_id,
                district_code=record.district_canonical_id,
                fin_year=fin_year,
                month=month,
                metric=AVG_WAGE_RATE_PER_DAY,
            )
            out.append(
                (
                    key,
                    SourceValue(
                        source_id=resolved.source_id,
                        value=wage,
                        original_unit="INR",
                        source_as_of=source_as_of,
                        authority_rank=FLAGSHIP_RANK,
                    ),
                )
            )
    return out
