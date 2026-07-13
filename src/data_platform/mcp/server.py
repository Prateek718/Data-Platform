"""The MCP protocol adapter — a thin layer over the pure core.

Registers the five read-only tools on a FastMCP stdio server; each tool does nothing but call the
corresponding core function and hand back its plain dict (a :class:`Refusal` is serialized via
``to_dict``). All logic — loading, schema, query grammar, refusals, lineage — lives in the core and
is tested there; this module only wires it to the protocol.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from data_platform.mcp import catalog, lineage, refresh
from data_platform.mcp import query as query_mod
from data_platform.mcp.loader import Dataset
from data_platform.mcp.refusals import Refusal

SERVER_NAME = "mgnrega-canonical-series"


def _as_dict(result: dict[str, object] | Refusal) -> dict[str, object]:
    return result.to_dict() if isinstance(result, Refusal) else result


def build_server(ds: Dataset) -> FastMCP:
    """Build the FastMCP server exposing the five tools over an already-loaded dataset."""
    server = FastMCP(SERVER_NAME)

    @server.tool(
        description=(
            "List the three data tables and the lineage table, each with row count, financial-year "
            "coverage window, grain, and metric list."
        )
    )
    def list_datasets() -> dict[str, Any]:
        return {"datasets": catalog.list_datasets(ds)}

    @server.tool(
        description=(
            "Return the full schema for a table: columns and types, per-metric unit and "
            "unit-class, grain, join key (fact_id), and null semantics."
        )
    )
    def get_schema(table: str) -> dict[str, Any]:
        return _as_dict(catalog.get_schema(table))

    @server.tool(
        description=(
            "Query a data table with structured filters: metrics, states/districts (by LGD code or "
            "current LGD name), and a financial-year range. Returns rows carrying fact_id in a "
            "result envelope, or a structured refusal. No raw SQL is accepted."
        )
    )
    def query(
        table: str,
        metrics: list[str] | None = None,
        states: list[str] | None = None,
        districts: list[str] | None = None,
        fy_from: str | None = None,
        fy_to: str | None = None,
        month: str | None = None,
    ) -> dict[str, Any]:
        return _as_dict(
            query_mod.query(
                ds,
                table,
                metrics=metrics,
                states=states,
                districts=districts,
                fy_from=fy_from,
                fy_to=fy_to,
                month=month,
            )
        )

    @server.tool(
        description=(
            "Return full provenance for one or more fact_ids: each source with its resource id and "
            "as-of date, reconciliation status, rejected value where one exists, materiality "
            "reading, and the null reason for null cells."
        )
    )
    def get_lineage(fact_ids: str | list[str]) -> dict[str, Any]:
        return lineage.get_lineage(ds, fact_ids)

    @server.tool(
        description=(
            "Report that the record is sealed (MGNREGA repealed 30 June 2026) and cannot be "
            "refreshed, with the DOI-versioned citation pointer."
        )
    )
    def request_refresh() -> dict[str, Any]:
        return refresh.request_refresh()

    return server
