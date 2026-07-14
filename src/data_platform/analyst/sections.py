"""The report's sections — each one a plan plus the retrieval that backs it.

A section is only here if the claim inventory (``docs/notes/STAGE8-CLAIM-INVENTORY.md``) verified
it against the served surface. Retrieval is a pure function of the tools: it fetches figures,
counts cohorts, computes the section's declared derivations, and captures the refusals it exhibits.

Two candidate sections from the inventory are deliberately ABSENT: the Goa "6.31x" cumulative-YTD
example and the "Rs 18,623/day" wage artifact. Both are figures about MONTHLY data, and the sealed
record is annual-only at every grain — they live in the archive the pipeline consumed, not in the
dataset it published, so no query can back them and the verifier would (rightly) block them.
"""

from __future__ import annotations

from collections.abc import Callable

from data_platform.analyst import cohort, derive, retrieve
from data_platform.analyst.models import QuerySpec, RetrievedSection, SectionPlan
from data_platform.analyst.tools import AnalystTools

Retriever = Callable[[AnalystTools], RetrievedSection]

_GOA = "Goa"
_STATE = "state_annual_series"
_NATIONAL = "national_annual_series"
_DISTRICT = "district_flagship"
_PERSONDAYS = "persondays_generated"
_WAGE_RATE = "avg_wage_rate_per_day"

# The financial years each grain covers (the served coverage windows).
_SPINE_METRICS: tuple[str, ...] = (
    "households_employed",
    "households_completed_100_days",
    "active_workers",
    "persondays_generated",
    "wages_expenditure",
    "material_skilled_expenditure",
    "admin_expenditure",
    "total_expenditure",
)
_STATE_YEARS: tuple[str, ...] = tuple(f"{y}-{str(y + 1)[2:]}" for y in range(2010, 2027))
_FLAGSHIP_YEARS: tuple[str, ...] = tuple(f"{y}-{str(y + 1)[2:]}" for y in range(2018, 2027))


# --- C1: the twenty-year national series --------------------------------------------------------

NATIONAL_SERIES = SectionPlan(
    key="national_series",
    title="The twenty-year record, 2006-07 to 2026-27",
    brief=(
        "State the scale and shape of MGNREGA's national record across its whole life. Give the "
        "first year's person-days, the peak year's person-days, the last COMPLETE financial year's "
        "person-days, and the peak year's total expenditure and households employed. Say how many "
        "times larger the peak was than the first year (the derived figure gives it). Explain that "
        "the series is stitched from two eras of sourcing — the counts of historical facts and of "
        "flagship-rollup facts are given — where pre-2018 years come from archived publishers "
        "(MoSPI, Rajya Sabha answers) and FY 2018-19 onward from the flagship district MIS. "
        "Finally: FY 2026-27 is a stub, not a year — the scheme was repealed effective 30 June "
        "2026 and the record carries April 2026 only, so its person-days figure is not comparable "
        "to a full year. The last complete financial year of MGNREGA is 2025-26."
    ),
)


def retrieve_national_series(tools: AnalystTools) -> RetrievedSection:
    first = retrieve.fetch_figure(
        tools,
        id="persondays_2006_07",
        label="national person-days generated, FY 2006-07 (the first year)",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2006-07"),
    )
    peak = retrieve.fetch_figure(
        tools,
        id="persondays_2020_21",
        label="national person-days generated, FY 2020-21 (the peak year)",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2020-21"),
    )
    last_complete = retrieve.fetch_figure(
        tools,
        id="persondays_2025_26",
        label="national person-days generated, FY 2025-26 (the last complete year)",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2025-26"),
    )
    stub = retrieve.fetch_figure(
        tools,
        id="persondays_2026_27",
        label="national person-days generated, FY 2026-27 (April 2026 only — a repeal stub)",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2026-27"),
    )
    peak_spend = retrieve.fetch_figure(
        tools,
        id="expenditure_2020_21",
        label="national total expenditure, FY 2020-21",
        geography="India",
        spec=QuerySpec(_NATIONAL, "total_expenditure", "2020-21"),
    )
    peak_households = retrieve.fetch_figure(
        tools,
        id="households_2020_21",
        label="national households employed, FY 2020-21",
        geography="India",
        spec=QuerySpec(_NATIONAL, "households_employed", "2020-21"),
    )

    growth = retrieve.derived(
        id="peak_over_first",
        label="peak-year person-days divided by first-year person-days (2 decimal places)",
        operation=derive.RATIO_2DP,
        inputs=[peak, first],
        unit="times",
    )
    # Presentation forms: the same served facts, restated in units a reader can hold. Declared
    # derivations the verifier recomputes — not the drafter rounding.
    first_billions = retrieve.derived(
        id="persondays_2006_07_billions",
        label="first-year person-days, in billions",
        operation=derive.TO_BILLIONS,
        inputs=[first],
        unit="billion person-days",
    )
    peak_billions = retrieve.derived(
        id="persondays_2020_21_billions",
        label="peak-year person-days, in billions",
        operation=derive.TO_BILLIONS,
        inputs=[peak],
        unit="billion person-days",
    )
    last_billions = retrieve.derived(
        id="persondays_2025_26_billions",
        label="last complete year's person-days, in billions",
        operation=derive.TO_BILLIONS,
        inputs=[last_complete],
        unit="billion person-days",
    )
    stub_millions = retrieve.derived(
        id="persondays_2026_27_millions",
        label="the repeal stub's person-days, in millions",
        operation=derive.TO_MILLIONS,
        inputs=[stub],
        unit="million person-days",
    )
    peak_spend_lakh_crore = retrieve.derived(
        id="expenditure_2020_21_lakh_crore",
        label="peak-year total expenditure, in lakh crore rupees",
        operation=derive.LAKH_TO_LAKH_CRORE,
        inputs=[peak_spend],
        unit="lakh crore rupees",
    )
    peak_households_millions = retrieve.derived(
        id="households_2020_21_millions",
        label="peak-year households employed, in millions",
        operation=derive.TO_MILLIONS,
        inputs=[peak_households],
        unit="million households",
    )

    # Chart data — verified like any figure, but never shown to the drafter.
    series = (
        *retrieve.fetch_series(
            tools,
            id_prefix="series_persondays",
            label="national person-days generated",
            geography="India",
            table=_NATIONAL,
            metric=_PERSONDAYS,
            fy_from="2006-07",
            fy_to="2026-27",
        ),
        *retrieve.fetch_series(
            tools,
            id_prefix="series_expenditure",
            label="national total expenditure",
            geography="India",
            table=_NATIONAL,
            metric="total_expenditure",
            fy_from="2006-07",
            fy_to="2026-27",
        ),
        *retrieve.fetch_series(
            tools,
            id_prefix="series_households",
            label="national households employed",
            geography="India",
            table=_NATIONAL,
            metric="households_employed",
            fy_from="2006-07",
            fy_to="2026-27",
        ),
    )

    historical = retrieve.fetch_cohort(
        tools,
        id="historical_facts",
        label="national facts sourced from the pre-2018 archive (historical era)",
        table=_NATIONAL,
        filter=cohort.HISTORICAL_ERA,
    )
    flagship = retrieve.fetch_cohort(
        tools,
        id="flagship_facts",
        label="national facts sourced from the flagship district MIS (FY 2018-19 onward)",
        table=_NATIONAL,
        filter=cohort.FLAGSHIP_ERA,
    )

    sealed = retrieve.refusal(
        tools,
        id="after_the_repeal",
        label="asking for data after the repeal",
        call='query(table="national_annual_series", fy_from="2027-28")',
        table=_NATIONAL,
        fy_from="2027-28",
    )

    return RetrievedSection(
        plan=NATIONAL_SERIES,
        figures=(first, peak, last_complete, stub, peak_spend, peak_households),
        derivations=(
            growth,
            first_billions,
            peak_billions,
            last_billions,
            stub_millions,
            peak_spend_lakh_crore,
            peak_households_millions,
        ),
        cohorts=(historical, flagship),
        refusals=(sealed,),
        series=series,
    )


