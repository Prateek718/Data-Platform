"""Cohort figures: a count over many facts, and how it proves itself.

A single fact carries one fact_id and one lineage payload. A count — "193 null cells", "34 flagged
disagreements" — rests on a whole set of facts, so its provenance is the query, the named
deterministic filter, EVERY member fact_id, and the distinct sources behind those members. The
verifier re-executes the query, re-applies the filter, and recomputes: a count the served data does
not produce blocks the section exactly like an invented number does.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from data_platform.analyst import cohort, retrieve, verify
from data_platform.analyst.models import Cohort
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import build_section
from tests.conftest import SyntheticDist


@pytest.fixture
def tools(synthetic_dist: SyntheticDist) -> DirectTools:
    return DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )


def _nulls(tools: DirectTools) -> Cohort:
    """The synthetic state table holds exactly two null cells (st02 unadjudicated, st04 partial)."""
    return retrieve.fetch_cohort(
        tools,
        id="state_nulls",
        label="null cells in the state series",
        table="state_annual_series",
        filter=cohort.VALUE_IS_NULL,
    )


def test_a_cohort_counts_the_facts_the_filter_selects(tools: DirectTools) -> None:
    nulls = _nulls(tools)
    assert nulls.value == Decimal("2")
    assert set(nulls.member_fact_ids) == {"st02", "st04"}
    assert nulls.filter == cohort.VALUE_IS_NULL


def test_a_cohort_carries_the_distinct_sources_behind_its_members(tools: DirectTools) -> None:
    for source in _nulls(tools).sources:
        assert source["resource_id"]
    assert any(source["as_of"] for source in _nulls(tools).sources)


def test_an_honest_count_passes_verification(tools: DirectTools) -> None:
    section = replace(build_section(tools), cohorts=(_nulls(tools),))
    prose = "The state series carries 2 null cells. The state generated 1,000,000 person-days."
    assert verify.verify(section, prose, tools).ok


def test_an_inflated_count_blocks_the_section(tools: DirectTools) -> None:
    """The count is recomputed from the served data, not taken from the cohort object."""
    tampered = replace(_nulls(tools), value=Decimal("7"))
    section = replace(build_section(tools), cohorts=(tampered,))
    report = verify.verify(section, "The state series carries 7 null cells.", tools)
    assert not report.ok
    assert "state_nulls" in report.render()


def test_a_doctored_member_set_blocks_the_section(tools: DirectTools) -> None:
    """The count can be right while the members are wrong — both are checked."""
    real = _nulls(tools)
    tampered = replace(real, member_fact_ids=("st01", "st03"))
    section = replace(build_section(tools), cohorts=(tampered,))
    report = verify.verify(section, "The state series carries 2 null cells.", tools)
    assert not report.ok
    assert "members" in report.render()


def test_a_cohort_with_no_members_is_a_real_finding(tools: DirectTools) -> None:
    """Zero is a claim the record supports: no wage facts exist for the repeal-truncated year.

    An empty cohort has no member facts and therefore no sources — it is the ABSENCE of facts, and
    demanding provenance for facts that do not exist would make the honest answer unprovable.
    """
    empty = retrieve.fetch_cohort(
        tools,
        id="wage_facts_2026_27",
        label="district wage-rate facts in FY 2026-27",
        table="district_flagship",
        metrics=["avg_wage_rate_per_day"],
        fy_from="2026-27",
        fy_to="2026-27",
        filter=cohort.ALL,
    )
    assert empty.value == Decimal("0")
    assert empty.member_fact_ids == ()
    assert empty.sources == ()

    section = replace(build_section(tools), cohorts=(empty,))
    assert verify.verify(section, "No wage facts exist for FY 2026-27: 0 of them.", tools).ok


def test_a_derivation_may_combine_cohorts(tools: DirectTools) -> None:
    """193 nulls is 174 + 19 — a derivation over two counts, recomputed by the verifier."""
    nulls = _nulls(tools)
    doubled = retrieve.derived(
        id="all_nulls",
        label="null cells across the record",
        operation="sum",
        inputs=[nulls, nulls],
        unit="cells",
    )
    assert doubled.value == Decimal("4")

    section = replace(build_section(tools), cohorts=(nulls,), derivations=(doubled,))
    assert verify.verify(section, "The record carries 4 null cells in total.", tools).ok


def test_an_unknown_filter_is_an_error_not_a_guess(tools: DirectTools) -> None:
    with pytest.raises(ValueError, match="unknown filter"):
        retrieve.fetch_cohort(
            tools,
            id="bogus",
            label="a filter nobody defined",
            table="state_annual_series",
            filter="value_is_suspicious",
        )


def test_a_cohorts_own_label_may_be_quoted(tools: DirectTools) -> None:
    """Labels are authored evidence handed to the drafter; a number in one is not an invention.

    Caught on the second full run: the wage section's label says "above Rs 1,000/day", the drafter
    repeated the threshold, and the verifier called 1,000 an invented number.
    """
    labelled = replace(
        _nulls(tools), label="null cells withheld (the 2 of them) above the Rs 1,000/day floor"
    )
    section = replace(build_section(tools), cohorts=(labelled,))
    prose = "The floor is Rs 1,000/day. The series carries 2 null cells."
    assert verify.verify(section, prose, tools).ok
