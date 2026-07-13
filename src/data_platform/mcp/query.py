"""The constrained filter query API (Stage 7 decision #4).

Callers pass structured parameters (table, metrics, states/districts, financial-year range); this
module validates them, resolves geography (LGD code or current LGD name), and builds parameterized
SQL with bound values — no raw SQL is ever accepted. Every result row carries its ``fact_id`` so
lineage is one ``get_lineage`` hop away, and the result is wrapped in an envelope stating the table,
the filters applied, and the row count. Requests the sealed record cannot honestly answer return a
structured :class:`~data_platform.mcp.refusals.Refusal`, never an empty result or an exception.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from data_platform.mcp import refusals, schema
from data_platform.mcp.loader import Dataset
from data_platform.mcp.refusals import Refusal

# Config-carried row cap (CLAUDE.md: thresholds are config, not inline magic numbers). Above it the
# query refuses with "narrow your filters" rather than returning an unbounded result. Sized so an
# honest analytical slice (e.g. a full single-metric district column, ~6.3k rows) succeeds; it
# guards against full-table dumps.
DEFAULT_ROW_CAP: Final = 10000


def query(
    ds: Dataset,
    table: str,
    *,
    metrics: Sequence[str] | None = None,
    states: Sequence[str] | None = None,
    districts: Sequence[str] | None = None,
    fy_from: str | None = None,
    fy_to: str | None = None,
    month: str | None = None,
    row_cap: int = DEFAULT_ROW_CAP,
) -> dict[str, object] | Refusal:
    """Run a constrained filter query; return a result envelope or a structured refusal."""
    if table not in schema.DATA_TABLES:
        if table in schema.TABLES:  # a known table (lineage) that this API does not serve
            return refusals.lineage_not_queryable(schema.DATA_TABLES)
        return refusals.unknown_table(table, schema.DATA_TABLES)
    tdef = schema.TABLES[table]

    # Sub-annual requests: the series is annual-only, so a monthly request is truthfully refused.
    if month is not None:
        return refusals.monthly_wage()

    period = _check_period(table, fy_from, fy_to)
    if period is not None:
        return period

    resolved_metrics = _resolve_metrics(tdef, metrics)
    if isinstance(resolved_metrics, Refusal):
        return resolved_metrics

    state_codes = _resolve_states(ds, tdef, states)
    if isinstance(state_codes, Refusal):
        return state_codes

    district_codes = _resolve_districts(ds, tdef, districts)
    if isinstance(district_codes, Refusal):
        return district_codes

    where, params = _build_where(resolved_metrics, state_codes, district_codes, fy_from, fy_to)
    count = _count(ds, table, where, params)
    if count > row_cap:
        return refusals.row_cap_exceeded(count, row_cap)

    rows = _fetch(ds, tdef, where, params)
    return {
        "table": table,
        "filters": {
            "metrics": list(resolved_metrics),
            "states": None if state_codes is None else list(state_codes),
            "districts": None if district_codes is None else list(district_codes),
            "fy_from": fy_from,
            "fy_to": fy_to,
        },
        "row_count": len(rows),
        "rows": rows,
    }


_FLOOR_REFUSAL = {
    "state_annual_series": refusals.state_series_floor,
    "national_annual_series": refusals.national_series_floor,
    "district_flagship": refusals.district_series_floor,
}


def _check_period(table: str, fy_from: str | None, fy_to: str | None) -> Refusal | None:
    """Refuse a window wholly outside coverage: after the ceiling, or below the table's floor.

    A coverage floor is a structural boundary of the record, so a window entirely below it refuses;
    the boundary year itself (fy_to == floor) is in scope and succeeds. A straddling window returns
    the in-coverage rows. An empty result is reserved for valid-scope filters matching zero rows.
    """
    if fy_from is not None and fy_from > schema.FISCAL_CEILING:
        return refusals.record_sealed(fy_from)
    floor = schema.FISCAL_FLOOR[table]
    if fy_to is not None and fy_to < floor:
        return _FLOOR_REFUSAL[table](floor)
    return None


def _resolve_metrics(tdef: schema.TableDef, metrics: Sequence[str] | None) -> list[str] | Refusal:
    if metrics is None:
        return list(tdef.metrics)
    valid = set(tdef.metrics)
    for metric in metrics:
        if metric in valid:
            continue
        pointer = _table_for_metric(metric)
        if pointer is not None and pointer != tdef.name:
            return refusals.unknown_metric(metric, tdef.metrics, pointer=pointer)
        return refusals.unknown_metric(metric, tdef.metrics)
    return list(metrics)


def _table_for_metric(metric: str) -> str | None:
    """A data table that serves ``metric`` (for the 'wrong grain' pointer), or None if unknown."""
    for name in schema.DATA_TABLES:
        if metric in schema.TABLES[name].metrics:
            return name
    return None


def _resolve_states(
    ds: Dataset, tdef: schema.TableDef, states: Sequence[str] | None
) -> list[str] | None | Refusal:
    if states is None:
        return None
    if "state_lgd_code" not in tdef.columns:
        return refusals.unknown_geography(
            f"{tdef.name} has no geography; drop the 'states' filter."
        )
    code_to_name = _distinct_pairs(ds, tdef.name, "state_lgd_code", "state_name")
    codes = set(code_to_name)
    by_name = {name.casefold(): code for code, name in code_to_name.items()}
    resolved: list[str] = []
    for token in states:
        key = token.strip()
        if key in codes:
            resolved.append(key)
        elif key.casefold() in by_name:
            resolved.append(by_name[key.casefold()])
        else:
            return refusals.unknown_geography(
                f"Unknown state {token!r} (give an LGD code or current LGD name).",
                options=tuple(sorted(code_to_name.values())),
            )
    return _dedupe(resolved)


def _resolve_districts(
    ds: Dataset, tdef: schema.TableDef, districts: Sequence[str] | None
) -> list[str] | None | Refusal:
    if districts is None:
        return None
    if "district_lgd_code" not in tdef.columns:
        return refusals.unknown_geography(
            f"{tdef.name} has no district grain; use district_flagship for district filters.",
            pointer="district_flagship",
        )
    code_to_name = _distinct_pairs(ds, tdef.name, "district_lgd_code", "district_name")
    codes = set(code_to_name)
    by_name: dict[str, list[str]] = {}
    for code, name in code_to_name.items():
        by_name.setdefault(name.casefold(), []).append(code)
    resolved: list[str] = []
    for token in districts:
        key = token.strip()
        if key in codes:
            resolved.append(key)
        elif key.casefold() in by_name:
            resolved.extend(by_name[key.casefold()])
        else:
            return refusals.unknown_geography(
                f"Unknown district {token!r} (give an LGD code or current LGD name).",
                pointer="get_schema",
            )
    return _dedupe(resolved)


def _build_where(
    metrics: Sequence[str],
    state_codes: Sequence[str] | None,
    district_codes: Sequence[str] | None,
    fy_from: str | None,
    fy_to: str | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    clauses.append(f"metric IN ({_placeholders(metrics)})")
    params.extend(metrics)
    if state_codes is not None:
        clauses.append(f"state_lgd_code IN ({_placeholders(state_codes)})")
        params.extend(state_codes)
    if district_codes is not None:
        clauses.append(f"district_lgd_code IN ({_placeholders(district_codes)})")
        params.extend(district_codes)
    if fy_from is not None:
        clauses.append("financial_year >= ?")
        params.append(fy_from)
    if fy_to is not None:
        clauses.append("financial_year <= ?")
        params.append(fy_to)
    return " AND ".join(clauses), params


def _count(ds: Dataset, table: str, where: str, params: Sequence[object]) -> int:
    row = ds.con.execute(f"SELECT count(*) FROM {table} WHERE {where}", list(params)).fetchone()
    assert row is not None
    return int(row[0])


def _fetch(
    ds: Dataset, tdef: schema.TableDef, where: str, params: Sequence[object]
) -> list[dict[str, object]]:
    columns = ", ".join(f'"{c}"' for c in tdef.columns)
    order = ", ".join(f'"{c}"' for c in tdef.columns)
    result = ds.con.execute(
        f"SELECT {columns} FROM {tdef.name} WHERE {where} ORDER BY {order}", list(params)
    ).fetchall()
    return [dict(zip(tdef.columns, row, strict=True)) for row in result]


def _distinct_pairs(ds: Dataset, table: str, code_col: str, name_col: str) -> dict[str, str]:
    result = ds.con.execute(f"SELECT DISTINCT {code_col}, {name_col} FROM {table}").fetchall()
    return {str(code): str(name) for code, name in result}


def _placeholders(values: Sequence[object]) -> str:
    return ", ".join("?" for _ in values)


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))