# --- C2: where the publishers disagree ----------------------------------------------------------

DISAGREEMENTS = SectionPlan(
    key="disagreements",
    title="Where the publishers disagree, and what the record does about it",
    brief=(
        "The record carries two DISTINCT and separately-counted phenomena. Never merge them into "
        "one homogeneous count.\n\n"
        "(a) PRE-2018: state-year cells where two archived publishers of the same statistic — "
        "MoSPI and Rajya Sabha parliamentary answers — materially disagree. Here reconciliation "
        "ADJUDICATED a canonical value between corroborating sources of comparable standing, under "
        "the cross-source reconciliation rule family (R4-REC): the winner is recorded, the "
        "rejected value and its publisher are kept in lineage, and the disagreement stays visible "
        "rather than being smoothed away.\n\n"
        "(b) FLAGSHIP-ERA: state-year cells where the primary district MIS disagrees with figures "
        "tabled in Parliament. Here the authority rule crowns the primary MIS — the production "
        "authority for the period it covers — so the divergence is RECORDED as a flagged note, "
        "NOT adjudicated between peers. The Parliament-tabled figure is retained in lineage, not "
        "discarded.\n\n"
        "Say explicitly which of the two each count refers to, and that both sets passed the same "
        "two-part materiality floor (a disagreement counts only if it clears both an absolute and "
        "a relative threshold).\n\n"
        "Give ONE example from each set, using the figures provided. Two cautions, both strict:\n"
        "- Do NOT call either example the largest, the biggest or the worst. Nothing here ranks "
        "them, and a ranking nobody computed is a claim you cannot support. Write 'one such case "
        "is'.\n"
        "- The figure attached to each example is the CANONICAL VALUE the record settled on — the "
        "value it publishes for that cell. It is NOT the size of the gap between the publishers. "
        "Say so explicitly, so no reader mistakes one for the other.\n\n"
        "This is a governance finding, not a scandal: the point is that the record shows its "
        "disagreements instead of hiding them."
    ),
)


def retrieve_disagreements(tools: AnalystTools) -> RetrievedSection:
    pre_2018 = retrieve.fetch_cohort(
        tools,
        id="pre_2018_disagreements",
        label=(
            "pre-2018 cross-publisher material disagreements, ADJUDICATED between MoSPI and "
            "Rajya Sabha (state series)"
        ),
        table=_STATE,
        filter=cohort.FLAGGED_DISAGREEMENT,
        fy_to="2017-18",
    )
    flagship_era = retrieve.fetch_cohort(
        tools,
        id="flagship_era_divergences",
        label=(
            "flagship-era divergences between the primary district MIS and figures tabled in "
            "Parliament, RECORDED as flagged notes (state series, FY 2018-19 onward)"
        ),
        table=_STATE,
        filter=cohort.FLAGGED_DISAGREEMENT,
        fy_from="2018-19",
    )
    total = retrieve.derived(
        id="all_flagged",
        label="flagged cells in the record (the two sets added together)",
        operation=derive.SUM,
        inputs=[pre_2018, flagship_era],
        unit="cells",
    )

    telangana = retrieve.fetch_figure(
        tools,
        id="telangana_expenditure_2016_17",
        label=(
            "Telangana total expenditure, FY 2016-17 — one pre-2018 case: this is the CANONICAL "
            "VALUE the record publishes (the Rajya Sabha figure), not the size of the gap; MoSPI's "
            "rejected value is kept in lineage"
        ),
        geography="Telangana",
        spec=QuerySpec(_STATE, "total_expenditure", "2016-17", "Telangana"),
    )
    lakshadweep = retrieve.fetch_figure(
        tools,
        id="lakshadweep_persondays_2023_24",
        label=(
            "Lakshadweep person-days, FY 2023-24 — one flagship-era case: this is the CANONICAL "
            "VALUE the record publishes (the district MIS figure), not the size of the gap; the "
            "Parliament-tabled figure is kept in lineage"
        ),
        geography="Lakshadweep",
        spec=QuerySpec(_STATE, _PERSONDAYS, "2023-24", "Lakshadweep"),
    )

    telangana_crore = retrieve.derived(
        id="telangana_expenditure_crore",
        label="Telangana's canonical FY 2016-17 total expenditure, in crore rupees",
        operation=derive.LAKH_TO_CRORE,
        inputs=[telangana],
        unit="crore rupees",
    )

    return RetrievedSection(
        plan=DISAGREEMENTS,
        figures=(telangana, lakshadweep),
        derivations=(total, telangana_crore),
        cohorts=(pre_2018, flagship_era),
    )


