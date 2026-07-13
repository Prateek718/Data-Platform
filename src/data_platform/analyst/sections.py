"""The report's sections — each one a plan plus the retrieval that backs it.

A section is only here if the claim inventory (``docs/notes/STAGE8-CLAIM-INVENTORY.md``) verified
it against the served surface. Retrieval is a pure function of the tools: it fetches figures,
computes the section's declared derivations, and captures the refusals the section exhibits.
"""

from __future__ import annotations

from collections.abc import Callable

from data_platform.analyst import derive, retrieve
from data_platform.analyst.models import QuerySpec, RetrievedSection, SectionPlan
from data_platform.analyst.tools import AnalystTools

Retriever = Callable[[AnalystTools], RetrievedSection]

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

_GOA = "Goa"
_FY = "2022-23"


def retrieve_goa_spine(tools: AnalystTools) -> RetrievedSection:
    """Goa FY 2022-23: districts sum to the state spine; the wage rate does not sum at all."""
    north = retrieve.fetch_figure(
        tools,
        id="north_goa_persondays",
        label="North Goa person-days generated, FY 2022-23",
        geography="North Goa, Goa",
        spec=QuerySpec("district_flagship", "persondays_generated", _FY, _GOA, "North Goa"),
    )
    south = retrieve.fetch_figure(
        tools,
        id="south_goa_persondays",
        label="South Goa person-days generated, FY 2022-23",
        geography="South Goa, Goa",
        spec=QuerySpec("district_flagship", "persondays_generated", _FY, _GOA, "South Goa"),
    )
    state = retrieve.fetch_figure(
        tools,
        id="goa_persondays",
        label="Goa state person-days generated, FY 2022-23",
        geography="Goa",
        spec=QuerySpec("state_annual_series", "persondays_generated", _FY, _GOA),
    )
    north_rate = retrieve.fetch_figure(
        tools,
        id="north_goa_wage_rate",
        label="North Goa average wage rate per day, FY 2022-23",
        geography="North Goa, Goa",
        spec=QuerySpec("district_flagship", "avg_wage_rate_per_day", _FY, _GOA, "North Goa"),
    )
    south_rate = retrieve.fetch_figure(
        tools,
        id="south_goa_wage_rate",
        label="South Goa average wage rate per day, FY 2022-23",
        geography="South Goa, Goa",
        spec=QuerySpec("district_flagship", "avg_wage_rate_per_day", _FY, _GOA, "South Goa"),
    )

    district_sum = retrieve.derived(
        id="district_sum_persondays",
        label="North Goa plus South Goa person-days",
        operation=derive.SUM,
        inputs=[north, south],
        unit="person-days",
    )
    # The residual is the claim: the drill-down reconciles to the spine EXACTLY, and the report says
    # so with a number rather than an adjective. It is a difference of the state fact against the
    # district sum's own inputs, so the verifier recomputes it from served facts alone.
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
        table="state_annual_series",
        metrics=["avg_wage_rate_per_day"],
        states=[_GOA],
    )
    monthly_refusal = retrieve.refusal(
        tools,
        id="monthly_figure",
        label="asking for a monthly figure",
        call='query(table="district_flagship", states=["Goa"], month="2022-04")',
        table="district_flagship",
        states=[_GOA],
        month="2022-04",
    )

    return RetrievedSection(
        plan=GOA_SPINE,
        figures=(north, south, state, north_rate, south_rate),
        derivations=(district_sum, residual),
        refusals=(rate_refusal, monthly_refusal),
    )


SECTIONS: dict[str, tuple[SectionPlan, Retriever]] = {
    GOA_SPINE.key: (GOA_SPINE, retrieve_goa_spine),
}
