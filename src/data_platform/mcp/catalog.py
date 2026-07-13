"""list_datasets + get_schema — the catalog surface over the loaded dataset.

Row counts and FY coverage windows are read from the loaded data (honest to what is actually
served); grain, columns, metrics, and null semantics come from the static single-source
definitions in :mod:`schema`.
"""

from __future__ import annotations

from data_platform.mcp import schema
from data_platform.mcp.loader import Dataset
from data_platform.mcp.refusals import Refusal, unknown_table


def _fy_range(ds: Dataset, table: schema.TableDef) -> tuple[str | None, str | None]:
    if table.has_financial_year:
        row = ds.con.execute(
            f"SELECT min(financial_year), max(financial_year) FROM {table.name}"
        ).fetchone()
        assert row is not None
        return row[0], row[1]
    # lineage has no FY column: it spans the union of the three data tables' facts.
    row = ds.con.execute(
        "SELECT min(fy_min), max(fy_max) FROM ("
        + " UNION ALL ".join(
            f"SELECT min(financial_year) AS fy_min, max(financial_year) AS fy_max FROM {name}"
            for name in schema.DATA_TABLES
        )
        + ")"
    ).fetchone()
    assert row is not None
    return row[0], row[1]


def list_datasets(ds: Dataset) -> list[dict[str, object]]:
    """The three data tables + lineage, each with row count, FY window, grain, and metric list."""
    out: list[dict[str, object]] = []
    for name, table in schema.TABLES.items():
        fy_from, fy_to = _fy_range(ds, table)
        out.append(
            {
                "table": name,
                "grain": table.grain,
                "row_count": ds.row_counts[name],
                "fy_from": fy_from,
                "fy_to": fy_to,
                "metrics": list(table.metrics),
                "join_key": schema.JOIN_KEY,
            }
        )
    return out


def get_schema(table: str) -> dict[str, object] | Refusal:
    """Full schema for one table: columns+types, per-metric unit/unit-class, grain, null semantics.

    An unknown table name returns a structured refusal listing the valid tables.
    """
    tdef = schema.TABLES.get(table)
    if tdef is None:
        return unknown_table(table, tuple(schema.TABLES))
    return {
        "table": tdef.name,
        "grain": tdef.grain,
        "join_key": schema.JOIN_KEY,
        "columns": [schema.column_def(c) for c in tdef.columns],
        "metrics": [schema.METRICS[m].to_dict() for m in tdef.metrics],
        "null_semantics": schema.NULL_SEMANTICS,
    }