# --- C3': the pilot — Goa's spine ---------------------------------------------------------------

GOA_SPINE = SectionPlan(
    key="goa_spine",
    title="Goa, FY 2022-23: the spine reconciles, and the rate refuses to",
    brief=(
        "Show that the district drill-down reconciles exactly to the state series for an additive "
        "metric: North Goa's person-days plus South Goa's person-days equal the Goa state figure "
        "with no residual. Then show the boundary of that arithmetic: the ninth metric, the "
        "average wage rate per day, is a RATE — it is served only at district-annual grain, the "
        "state series refuses it, and adding the two districts' rates together would be "
        "meaningless. Quote what the server says when asked for the wage rate at state grain, and "
        "when asked for any monthly figure. The record is annual-only, and it says so when asked."
    ),
)

_FY = "2022-23"


def retrieve_goa_spine(tools: AnalystTools) -> RetrievedSection:
    """Goa FY 2022-23: districts sum to the state spine; the wage rate does not sum at all."""
    north = retrieve.fetch_figure(
        tools,
        id="north_goa_persondays",
        label="North Goa person-days generated, FY 2022-23",
        geography="North Goa, Goa",
        spec=QuerySpec(_DISTRICT, _PERSONDAYS, _FY, _GOA, "North Goa"),
    )
    south = retrieve.fetch_figure(
        tools,
        id="south_goa_persondays",
        label="South Goa person-days generated, FY 2022-23",
        geography="South Goa, Goa",
        spec=QuerySpec(_DISTRICT, _PERSONDAYS, _FY, _GOA, "South Goa"),
    )
    state = retrieve.fetch_figure(
        tools,
        id="goa_persondays",
        label="Goa state person-days generated, FY 2022-23",
        geography="Goa",
        spec=QuerySpec(_STATE, _PERSONDAYS, _FY, _GOA),
    )
    north_rate = retrieve.fetch_figure(
        tools,
        id="north_goa_wage_rate",
        label="North Goa average wage rate per day, FY 2022-23",
        geography="North Goa, Goa",
        spec=QuerySpec(_DISTRICT, _WAGE_RATE, _FY, _GOA, "North Goa"),
    )
    south_rate = retrieve.fetch_figure(
        tools,
        id="south_goa_wage_rate",
        label="South Goa average wage rate per day, FY 2022-23",
        geography="South Goa, Goa",
        spec=QuerySpec(_DISTRICT, _WAGE_RATE, _FY, _GOA, "South Goa"),
    )

    district_sum = retrieve.derived(
        id="district_sum_persondays",
        label="North Goa plus South Goa person-days",
        operation=derive.SUM,
        inputs=[north, south],
        unit="person-days",
    )
    # The residual is the claim: the drill-down reconciles to the spine EXACTLY, and the report says
    # so with a number rather than an adjective.
    residual = retrieve.derived(
        id="spine_residual",
        label="state person-days minus the district sum",
        operation=derive.DIFFERENCE,
        inputs=[state, district_sum],
        unit="person-days",
    )

    rate_refusal = retrieve.refusal(
        tools,
        id="wage_rate_at_state_grain",
        label="asking for the wage rate at state grain",
        call=(
            'query(table="state_annual_series", metrics=["avg_wage_rate_per_day"], states=["Goa"])'
        ),
        table=_STATE,
        metrics=[_WAGE_RATE],
        states=[_GOA],
    )
    monthly_refusal = retrieve.refusal(
        tools,
        id="monthly_figure",
        label="asking for a monthly figure",
        call='query(table="district_flagship", states=["Goa"], month="2022-04")',
        table=_DISTRICT,
        states=[_GOA],
        month="2022-04",
    )

    north_rate_2dp = retrieve.derived(
        id="north_goa_wage_rate_2dp",
        label="North Goa's average wage rate per day, to the paisa",
        operation=derive.ROUND_2DP,
        inputs=[north_rate],
        unit="rupees per day",
    )
    south_rate_2dp = retrieve.derived(
        id="south_goa_wage_rate_2dp",
        label="South Goa's average wage rate per day, to the paisa",
        operation=derive.ROUND_2DP,
        inputs=[south_rate],
        unit="rupees per day",
    )

    return RetrievedSection(
        plan=GOA_SPINE,
        figures=(north, south, state, north_rate, south_rate),
        derivations=(district_sum, residual, north_rate_2dp, south_rate_2dp),
        refusals=(rate_refusal, monthly_refusal),
    )


# --- C4': the wage rate the record will not price -----------------------------------------------

