"""Backend parity: the in-process core and the real MCP server return identical payloads.

DirectTools is the fast, hermetic backend (used by unit tests and by the report verifier);
McpStdioTools is the honest demo path — a real MCP client speaking the protocol to the actual
server, spawned as a subprocess over stdio. The analyst must not be able to tell them apart, or
"verified against the served data" would mean something different from what the demo shows.

Golden: needs the real ``dist/v1.0`` (the server's checksum gate loads it at startup), so these
are skipped when it is absent. No network — stdio is pipes to a local subprocess.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from data_platform.analyst.tools import AnalystTools, DirectTools, McpStdioTools, Payload
from data_platform.mcp import loader

pytestmark = pytest.mark.golden

Call = Callable[[AnalystTools], Payload]

# A representative matrix: the catalog surface, real data reads at all three grains, a derived-
# figure read, and every refusal shape the analyst can provoke — post-repeal period, monthly wage
# rate, unknown geography, malformed financial year (R7-SRV-01), unknown table.
CALLS: dict[str, Call] = {
    "list_datasets": lambda t: t.list_datasets(),
    "get_schema_district": lambda t: t.get_schema("district_flagship"),
    "get_schema_lineage": lambda t: t.get_schema("lineage"),
    "national_persondays_first_years": lambda t: t.query(
        "national_annual_series",
        metrics=["persondays_generated"],
        fy_from="2006-07",
        fy_to="2008-09",
    ),
    "state_goa_expenditure": lambda t: t.query(
        "state_annual_series",
        metrics=["total_expenditure"],
        states=["Goa"],
        fy_from="2022-23",
        fy_to="2022-23",
    ),
    "district_goa_wage_rate": lambda t: t.query(
        "district_flagship",
        metrics=["avg_wage_rate_per_day"],
        states=["Goa"],
        fy_from="2022-23",
        fy_to="2022-23",
    ),
    "lineage_of_a_national_fact": lambda t: t.get_lineage(_first_fact_id(t)),
    "request_refresh": lambda t: t.request_refresh(),
    # Refusals.
    "refusal_post_repeal": lambda t: t.query("state_annual_series", fy_from="2027-28"),
    "refusal_monthly_wage": lambda t: t.query("district_flagship", month="April"),
    "refusal_unknown_geography": lambda t: t.query("state_annual_series", states=["Atlantis"]),
    "refusal_malformed_fy": lambda t: t.query("state_annual_series", fy_from="2019"),
    "refusal_unknown_table": lambda t: t.query("bogus_table"),
    "refusal_district_floor": lambda t: t.query("district_flagship", fy_to="2010-11"),
}


def _first_fact_id(tools: AnalystTools) -> str:
    """The fact_id of the earliest national person-days fact — a stable, real lineage target."""
    result = tools.query(
        "national_annual_series",
        metrics=["persondays_generated"],
        fy_from="2006-07",
        fy_to="2006-07",
    )
    rows = result["rows"]
    assert isinstance(rows, list)
    fact_id = rows[0]["fact_id"]
    assert isinstance(fact_id, str)
    return fact_id


@pytest.fixture(scope="module")
def direct_tools() -> Iterator[DirectTools]:
    dataset = loader.load_dataset()
    yield DirectTools(dataset)
    dataset.close()


@pytest.fixture(scope="module")
def stdio_tools() -> Iterator[McpStdioTools]:
    with McpStdioTools() as tools:
        yield tools


@pytest.mark.parametrize("label", sorted(CALLS))
def test_backends_return_identical_payloads(
    label: str, direct_tools: DirectTools, stdio_tools: McpStdioTools
) -> None:
    call = CALLS[label]
    assert call(direct_tools) == call(stdio_tools)


def test_stdio_serves_the_five_tools(stdio_tools: McpStdioTools) -> None:
    assert stdio_tools.tool_names() == (
        "list_datasets",
        "get_schema",
        "query",
        "get_lineage",
        "request_refresh",
    )
