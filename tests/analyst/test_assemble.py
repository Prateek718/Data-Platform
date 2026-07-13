"""report.json is the contract a viewer consumes: typed figures, no number without provenance."""

from __future__ import annotations

import json

import pytest

from data_platform.analyst import assemble
from data_platform.analyst.models import VerifiedSection
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import build_section
from tests.conftest import SyntheticDist

PROSE = "The state generated 1,000,000 person-days; Anantnag accounted for 300,000, a share of 0.3."


@pytest.fixture
def report(synthetic_dist: SyntheticDist) -> dict[str, object]:
    tools = DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )
    section = VerifiedSection(retrieved=build_section(tools), prose=PROSE, attempts=1)
    return assemble.build_report([section], generated_at="2026-07-13T00:00:00Z")


def test_report_is_json_serializable(report: dict[str, object]) -> None:
    """The artifact must survive a round-trip to disk exactly — Decimals rendered as strings."""
    assert json.loads(json.dumps(report)) == report


def test_every_figure_is_a_typed_object_with_lineage(report: dict[str, object]) -> None:
    sections = report["sections"]
    assert isinstance(sections, list)
    figures = sections[0]["figures"]
    assert isinstance(figures, list)
    state = next(f for f in figures if f["id"] == "state_persondays")
    assert state["value"] == "1000000"
    assert state["unit"] == "person-days"
    assert state["metric"] == "persondays_generated"
    assert state["geography"] == "Jammu and Kashmir"
    assert state["period"] == "2018-19"
    assert state["fact_id"] == "st01"
    assert state["lineage"]["sources"]  # provenance travels with the figure


def test_derived_figures_declare_their_operation_and_input_facts(
    report: dict[str, object],
) -> None:
    sections = report["sections"]
    assert isinstance(sections, list)
    derived = sections[0]["derivations"]
    assert isinstance(derived, list)
    share = derived[0]
    assert share["operation"] == "ratio"
    assert share["value"] == "0.3"
    assert share["input_fact_ids"] == ["ds01", "st01"]  # the facts, not just the figure ids


def test_refusals_are_carried_as_the_objects_the_server_returned(
    report: dict[str, object],
) -> None:
    sections = report["sections"]
    assert isinstance(sections, list)
    refusals = sections[0]["refusals"]
    assert isinstance(refusals, list)
    assert refusals[0]["payload"]["code"] == "monthly_wage_unavailable"


def test_markdown_renders_the_prose_under_the_section_title(report: dict[str, object]) -> None:
    markdown = assemble.render_markdown(report)
    assert assemble.REPORT_TITLE in markdown
    assert "Jammu and Kashmir, FY 2018-19" in markdown
    assert PROSE in markdown
