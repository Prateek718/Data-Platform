"""Tests for the MCP protocol adapter (Stage 7 step 6).

The adapter is thin, so these are few: they confirm the five tools register and that each
round-trips its core result (including refusals) through the protocol. All substantive behaviour
is covered by the core tests.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from data_platform.mcp import loader
from data_platform.mcp.server import build_server
from tests.mcp.conftest import SyntheticDist


def _server(sd: SyntheticDist) -> FastMCP:
    ds = loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path)
    return build_server(ds)


def _call(server: FastMCP, name: str, arguments: dict[str, Any]) -> Any:
    result = asyncio.run(server.call_tool(name, arguments))
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list):
        block = result[0]
        assert isinstance(block, TextContent)
        return json.loads(block.text)
    return result


def test_registers_the_five_tools(synthetic_dist: SyntheticDist) -> None:
    server = _server(synthetic_dist)
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {
        "list_datasets",
        "get_schema",
        "query",
        "get_lineage",
        "request_refresh",
    }


def test_list_datasets_tool(synthetic_dist: SyntheticDist) -> None:
    result = _call(_server(synthetic_dist), "list_datasets", {})
    assert {row["table"] for row in result["datasets"]} == {
        "state_annual_series",
        "national_annual_series",
        "district_flagship",
        "lineage",
    }


def test_query_tool_roundtrips(synthetic_dist: SyntheticDist) -> None:
    result = _call(
        _server(synthetic_dist),
        "query",
        {"table": "state_annual_series", "metrics": ["households_employed"]},
    )
    assert result["row_count"] == 1
    assert result["rows"][0]["fact_id"] == "st03"


def test_query_tool_serializes_refusal(synthetic_dist: SyntheticDist) -> None:
    result = _call(_server(synthetic_dist), "query", {"table": "bogus"})
    assert result["refused"] is True
    assert result["code"] == "unknown_table"


def test_get_schema_tool(synthetic_dist: SyntheticDist) -> None:
    result = _call(_server(synthetic_dist), "get_schema", {"table": "district_flagship"})
    metric_names = {m["name"] for m in result["metrics"]}
    assert "avg_wage_rate_per_day" in metric_names


def test_get_lineage_tool(synthetic_dist: SyntheticDist) -> None:
    result = _call(_server(synthetic_dist), "get_lineage", {"fact_ids": "st03"})
    rec = result["records"][0]
    assert rec["fact_id"] == "st03"
    assert rec["rejected"][0]["value"] == "4025000"


def test_request_refresh_tool(synthetic_dist: SyntheticDist) -> None:
    result = _call(_server(synthetic_dist), "request_refresh", {})
    assert result["refresh_available"] is False
