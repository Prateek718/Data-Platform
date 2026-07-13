"""The report's sections — each one a plan plus the retrieval that backs it.

A section is only here if the claim inventory (``docs/notes/STAGE8-CLAIM-INVENTORY.md``) verified
it against the served surface. Retrieval is a pure function of the tools: it fetches figures,
computes the section's declared derivations, and captures any refusal the section exhibits.
"""

from __future__ import annotations

from collections.abc import Callable

from data_platform.analyst.models import RetrievedSection, SectionPlan
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


def retrieve_goa_spine(tools: AnalystTools) -> RetrievedSection:
    """Goa FY 2022-23: districts sum to the state spine; the wage rate does not sum at all."""
    raise NotImplementedError


SECTIONS: dict[str, tuple[SectionPlan, Retriever]] = {
    GOA_SPINE.key: (GOA_SPINE, retrieve_goa_spine),
}