WAGE_RATE = SectionPlan(
    key="wage_rate",
    title="The wage rate the record will not price by the month",
    brief=(
        "The record serves an average wage rate per day only at district-annual grain, only for a "
        "COMPLETE financial year, and never by the month. Give the count of wage-rate facts it "
        "serves. Then state the two absences and what they mean:\n\n"
        "(1) ZERO wage-rate facts exist for FY 2026-27. That year never completed — the scheme was "
        "repealed effective 30 June 2026 — and an incomplete year has no annual rate, so the "
        "record withholds it rather than publishing a part-year ratio as if it were a wage.\n\n"
        "(2) Monthly wage figures are REFUSED outright. Quote the server's reason: the published "
        "monthly values are cumulative year-to-date ratios, not monthly rates.\n\n"
        "Then the caveat, and state it plainly and prominently: a small number of financial-year-"
        "final rates are still implausibly high — the count is given, and the highest is a West "
        "Bengal district. These are NOT observed wages. A plausible MGNREGA daily wage is an order "
        "of magnitude lower than these figures. They are data-quality artifacts of the source "
        "series, carried faithfully into the record with their lineage rather than quietly "
        "deleted, and a reader must not read them as what anyone was paid."
    ),
)


def retrieve_wage_rate(tools: AnalystTools) -> RetrievedSection:
    served = retrieve.fetch_cohort(
        tools,
        id="wage_facts_served",
        label="district-annual wage-rate facts the record serves (FY 2018-19 to 2025-26)",
        table=_DISTRICT,
        metrics=[_WAGE_RATE],
        filter=cohort.ALL,
    )
    terminal_year = retrieve.fetch_cohort(
        tools,
        id="wage_facts_2026_27",
        label="wage-rate facts for FY 2026-27, the repeal-truncated year",
        table=_DISTRICT,
        metrics=[_WAGE_RATE],
        fy_from="2026-27",
        fy_to="2026-27",
        filter=cohort.ALL,
    )
    implausible = retrieve.fetch_cohort(
        tools,
        id="implausible_rates",
        label=(
            "financial-year-final wage rates above Rs 1,000/day — source data-quality artifacts, "
            "not observed wages"
        ),
        table=_DISTRICT,
        metrics=[_WAGE_RATE],
        filter=cohort.WAGE_ABOVE_IMPLAUSIBILITY_FLOOR,
    )
    highest = retrieve.fetch_figure(
        tools,
        id="hooghly_wage_rate",
        label=(
            "the highest financial-year-final wage rate in the record: Hooghly, West Bengal, "
            "FY 2023-24 — an artifact, not a wage anyone was paid"
        ),
        geography="Hooghly, West Bengal",
        spec=QuerySpec(_DISTRICT, _WAGE_RATE, "2023-24", "West Bengal", "Hooghly"),
    )

    monthly_refusal = retrieve.refusal(
        tools,
        id="monthly_wage",
        label="asking for a monthly wage rate",
        call='query(table="district_flagship", metrics=["avg_wage_rate_per_day"], month="2022-04")',
        table=_DISTRICT,
        metrics=[_WAGE_RATE],
        month="2022-04",
    )
    state_grain_refusal = retrieve.refusal(
        tools,
        id="wage_at_state_grain",
        label="asking for the wage rate at state grain",
        call='query(table="state_annual_series", metrics=["avg_wage_rate_per_day"])',
        table=_STATE,
        metrics=[_WAGE_RATE],
    )

    return RetrievedSection(
        plan=WAGE_RATE,
        figures=(highest,),
        derivations=(),
        cohorts=(served, terminal_year, implausible),
        refusals=(monthly_refusal, state_grain_refusal),
    )


# --- C5 + C9: coverage honesty ------------------------------------------------------------------

COVERAGE = SectionPlan(
    key="coverage",
    title="What the record does not contain",
    brief=(
        "A null cell in this record is data, not a gap in the plumbing: it carries a reason, and "
        "it is never coerced to zero. Give the counts of null cells at state grain — the "
        "partial-period-only ones (the only reading was an edition's mid-year partial, withheld "
        "rather than published as if it were an annual figure) and the unadjudicated ones (a "
        "structurally-incomplete aggregate materially disagrees with a whole-geography peer, so no "
        "value is asserted) — and at national grain the single-publisher-divergence ones (one "
        "publisher's own vintages disagree with no defensible order between them). The derived "
        "total is given.\n\n"
        "THE SEAM. Cite the count of state cells that are BOTH in FY 2017-18 AND withheld as "
        "partial-period-only — that exact count is given, and it is the one to use. FY 2017-18 is "
        "the year before the district system begins, and the record's weakest year is exactly "
        "where its two sourcing eras meet.\n\n"
        "THE NATIONAL HOLE, decomposed. Do not leave the national nulls as a bare total: say which "
        "years they fall in (counts for FY 2012-13, 2013-14, 2014-15 and 2015-16 are given, and "
        "they account for all of them — there are no national nulls in any other year) and say "
        "that they are spread across seven of the eight metrics rather than concentrated in one "
        "(per-metric counts are given; active workers is the exception, and it has no pre-2018 "
        "values to disagree about in the first place).\n\n"
        "A DIFFERENT KIND OF ABSENCE. The national expenditure series does not begin with the "
        "scheme: the count of national expenditure facts in FY 2006-07 and FY 2007-08 is given, "
        "and it is zero. Person-days and households are recorded from the first year; spending is "
        "not. That is an absence of source data, not a withheld value, and it is why the "
        "expenditure chart starts two years later than the person-days chart.\n\n"
        "Finally, a metric that is absent rather than null: active workers exists only from FY "
        "2018-19 onward (the count of such facts in that first year is given). Anyone comparing "
        "'workers' across the full twenty years would be comparing a metric against its own "
        "absence."
    ),
)


