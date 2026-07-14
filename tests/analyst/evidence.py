"""A small, real retrieved section over the synthetic dist — shared by the verifier/graph tests.

Built through the actual retriever against the actual query core (the synthetic fixture dist), so
these tests exercise the real fetch → lineage → derive path rather than hand-written stand-ins.
"""

from __future__ import annotations

from data_platform.analyst import retrieve
from data_platform.analyst.models import QuerySpec, RetrievedSection, SectionPlan
from data_platform.analyst.tools import AnalystTools

PLAN = SectionPlan(
    key="test_section",
    title="Jammu and Kashmir, FY 2018-19",
    brief="State person-days, the Anantnag district share of them, and what the record refuses.",
)

STATE_PERSONDAYS = QuerySpec(
    table="state_annual_series",
    metric="persondays_generated",
    fy="2018-19",
    state="Jammu and Kashmir",
)
DISTRICT_PERSONDAYS = QuerySpec(
    table="district_flagship",
    metric="persondays_generated",
    fy="2018-19",
    state="Jammu and Kashmir",
    district="Anantnag",
)


def build_section(tools: AnalystTools) -> RetrievedSection:
    """State person-days (1,000,000), Anantnag's (300,000), and the derived 0.3 share."""
    state = retrieve.fetch_figure(
        tools,
        id="state_persondays",
        label="Jammu and Kashmir person-days, FY 2018-19",
        geography="Jammu and Kashmir",
        spec=STATE_PERSONDAYS,
    )
    district = retrieve.fetch_figure(
        tools,
        id="anantnag_persondays",
        label="Anantnag person-days, FY 2018-19",
        geography="Anantnag, Jammu and Kashmir",
        spec=DISTRICT_PERSONDAYS,
    )
    share = retrieve.derived(
        id="anantnag_share",
        label="Anantnag's share of state person-days",
        operation="ratio",
        inputs=[district, state],
        unit="ratio",
    )
    monthly = retrieve.refusal(
        tools,
        id="monthly_refusal",
        label="asking for a monthly figure",
        call='query(table="district_flagship", month="2022-04")',
        table="district_flagship",
        month="2022-04",
    )
    return RetrievedSection(
        plan=PLAN, figures=(state, district), derivations=(share,), refusals=(monthly,)
    )
