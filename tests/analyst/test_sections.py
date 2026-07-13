"""The pilot section's retrieval, against the real dist.

Goa FY 2022-23: the two districts' person-days sum exactly to the state figure, and the ninth
metric — the wage rate — refuses to be served at state grain because it is a rate, not an additive
quantity. These are the figures the claim inventory verified (C3′).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from data_platform.analyst import sections
from data_platform.analyst.models import RetrievedSection
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader

pytestmark = pytest.mark.golden


@pytest.fixture(scope="module")
def section() -> RetrievedSection:
    tools = DirectTools(loader.load_dataset())
    return sections.retrieve_goa_spine(tools)


def test_district_persondays_sum_to_the_state_figure(section: RetrievedSection) -> None:
    north = section.figure("north_goa_persondays")
    south = section.figure("south_goa_persondays")
    state = section.figure("goa_persondays")
    assert north.value == Decimal("42253")
    assert south.value == Decimal("51751")
    assert state.value == Decimal("94004")

    summed = next(d for d in section.derivations if d.id == "district_sum_persondays")
    assert summed.operation == "sum"
    assert summed.value == Decimal("94004")
    assert summed.inputs == ("north_goa_persondays", "south_goa_persondays")

    residual = next(d for d in section.derivations if d.id == "spine_residual")
    assert residual.value == Decimal("0")


def test_every_figure_carries_a_source_and_an_as_of(section: RetrievedSection) -> None:
    for figure in section.figures:
        assert figure.fact_id
        assert figure.sources
        for source in figure.sources:
            assert source["resource_id"]
            assert source["as_of"]


def test_the_state_persondays_fact_is_cross_publisher_corroborated(
    section: RetrievedSection,
) -> None:
    lineage = section.figure("goa_persondays").lineage
    assert lineage["reconciliation_status"] == "corroborated"
    assert lineage["resolution_rule_id"] == "R4-REC-01"


def test_the_section_exhibits_the_rate_and_monthly_refusals(
    section: RetrievedSection,
) -> None:
    codes = {r.payload["code"] for r in section.refusals}
    assert codes == {"unknown_metric", "monthly_wage_unavailable"}