def retrieve_coverage(tools: AnalystTools) -> RetrievedSection:
    partial = retrieve.fetch_cohort(
        tools,
        id="partial_period_nulls",
        label="state-series null cells withheld as partial-period-only",
        table=_STATE,
        filter=cohort.PARTIAL_PERIOD_ONLY,
    )
    unadjudicated = retrieve.fetch_cohort(
        tools,
        id="unadjudicated_nulls",
        label="state-series null cells withheld as unadjudicated",
        table=_STATE,
        filter=cohort.UNADJUDICATED,
    )
    national_nulls = retrieve.fetch_cohort(
        tools,
        id="national_divergence_nulls",
        label="national-series null cells withheld as single-publisher divergence",
        table=_NATIONAL,
        filter=cohort.SINGLE_PUBLISHER_DIVERGENCE,
    )
    total = retrieve.derived(
        id="all_nulls",
        label="null cells in the record, all reasons together",
        operation=derive.SUM,
        inputs=[partial, unadjudicated, national_nulls],
        unit="cells",
    )

    # The compound predicate: BOTH in FY 2017-18 AND withheld for this reason. Counting all nulls in
    # that year and attributing them to one reason would be a predicate mismatch — the state series
    # also carries unadjudicated nulls, and nothing says they avoid this year.
    seam = retrieve.fetch_cohort(
        tools,
        id="seam_partial_period_nulls",
        label=(
            "state cells that are BOTH in FY 2017-18 AND withheld as partial-period-only "
            "(the seam between the two sourcing eras)"
        ),
        table=_STATE,
        fy_from="2017-18",
        fy_to="2017-18",
        filter=cohort.PARTIAL_PERIOD_ONLY,
    )

    national_nulls_by_year = tuple(
        retrieve.fetch_cohort(
            tools,
            id=f"national_nulls_{fy.replace('-', '_')}",
            label=f"national cells withheld as single-publisher divergence in FY {fy}",
            table=_NATIONAL,
            fy_from=fy,
            fy_to=fy,
            filter=cohort.SINGLE_PUBLISHER_DIVERGENCE,
        )
        for fy in ("2012-13", "2013-14", "2014-15", "2015-16")
    )
    national_nulls_by_metric = tuple(
        retrieve.fetch_cohort(
            tools,
            id=f"national_nulls_metric_{metric}",
            label=(
                f"national {metric.replace('_', ' ')} cells withheld as single-publisher divergence"
            ),
            table=_NATIONAL,
            metrics=[metric],
            filter=cohort.SINGLE_PUBLISHER_DIVERGENCE,
        )
        for metric in _SPINE_METRICS
    )
    expenditure_before_2008 = retrieve.fetch_cohort(
        tools,
        id="national_expenditure_2006_08",
        label=(
            "national total-expenditure facts in FY 2006-07 and FY 2007-08 — none exist; the "
            "spending series starts two years after the work series"
        ),
        table=_NATIONAL,
        metrics=["total_expenditure"],
        fy_from="2006-07",
        fy_to="2007-08",
        filter=cohort.ALL,
    )
    active_workers_first_year = retrieve.fetch_cohort(
        tools,
        id="active_workers_2018_19",
        label="active-workers facts at state grain in FY 2018-19, the metric's first year",
        table=_STATE,
        metrics=["active_workers"],
        fy_from="2018-19",
        fy_to="2018-19",
        filter=cohort.ALL,
    )

    floor_refusal = retrieve.refusal(
        tools,
        id="state_series_floor",
        label="asking the state series for a year before it starts",
        call='query(table="state_annual_series", fy_to="2008-09")',
        table=_STATE,
        fy_to="2008-09",
    )

    nulls_by_year = tuple(
        retrieve.fetch_cohort(
            tools,
            id=f"nulls_by_year_{fy.replace('-', '_')}",
            label=f"state-series null cells in FY {fy}",
            table=_STATE,
            fy_from=fy,
            fy_to=fy,
            filter=cohort.VALUE_IS_NULL,
        )
        for fy in _STATE_YEARS
    )

    return RetrievedSection(
        plan=COVERAGE,
        figures=(),
        derivations=(total,),
        cohorts=(
            partial,
            unadjudicated,
            national_nulls,
            seam,
            expenditure_before_2008,
            active_workers_first_year,
            *national_nulls_by_year,
            *national_nulls_by_metric,
        ),
        refusals=(floor_refusal,),
        series_cohorts=nulls_by_year,
    )


# --- C6: the refusal surface --------------------------------------------------------------------

REFUSALS = SectionPlan(
    key="refusals",
    title="What this record refuses to answer",
    brief=(
        "A governed record is defined as much by what it declines to say as by what it says. Walk "
        "through the refusals below — each one an object the server actually returned — and "
        "explain what each protects. Quote the reasons.\n\n"
        "The shape of the argument: asking for data after the repeal is refused because the series "
        "is sealed; asking for a monthly figure is refused because the record is annual-only; "
        "asking for the wage rate at state grain is refused because it is a rate and does not sum; "
        "asking for district data before the flagship era is refused because the drill-down does "
        "not exist there; a malformed financial-year label is refused rather than compared, "
        "because such a label is compared as a string and a malformed one would silently produce a "
        "wrong answer instead of an error; an unknown geography is refused rather than guessed; "
        "and asking for the lineage table through the query verb is refused with a pointer to the "
        "verb that serves it.\n\n"
        "Each refusal names what is wrong AND where to go instead. That is the point: the record "
        "does not fail silently, and it does not answer a question it cannot honestly answer. "
        "Write no numbers of your own in this section."
    ),
)


