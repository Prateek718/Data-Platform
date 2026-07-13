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


def test_a_refusal_may_be_quoted_verbatim(section: RetrievedSection, tools: DirectTools) -> None:
    """A refusal object is served content: quoting it exactly is verifiable by string equality.

    Caught on the first live run — the drafter quoted the refusal call, whose month argument
    ("2022-04") the verifier read as a financial-year claim and blocked. The section's whole point
    is to show what the server says, so the exhibit's own text must be quotable.
    """
    quoted = section.refusals[0].call
    reason = section.refusals[0].payload["reason"]
    prose = (
        f'Asked for a monthly figure — {quoted} — the record refuses: "{reason}" '
        "The state generated 1,000,000 person-days."
    )
    assert verify.verify(section, prose, tools).ok


def test_a_doctored_quote_still_blocks(section: RetrievedSection, tools: DirectTools) -> None:
    """Only a VERBATIM quote is served content. Alter a digit and it is an invented number again."""
    doctored = section.refusals[0].call.replace("2022-04", "1,400,000")
    report = verify.verify(section, f"The record refuses: {doctored}", tools)
    assert not report.ok
    assert "1,400,000" in report.render()


def test_number_tokens_ignores_financial_years() -> None:
    assert verify.number_tokens("In 2018-19 it was 1,000,000.") == ["1,000,000"]


def test_renderings_accept_grouped_and_raw() -> None:
    assert {"1000000", "1,000,000"} <= verify.renderings(Decimal("1000000"))


def test_a_figure_followed_by_a_comma_is_still_that_figure(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """Caught on the full live run: '300,000, and' tokenized as '300,000,' and was rejected.

    A trailing separator is punctuation, not a digit. The drafter reworded around it, which is the
    verifier corrupting the report rather than protecting it.
    """
    prose = "Anantnag contributed 300,000, and the state generated 1,000,000 person-days."
    assert verify.verify(section, prose, tools).ok


def test_the_servers_own_refusal_numbers_may_be_narrated(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """A number inside a refusal the server returned is served content, quoted or paraphrased.

    Caught on the full live run: the model deleted the dates out of the server's own quoted reason
    ("MGNREGA was repealed effective, so the canonical series ends at FY") to satisfy the verifier.
    """
    reason = section.refusals[0].payload["reason"]
    assert isinstance(reason, str)
    prose = f"The record refuses monthly figures. It says: {reason[:40]}"
    assert verify.verify(section, prose, tools).ok


def test_numbers_the_section_brief_supplies_may_be_narrated(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """The brief is authored spec text in this repo, reviewed like code — not model output.

    The repeal date (30 June 2026) and the era boundary (FY 2018-19) are framing the brief gives the
    drafter. They are not data claims, and a drafter that cannot state them writes a worse report.
    """
    briefed = replace(
        section.plan, brief="Note that MGNREGA was repealed effective 30 June 2026, in FY 2026-27."
    )
    briefed_section = replace(section, plan=briefed)
    prose = "MGNREGA was repealed effective 30 June 2026 (FY 2026-27). It made 1,000,000."
    assert verify.verify(briefed_section, prose, tools).ok


def test_an_invented_number_still_blocks_even_with_a_brief_and_refusals(
    section: RetrievedSection, tools: DirectTools
) -> None:
    """The three allowances are exhaustive: anything else is still an invention."""
    report = verify.verify(section, "The state generated 1,400,000 person-days.", tools)
    assert not report.ok
    assert "1,400,000" in report.render()
