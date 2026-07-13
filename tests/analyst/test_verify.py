"""The verifier is the report's spine: no number survives it unless the served data backs it.

These tests are written as attacks. Honest prose must pass; every way a drafter could bluff — an
invented number, a rounded one, a mis-stated derivation, a figure with no provenance, a value that
no longer matches the served data — must block the section.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from data_platform.analyst import verify
from data_platform.analyst.models import Derivation, RetrievedSection
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import build_section
from tests.conftest import SyntheticDist

HONEST = (
    "Jammu and Kashmir generated 1,000,000 person-days in FY 2018-19. Anantnag accounts for "
    "300,000 of them, a share of 0.3. Asked for a monthly figure, the record refuses: it is "
    "annual-only."
)


@pytest.fixture
def tools(synthetic_dist: SyntheticDist) -> DirectTools:
    return DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )


@pytest.fixture
def section(tools: DirectTools) -> RetrievedSection:
    return build_section(tools)


def test_honest_prose_passes(section: RetrievedSection, tools: DirectTools) -> None:
    report = verify.verify(section, HONEST, tools)
    assert report.ok, report.render()


def test_an_invented_number_blocks_the_section(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """The lie the whole stage exists to catch."""
    lie = "Jammu and Kashmir generated 1,400,000 person-days in FY 2018-19."
    report = verify.verify(section, lie, tools)
    assert not report.ok
    assert "1,400,000" in report.render()


def test_a_rounded_number_blocks_the_section(section: RetrievedSection, tools: DirectTools) -> None:
    """Rounding is how a plausible-sounding wrong number gets in. 1,000,000 is not '1 million'."""
    rounded = "Jammu and Kashmir generated roughly 1.0 million person-days in FY 2018-19."
    report = verify.verify(section, rounded, tools)
    assert not report.ok


def test_financial_year_labels_are_not_numeric_claims(
    section: RetrievedSection, tools: DirectTools
) -> None:
    prose = "In FY 2018-19 the state generated 1,000,000 person-days; Anantnag contributed 300,000."
    assert verify.verify(section, prose, tools).ok


def test_a_period_the_section_never_retrieved_blocks(
    section: RetrievedSection, tools: DirectTools
) -> None:
    prose = "In FY 2019-20 the state generated 1,000,000 person-days."
    report = verify.verify(section, prose, tools)
    assert not report.ok
    assert "2019-20" in report.render()


def test_a_derived_number_may_be_narrated(section: RetrievedSection, tools: DirectTools) -> None:
    assert verify.verify(section, "Anantnag's share of the state total is 0.3.", tools).ok


def test_a_derivation_whose_declared_value_is_wrong_blocks(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """The verifier recomputes every derivation from its declared inputs, and does not trust it."""
    tampered = replace(section.derivations[0], value=Decimal("0.9"))
    bad = replace(section, derivations=(tampered,))
    report = verify.verify(bad, "Anantnag's share of the state total is 0.9.", tools)
    assert not report.ok
    assert "anantnag_share" in report.render()


def test_a_derivation_over_undeclared_inputs_blocks(
    section: RetrievedSection, tools: DirectTools
) -> None:
    orphan = Derivation(
        id="orphan",
        label="a derivation whose inputs the retriever never fetched",
        operation="ratio",
        inputs=("ghost_figure", "state_persondays"),
        value=Decimal("2"),
        unit="ratio",
    )
    bad = replace(section, derivations=(*section.derivations, orphan))
    report = verify.verify(bad, HONEST, tools)
    assert not report.ok
    assert "ghost_figure" in report.render()


def test_a_figure_without_lineage_blocks(section: RetrievedSection, tools: DirectTools) -> None:
    """A figure without a lineage reference is a failure, not a warning."""
    stripped = replace(section.figures[0], lineage={})
    bad = replace(section, figures=(stripped, section.figures[1]))
    report = verify.verify(bad, HONEST, tools)
    assert not report.ok
    assert "lineage" in report.render().lower()


def test_a_figure_that_no_longer_matches_the_served_data_blocks(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """Defense in depth: the backing query is re-executed, not taken on trust."""
    tampered = replace(section.figures[0], value=Decimal("999999"))
    bad = replace(section, figures=(tampered, section.figures[1]))
    report = verify.verify(bad, "The state generated 999,999 person-days.", tools)
    assert not report.ok
    assert "state_persondays" in report.render()


def test_number_tokens_ignores_financial_years() -> None:
    assert verify.number_tokens("In 2018-19 it was 1,000,000.") == ["1,000,000"]


def test_renderings_accept_grouped_and_raw() -> None:
    assert {"1000000", "1,000,000"} <= verify.renderings(Decimal("1000000"))