def retrieve_refusals(tools: AnalystTools) -> RetrievedSection:
    exhibits = (
        retrieve.refusal(
            tools,
            id="post_repeal",
            label="data after the repeal",
            call='query(table="national_annual_series", fy_from="2027-28")',
            table=_NATIONAL,
            fy_from="2027-28",
        ),
        retrieve.refusal(
            tools,
            id="monthly",
            label="a monthly figure",
            call='query(table="district_flagship", month="2022-04")',
            table=_DISTRICT,
            month="2022-04",
        ),
        retrieve.refusal(
            tools,
            id="rate_at_state_grain",
            label="the wage rate at state grain",
            call='query(table="state_annual_series", metrics=["avg_wage_rate_per_day"])',
            table=_STATE,
            metrics=[_WAGE_RATE],
        ),
        retrieve.refusal(
            tools,
            id="district_before_the_flagship",
            label="district data before the flagship era",
            call='query(table="district_flagship", fy_to="2015-16")',
            table=_DISTRICT,
            fy_to="2015-16",
        ),
        retrieve.refusal(
            tools,
            id="malformed_year",
            label="a malformed financial-year label",
            call='query(table="state_annual_series", fy_from="2019")',
            table=_STATE,
            fy_from="2019",
        ),
        retrieve.refusal(
            tools,
            id="unknown_geography",
            label="a geography that does not exist",
            call='query(table="state_annual_series", states=["Atlantis"])',
            table=_STATE,
            states=["Atlantis"],
        ),
        retrieve.refusal(
            tools,
            id="lineage_through_query",
            label="the lineage table through the query verb",
            call='query(table="lineage")',
            table="lineage",
        ),
    )
    return RetrievedSection(plan=REFUSALS, figures=(), derivations=(), refusals=exhibits)


# --- C7: the district set -----------------------------------------------------------------------

DISTRICTS = SectionPlan(
    key="districts",
    title="The district set is not a constant",
    brief=(
        "Districts split over the life of the scheme, so the number of districts reporting is not "
        "fixed. Using the counts of district person-days facts (one such fact per district per "
        "year), give the number of districts reporting in the flagship's first year, FY 2018-19, "
        "and in FY 2025-26, the last complete financial year of the scheme.\n\n"
        "The difference between those two counts is a NET figure — additions minus any districts "
        "that stopped reporting — and you must call it a net increase, not a count of districts "
        "added. The record does not tell us that nothing was subtracted.\n\n"
        "Explain what the record does about splits: each fact stays filed under the geography that "
        "existed at its OWN period, and is never forward-mapped across a split — redistributing an "
        "old district's value across its successors would require an allocation the source never "
        "published, which would be inventing data. The rise in the count is districts dividing, "
        "not territory being added."
    ),
)


def retrieve_districts(tools: AnalystTools) -> RetrievedSection:
    first_year = retrieve.fetch_cohort(
        tools,
        id="districts_2018_19",
        label="districts reporting person-days in FY 2018-19 (the flagship's first year)",
        table=_DISTRICT,
        metrics=[_PERSONDAYS],
        fy_from="2018-19",
        fy_to="2018-19",
        filter=cohort.ALL,
    )
    later = retrieve.fetch_cohort(
        tools,
        id="districts_2025_26",
        label="districts reporting person-days in FY 2025-26 (the last complete year)",
        table=_DISTRICT,
        metrics=[_PERSONDAYS],
        fy_from="2025-26",
        fy_to="2025-26",
        filter=cohort.ALL,
    )
    # A difference of two reporting counts is a NET change: it cannot see a district that stopped
    # reporting being offset by two that started. The label says so, so the prose cannot overstate.
    growth = retrieve.derived(
        id="districts_net_increase",
        label=(
            "NET increase in districts reporting between FY 2018-19 and FY 2025-26 "
            "(additions minus any that stopped reporting — not a count of districts added)"
        ),
        operation=derive.DIFFERENCE,
        inputs=[later, first_year],
        unit="districts",
    )
    floor_refusal = retrieve.refusal(
        tools,
        id="district_floor",
        label="asking for district data before the flagship era",
        call='query(table="district_flagship", fy_to="2015-16")',
        table=_DISTRICT,
        fy_to="2015-16",
    )
    districts_by_year = tuple(
        retrieve.fetch_cohort(
            tools,
            id=f"districts_by_year_{fy.replace('-', '_')}",
            label=f"districts reporting person-days in FY {fy}",
            table=_DISTRICT,
            metrics=[_PERSONDAYS],
            fy_from=fy,
            fy_to=fy,
            filter=cohort.ALL,
        )
        for fy in _FLAGSHIP_YEARS
    )

    return RetrievedSection(
        plan=DISTRICTS,
        figures=(),
        derivations=(growth,),
        cohorts=(first_year, later),
        refusals=(floor_refusal,),
        series_cohorts=districts_by_year,
    )


# --- Front and back matter: the frame a stranger needs ------------------------------------------

ABSTRACT = SectionPlan(
    key="abstract",
    title="Abstract",
    brief=(
        "One paragraph. State what this document is: a reconciled, lineage-traced record of "
        "MGNREGA — India's rural employment guarantee, in force from 2006 until its repeal "
        "effective 30 June 2026 — assembled from the many separately-published government "
        "datasets on data.gov.in into one canonical annual series, and read here by an analyst "
        "that can see it only through a governed query interface. Then the headline findings, "
        "using the presentation figures given: the scale the scheme reached at its peak and how "
        "many times the first year that was; the two eras of sourcing; the cells where the "
        "publishers disagree; the cells the record withholds rather than guessing. Close on what "
        "makes this document unusual: every number in it was machine-verified against the served "
        "data, and any figure that could not be verified was blocked rather than printed."
    ),
)


