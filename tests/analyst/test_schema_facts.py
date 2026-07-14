"""A denominator must be as traceable as its numerators.

"Seven of the eight metrics" rests on an eight that is not a fact about the data but about the
CONTRACT. The schema declares it, the report records the declaration, and the verifier re-executes
get_schema and recounts — so the denominator cannot be asserted any more than a figure can.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from data_platform.analyst import retrieve, verify
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import build_section
from tests.conftest import SyntheticDist


@pytest.fixture
def tools(synthetic_dist: SyntheticDist) -> DirectTools:
    return DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )


def test_the_metric_count_is_read_from_the_served_schema(tools: DirectTools) -> None:
    fact = retrieve.fetch_metric_count(
        tools,
        id="metrics",
        label="metrics the national series carries",
        table="national_annual_series",
    )
    assert fact.value == Decimal(8)
    assert "persondays_generated" in fact.metrics
    assert fact.call == 'get_schema(table="national_annual_series")'


def test_a_schema_count_may_be_cited_in_prose(tools: DirectTools) -> None:
    fact = retrieve.fetch_metric_count(
        tools,
        id="metrics",
        label="metrics the national series carries",
        table="national_annual_series",
    )
    section = replace(build_section(tools), schema_facts=(fact,))
    prose = "The series carries 8 metrics. The state generated 1,000,000 person-days."
    assert verify.verify(section, prose, tools).ok


def test_a_miscounted_denominator_blocks_the_section(tools: DirectTools) -> None:
    fact = retrieve.fetch_metric_count(
        tools,
        id="metrics",
        label="metrics the national series carries",
        table="national_annual_series",
    )
    tampered = replace(fact, value=Decimal(9))
    section = replace(build_section(tools), schema_facts=(tampered,))
    report = verify.verify(section, "The series carries 9 metrics.", tools)
    assert not report.ok
    assert "metrics" in report.render()
