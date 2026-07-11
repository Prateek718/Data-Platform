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

# The flagship average wage rate (INR/day/person). VERIFIED (400,430/400,430 rows @ rel 1e-9,
# R4-DEF-03): this column is cumulative-YTD Wages (INR lakh ×100,000) ÷ cumulative-YTD persondays —
# NOT a monthly rate. Its FY-final month value is the true annual average wage rate; the earlier
# months are year-to-date ratios (April can read ₹18,623/day: arrears on a near-zero persondays
# base), unfit to publish as rates. Taken at DISTRICT-ANNUAL grain, COMPLETE financial years only
# (FY-final month = March), single-source.
FLAGSHIP_WAGE_RATE_COLUMN = "Average_Wage_rate_per_day_per_person"

# A cumulative-YTD ratio is a genuine ANNUAL rate only for a COMPLETE financial year — one whose
# final month, March ("03"), is present. A partial final year yields only an early year-to-date
# ratio (arrears-contaminated, near-zero denominator), not a rate. FY2026-27 is PERMANENTLY partial:
# MGNREGA was repealed effective 30 June 2026, so it carries April 2026 only and will never complete
# — its wage ratio is suppressed as honestly absent (R4-DEF-03). Canonical months: "03" = March.
_FY_FINAL_MONTH_MARCH = "03"

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


def roll_to_national(
    keyed_state_values: list[tuple[CanonicalKey, SourceValue]],
    *,
    source_id: str,
    authority_rank: int,
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Roll STATE-annual source values up to national totals per (fin_year, metric): national = sum
    of the reporting states (additive metrics). Only STATE-grain inputs contribute; a state that did
    not report simply has no source value here (it does not zero the national total — null≠0)."""
    grouped: dict[tuple[str, str], list[SourceValue]] = defaultdict(list)
    for key, source_value in keyed_state_values:
        if key.geo_level is GeoLevel.STATE:
            grouped[(key.fin_year, key.metric)].append(source_value)
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for (fin_year, metric), source_values in grouped.items():
        total = sum((sv.value for sv in source_values), Decimal(0))
        as_of = next((sv.source_as_of for sv in source_values if sv.source_as_of is not None), None)
        key = CanonicalKey(
            scheme="MGNREGA",
            geo_level=GeoLevel.NATIONAL,
            state_code=None,
            district_code=None,
            fin_year=fin_year,
            month=None,
            metric=metric,
        )
        out.append(
            (
                key,
                SourceValue(
                    source_id=source_id,
                    value=total,
                    original_unit=source_values[0].original_unit,
                    source_as_of=as_of,
                    authority_rank=authority_rank,
                ),
            )
        )
    return out


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


def flagship_district_annual_avg_wage(
    resolved: ResolvedBatch, cells: Cells, *, source_as_of: datetime | None
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Flagship average wage rate at DISTRICT-ANNUAL grain: the annual rate of a COMPLETE FY.

    The column is cumulative-YTD wages / cumulative-YTD persondays (R4-DEF-03), so its FY-final
    value is a genuine ANNUAL rate ONLY for a complete financial year — one whose final month,
    March, is present. Emitted only then. A partial final year (e.g. permanently-partial FY2026-27,
    April only, scheme repealed 30 Jun 2026) yields an arrears-contaminated early-YTD ratio, not a
    rate, and is suppressed as honestly absent. The FY-final month is located via the persondays
    cumulative series (the rate's denominator); where that final month has ZERO cumulative
    persondays the rate is undefined (0/0) and the fact is likewise absent (null != 0), never a
    stale earlier month. A rate does not sum, so this is not rolled to state; single-source ->
    R4-REC-04.
    """
    # (state, district, fin_year) -> month -> (wage_rate, cumulative_persondays)
    per_year: dict[tuple[str, str, str], dict[str, tuple[Decimal, Decimal]]] = defaultdict(dict)
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month = row.get("fin_year"), row.get("month")
        wage = _as_decimal(row.get(FLAGSHIP_WAGE_RATE_COLUMN))
        persondays = _as_decimal(row.get(FLAGSHIP_PERSONDAYS_COLUMN))
        if (
            isinstance(fin_year, str)
            and isinstance(month, str)
            and wage is not None
            and persondays is not None
        ):
            district_year = (record.state_canonical_id, record.district_canonical_id, fin_year)
            per_year[district_year][month] = (wage, persondays)

    out: list[tuple[CanonicalKey, SourceValue]] = []
    for (state_code, district_code, fin_year), months in per_year.items():
        final = fy_final_of_cumulative({month: pd for month, (_wage, pd) in months.items()})
        if final is None:
            continue
        final_month, final_persondays = final
        if final_month != _FY_FINAL_MONTH_MARCH:  # incomplete FY — no genuine annual rate
            continue
        if final_persondays == 0:  # rate undefined at zero persondays — honestly absent, never 0
            continue
        wage, _pd = months[final_month]
        key = CanonicalKey(
            scheme="MGNREGA",
            geo_level=GeoLevel.DISTRICT,
            state_code=state_code,
            district_code=district_code,
            fin_year=fin_year,
            month=None,
            metric=AVG_WAGE_RATE_PER_DAY,
        )
        out.append(
            (
                key,
                SourceValue(
                    source_id=resolved.source_id,
                    value=wage,
                    original_unit=CANONICAL_UNIT[AVG_WAGE_RATE_PER_DAY],
                    source_as_of=source_as_of,
                    authority_rank=FLAGSHIP_RANK,
                ),
            )
        )
    return out