def retrieve_abstract(tools: AnalystTools) -> RetrievedSection:
    peak = retrieve.fetch_figure(
        tools,
        id="abstract_peak_persondays",
        label="person-days generated at the scheme's peak, FY 2020-21",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2020-21"),
    )
    first = retrieve.fetch_figure(
        tools,
        id="abstract_first_persondays",
        label="person-days generated in the first year, FY 2006-07",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2006-07"),
    )
    peak_billions = retrieve.derived(
        id="abstract_peak_billions",
        label="peak-year person-days, in billions",
        operation=derive.TO_BILLIONS,
        inputs=[peak],
        unit="billion person-days",
    )
    growth = retrieve.derived(
        id="abstract_growth",
        label="peak-year person-days as a multiple of the first year's",
        operation=derive.RATIO_2DP,
        inputs=[peak, first],
        unit="times",
    )
    flagged = retrieve.fetch_cohort(
        tools,
        id="abstract_flagged",
        label="state-year cells where publishers materially disagree",
        table=_STATE,
        filter=cohort.FLAGGED_DISAGREEMENT,
    )
    withheld = retrieve.fetch_cohort(
        tools,
        id="abstract_partial_nulls",
        label="state-year cells the record withholds as partial-period-only",
        table=_STATE,
        filter=cohort.PARTIAL_PERIOD_ONLY,
    )
    return RetrievedSection(
        plan=ABSTRACT,
        figures=(peak, first),
        derivations=(peak_billions, growth),
        cohorts=(flagged, withheld),
    )


INTRODUCTION = SectionPlan(
    key="introduction",
    title="Introduction",
    brief=(
        "Write for a reader with ZERO prior context — assume they have never heard of MGNREGA.\n\n"
        "Explain, in plain prose: MGNREGA (the Mahatma Gandhi National Rural Employment Guarantee "
        "Act) was India's rural employment guarantee, enacted in 2005 and running from financial "
        "year 2006-07. It gave rural households a legal right to a fixed quota of paid manual "
        "work each year; the state's obligation was to provide it on demand. Work is measured in "
        "PERSON-DAYS (one day of work by one person), spending in rupees, participation in "
        "households employed. It was repealed effective 30 June 2026, so the record is now closed: "
        "no new data will ever be published for it.\n\n"
        "Say NOTHING about what replaced it. Whether a successor programme exists, and what it "
        "does, is outside this record — the served data contains no such fact, so this document "
        "cannot assert one.\n\n"
        "Then explain what this document is and is not. It is a reading of a reconciled dataset "
        "assembled from the many separately-published government datasets on India's open-data "
        "portal, which disagree with each other on units, geography and even on the numbers "
        "themselves. It is NOT an evaluation of the scheme's policy merits, and it draws no "
        "causal conclusions: it says what the record contains, how confidently, and where it "
        "refuses to answer. Give the span of the record in years, and note that the last complete "
        "financial year is 2025-26 (the figure for the final year covers April 2026 alone).\n\n"
        "Do not preview the findings in detail — that is the body's job."
    ),
)


def retrieve_introduction(tools: AnalystTools) -> RetrievedSection:
    last_complete = retrieve.fetch_figure(
        tools,
        id="intro_last_complete",
        label="national person-days generated in the last complete year, FY 2025-26",
        geography="India",
        spec=QuerySpec(_NATIONAL, _PERSONDAYS, "2025-26"),
    )
    last_billions = retrieve.derived(
        id="intro_last_billions",
        label="last complete year's person-days, in billions",
        operation=derive.TO_BILLIONS,
        inputs=[last_complete],
        unit="billion person-days",
    )
    sealed = retrieve.refusal(
        tools,
        id="intro_sealed",
        label="asking for data after the repeal",
        call='query(table="national_annual_series", fy_from="2027-28")',
        table=_NATIONAL,
        fy_from="2027-28",
    )
    return RetrievedSection(
        plan=INTRODUCTION,
        figures=(last_complete,),
        derivations=(last_billions,),
        refusals=(sealed,),
    )


METHODOLOGY = SectionPlan(
    key="methodology",
    title="Methodology",
    brief=(
        "Explain, in plain English and without jargon, how the record was built and what its "
        "guarantees mean. Four things:\n\n"
        "(1) TWO ERAS OF SOURCING. From FY 2018-19 the figures come from the government's own "
        "district-level management information system, the primary production authority for the "
        "period it covers. Before that, the flagship system published nothing, so the years back "
        "to 2006-07 are carried by archived secondary sources — statistical yearbooks and tables "
        "tabled in Parliament in answer to questions. The counts of facts from each era are "
        "given. The join between them is a seam, and the report does not pretend otherwise.\n\n"
        "(2) WHEN SOURCES DISAGREE. Where two publishers of comparable standing disagree on the "
        "same cell, the pipeline adjudicates by a documented rule and keeps the rejected value, "
        "its publisher and the size of the gap in the record's lineage — the disagreement is "
        "published, not hidden. Where the primary district management information system disagrees "
        "with a figure tabled in Parliament for the same cell, authority decides: the primary "
        "system stands, and the divergence is recorded as a flagged note rather than adjudicated "
        "between peers. (Do not characterise how the Parliament-tabled figures were produced or "
        "where they came from — the record does not say, and neither does this document.) A "
        "disagreement is only "
        "counted at all if it clears a two-part materiality floor: it must be large in absolute "
        "terms AND large relative to the value, so that rounding noise is never reported as a "
        "conflict.\n\n"
        "(3) WHAT IS WITHHELD. Where the pipeline cannot honestly assert a value — the only "
        "available reading covers part of a year, or an incomplete aggregate contradicts a "
        "complete one — the cell is left empty and carries the reason why. An empty cell is never "
        "written as a zero.\n\n"
        "(4) WHAT 'MACHINE-VERIFIED' MEANS HERE. The prose in this document was written by a "
        "language model, but the model never chose a number. Each figure was retrieved from the "
        "query server by code, with its provenance attached; figures the report combines (sums, "
        "ratios, unit conversions) were computed by code and recomputed independently afterwards; "
        "and every number in the finished prose was checked back against the served data. A "
        "number that failed the check blocked its section from the report entirely. The model "
        "cannot query the data and cannot do arithmetic — it can only narrate what it was handed."
    ),
)


