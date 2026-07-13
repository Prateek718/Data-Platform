"""The graph: a drafter it cannot trust produces no report, never a wrong one."""

from __future__ import annotations

import pytest

from data_platform.analyst import graph, sections
from data_platform.analyst.models import RetrievedSection
from data_platform.analyst.tools import AnalystTools, DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import PLAN, build_section
from tests.analyst.fakes import ScriptedDrafter
from tests.conftest import SyntheticDist

HONEST = (
    "Jammu and Kashmir generated 1,000,000 person-days in FY 2018-19, of which Anantnag "
    "accounted for 300,000 — a share of 0.3."
)
LIE = "Jammu and Kashmir generated 1,400,000 person-days in FY 2018-19."


@pytest.fixture
def tools(synthetic_dist: SyntheticDist) -> DirectTools:
    return DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )


@pytest.fixture(autouse=True)
def register_test_section(monkeypatch: pytest.MonkeyPatch) -> None:
    """Register the synthetic-dist section in the section registry for the duration of a test."""

    def retriever(tools: AnalystTools) -> RetrievedSection:
        return build_section(tools)

    monkeypatch.setitem(sections.SECTIONS, PLAN.key, (PLAN, retriever))


def _run(tools: DirectTools, drafter: ScriptedDrafter) -> dict[str, object]:
    return graph.run(
        tools=tools,
        drafter=drafter,
        section_keys=[PLAN.key],
        generated_at="2026-07-13T00:00:00Z",
    )


def test_honest_draft_is_assembled_into_a_report(tools: DirectTools) -> None:
    drafter = ScriptedDrafter(HONEST)
    report = _run(tools, drafter)
    written = report["sections"]
    assert isinstance(written, list)
    assert len(written) == 1
    assert written[0]["prose"] == HONEST
    assert written[0]["attempts"] == 1
    assert drafter.calls == 1


def test_a_lying_drafter_produces_no_report(tools: DirectTools) -> None:
    """The whole point: the verifier blocks, the graph retries, and then it fails loudly."""
    drafter = ScriptedDrafter(LIE)
    with pytest.raises(graph.VerificationFailure) as excinfo:
        _run(tools, drafter)
    assert drafter.calls == graph.MAX_DRAFT_ATTEMPTS
    message = str(excinfo.value)
    assert PLAN.key in message
    assert "1,400,000" in message  # the mismatch report rides along, so a failed run is diagnosable


def test_the_drafter_is_handed_the_mismatch_report_and_can_recover(tools: DirectTools) -> None:
    drafter = ScriptedDrafter(LIE, HONEST)
    report = _run(tools, drafter)
    sections_written = report["sections"]
    assert isinstance(sections_written, list)
    assert sections_written[0]["attempts"] == 2
    assert drafter.calls == 2
    retry = drafter.requests[1]
    assert retry.mismatches  # the verifier's complaint was handed back
    assert retry.previous_prose == LIE


def test_figures_and_lineage_reach_the_drafter(tools: DirectTools) -> None:
    drafter = ScriptedDrafter(HONEST)
    _run(tools, drafter)
    request = drafter.requests[0]
    assert {f.id for f in request.section.figures} == {"state_persondays", "anantnag_persondays"}
    assert all(fig.sources for fig in request.section.figures)
