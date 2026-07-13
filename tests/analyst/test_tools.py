"""Unit tests for the analyst tool layer — DirectTools against the synthetic dist.

DirectTools is the hermetic backend: it calls the MCP server's pure query core in-process, so it
runs in CI without the released artifacts. These tests pin the payload contract every backend owes
the analyst — the same dicts the MCP tools put on the wire, refusals included. Parity between the
two backends is asserted separately (test_contract.py, golden).
"""

from __future__ import annotations

from data_platform.analyst.tools import AnalystTools, DirectTools
from data_platform.mcp import loader
from tests.conftest import SyntheticDist


def _tools(sd: SyntheticDist) -> DirectTools:
    return DirectTools(loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path))


def _accepts(tools: AnalystTools) -> AnalystTools:
    """Static conformance: mypy --strict rejects a backend that does not satisfy the protocol."""
    return tools


def test_direct_tools_satisfies_the_protocol(synthetic_dist: SyntheticDist) -> None:
    assert _accepts(_tools(synthetic_dist)) is not None


def test_list_datasets(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).list_datasets()
    datasets = result["datasets"]
    assert isinstance(datasets, list)
    assert {row["table"] for row in datasets} == {
        "state_annual_series",
        "national_annual_series",
        "district_flagship",
        "lineage",
    }


def test_get_schema(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).get_schema("district_flagship")
    metrics = result["metrics"]
    assert isinstance(metrics, list)
    assert "avg_wage_rate_per_day" in {m["name"] for m in metrics}


def test_get_schema_refusal_is_a_payload(synthetic_dist: SyntheticDist) -> None:
    """A refusal reaches the analyst as the same dict the wire carries, never as an exception."""
    result = _tools(synthetic_dist).get_schema("bogus")
    assert result["refused"] is True
    assert result["code"] == "unknown_table"


def test_query_returns_rows_with_fact_ids(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).query("state_annual_series", metrics=["households_employed"])
    rows = result["rows"]
    assert isinstance(rows, list)
    assert result["row_count"] == 1
    assert rows[0]["fact_id"] == "st03"


def test_query_refusal_is_a_payload(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).query("state_annual_series", fy_from="2027-28")
    assert result["refused"] is True
    assert result["code"] == "record_sealed"


def test_query_malformed_financial_year_refuses(synthetic_dist: SyntheticDist) -> None:
    """R7-SRV-01: a malformed FY label is refused at the boundary, not compared lexically."""
    result = _tools(synthetic_dist).query("state_annual_series", fy_from="2019")
    assert result["refused"] is True
    assert result["code"] == "invalid_period"


def test_get_lineage(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).get_lineage("st03")
    records = result["records"]
    assert isinstance(records, list)
    assert records[0]["fact_id"] == "st03"
    assert records[0]["rejected"][0]["value"] == "4025000"


def test_request_refresh(synthetic_dist: SyntheticDist) -> None:
    result = _tools(synthetic_dist).request_refresh()
    assert result["refresh_available"] is False