def retrieve_methodology(tools: AnalystTools) -> RetrievedSection:
    historical = retrieve.fetch_cohort(
        tools,
        id="method_historical",
        label="national facts carried by the pre-2018 archived sources",
        table=_NATIONAL,
        filter=cohort.HISTORICAL_ERA,
    )
    flagship = retrieve.fetch_cohort(
        tools,
        id="method_flagship",
        label="national facts carried by the district management information system",
        table=_NATIONAL,
        filter=cohort.FLAGSHIP_ERA,
    )
    malformed = retrieve.refusal(
        tools,
        id="method_malformed_year",
        label="a malformed financial-year label",
        call='query(table="state_annual_series", fy_from="2019")',
        table=_STATE,
        fy_from="2019",
    )
    return RetrievedSection(
        plan=METHODOLOGY,
        figures=(),
        derivations=(),
        cohorts=(historical, flagship),
        refusals=(malformed,),
    )


LIMITATIONS = SectionPlan(
    key="limitations",
    title="Limitations",
    brief=(
        "State plainly what this record cannot do. Four limits, each with its reason:\n\n"
        "(1) NO MONTHLY DATA, AND WHY. The record is annual at every level of geography. The "
        "source system did publish month-by-month columns, but those columns are cumulative "
        "running totals for the year to date, not monthly figures — and its published wage-rate "
        "column is a running ratio of money paid to days worked, which early in a year is "
        "distorted by arrears paid for the previous year's work. Summing those columns, or "
        "reading one as a monthly rate, produces figures that are badly wrong. Rather than "
        "publish a number that looks monthly but is not, the record refuses monthly questions "
        "outright; quote the server's reason. A consequence worth stating: figures that "
        "circulate elsewhere and are derived from those monthly columns cannot be reproduced or "
        "checked here, and this document does not repeat them.\n\n"
        "(2) THE SEAM AT FY 2017-18. The year before the district system begins is the record's "
        "weakest: the count of withheld cells in that single year is given. Comparisons that "
        "straddle it should be made with care.\n\n"
        "(3) WAGE-RATE ARTIFACTS SURVIVE INTO THE ANNUAL FIGURES. The count of district-year wage "
        "rates above Rs 1,000 a day is given, and the highest of them is given. State plainly "
        "that these are NOT wages anyone was paid — a plausible MGNREGA daily wage is an order of "
        "magnitude lower. They are defects of the source series, carried into the record "
        "faithfully with their provenance rather than quietly deleted, so that a reader can see "
        "them and discount them.\n\n"
        "(4) A METRIC THAT SIMPLY DOES NOT EXIST BEFORE 2018. Active workers is only reported from "
        "FY 2018-19 onward; the count of such facts in its first year is given. Comparing it "
        "across the full span would compare a metric against its own absence."
    ),
)


def retrieve_limitations(tools: AnalystTools) -> RetrievedSection:
    seam = retrieve.fetch_cohort(
        tools,
        id="limits_seam_nulls",
        label="cells the record withholds in FY 2017-18, the seam year",
        table=_STATE,
        fy_from="2017-18",
        fy_to="2017-18",
        filter=cohort.VALUE_IS_NULL,
    )
    implausible = retrieve.fetch_cohort(
        tools,
        id="limits_implausible_rates",
        label="district-year wage rates above Rs 1,000 a day (source artifacts, not wages paid)",
        table=_DISTRICT,
        metrics=[_WAGE_RATE],
        filter=cohort.WAGE_ABOVE_IMPLAUSIBILITY_FLOOR,
    )
    active_workers = retrieve.fetch_cohort(
        tools,
        id="limits_active_workers",
        label="active-workers facts at state grain in FY 2018-19, the metric's first year",
        table=_STATE,
        metrics=["active_workers"],
        fy_from="2018-19",
        fy_to="2018-19",
        filter=cohort.ALL,
    )
    highest = retrieve.fetch_figure(
        tools,
        id="limits_highest_rate",
        label=(
            "the highest district-year wage rate in the record (Hooghly, West Bengal, FY 2023-24)"
        ),
        geography="Hooghly, West Bengal",
        spec=QuerySpec(_DISTRICT, _WAGE_RATE, "2023-24", "West Bengal", "Hooghly"),
    )
    monthly = retrieve.refusal(
        tools,
        id="limits_monthly",
        label="asking for a monthly figure",
        call='query(table="district_flagship", month="2022-04")',
        table=_DISTRICT,
        month="2022-04",
    )
    return RetrievedSection(
        plan=LIMITATIONS,
        figures=(highest,),
        derivations=(),
        cohorts=(seam, implausible, active_workers),
        refusals=(monthly,),
    )


SECTIONS: dict[str, tuple[SectionPlan, Retriever]] = {
    ABSTRACT.key: (ABSTRACT, retrieve_abstract),
    INTRODUCTION.key: (INTRODUCTION, retrieve_introduction),
    METHODOLOGY.key: (METHODOLOGY, retrieve_methodology),
    LIMITATIONS.key: (LIMITATIONS, retrieve_limitations),
    NATIONAL_SERIES.key: (NATIONAL_SERIES, retrieve_national_series),
    DISAGREEMENTS.key: (DISAGREEMENTS, retrieve_disagreements),
    GOA_SPINE.key: (GOA_SPINE, retrieve_goa_spine),
    WAGE_RATE.key: (WAGE_RATE, retrieve_wage_rate),
    COVERAGE.key: (COVERAGE, retrieve_coverage),
    DISTRICTS.key: (DISTRICTS, retrieve_districts),
    REFUSALS.key: (REFUSALS, retrieve_refusals),
}

# The report's reading order: front matter, the findings, then the limits.
REPORT_ORDER: tuple[str, ...] = (
    ABSTRACT.key,
    INTRODUCTION.key,
    METHODOLOGY.key,
    NATIONAL_SERIES.key,
    DISAGREEMENTS.key,
    GOA_SPINE.key,
    WAGE_RATE.key,
    COVERAGE.key,
    DISTRICTS.key,
    REFUSALS.key,
    LIMITATIONS.key,
)
