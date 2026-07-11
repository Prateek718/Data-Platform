"""Serialize the assembled series to the deliverable files (CSV + Parquet + lineage JSONL).

CSV and JSONL bytes come from the pure :mod:`records` serializers (byte-identical across runs).
Parquet is written with pyarrow, isolated here so it is the ONLY module importing it — the numeric
``value``/``sources_seen_count`` columns are typed (float64 / int64) for query-friendliness, every
other column is a nullable string. Import is lazy so CSV + JSONL still write when pyarrow is absent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from data_platform.export.build import ExportBundle
from data_platform.export.records import (
    DISTRICT_COLUMNS,
    NATIONAL_COLUMNS,
    STATE_COLUMNS,
    csv_bytes,
    district_row,
    jsonl_bytes,
    lineage_record,
    national_row,
    sort_rows,
    state_row,
)

# Numeric columns get real Parquet types; everything else is a nullable UTF-8 string.
_FLOAT_COLUMNS = frozenset({"value"})
_INT_COLUMNS = frozenset({"sources_seen_count"})

_STATE_SORT = ("state_lgd_code", "financial_year", "metric")
_NATIONAL_SORT = ("financial_year", "metric")
_DISTRICT_SORT = ("state_lgd_code", "district_lgd_code", "financial_year", "metric")


def parquet_bytes(
    rows: Sequence[Mapping[str, object]], *, columns: Sequence[str], sort_by: Sequence[str]
) -> bytes:
    """Serialize rows to Parquet bytes in the same deterministic order as the CSV."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    ordered = sort_rows(rows, sort_by)
    table_columns: dict[str, pa.Array] = {}
    for column in columns:
        values = [row.get(column) for row in ordered]
        if column in _FLOAT_COLUMNS:
            table_columns[column] = pa.array([_as_float(v) for v in values], type=pa.float64())
        elif column in _INT_COLUMNS:
            table_columns[column] = pa.array([_as_int(v) for v in values], type=pa.int64())
        else:
            table_columns[column] = pa.array(
                [None if v is None else _str(v) for v in values], type=pa.string()
            )
    sink = pa.BufferOutputStream()
    pq.write_table(pa.table(table_columns), sink, compression="zstd")  # type: ignore[no-untyped-call]
    result: bytes = sink.getvalue().to_pybytes()
    return result


def _str(value: object) -> str:
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    assert isinstance(value, Decimal | int | float)
    return float(value)


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    assert isinstance(value, int)
    return value


def _write_table(
    out_dir: Path,
    name: str,
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[str],
    sort_by: Sequence[str],
    *,
    parquet: bool,
) -> None:
    (out_dir / f"{name}.csv").write_bytes(csv_bytes(rows, columns=columns, sort_by=sort_by))
    if parquet:
        (out_dir / f"{name}.parquet").write_bytes(
            parquet_bytes(rows, columns=columns, sort_by=sort_by)
        )


def _pyarrow_available() -> bool:
    try:
        import pyarrow  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def write_all(out_dir: Path, bundle: ExportBundle) -> dict[str, int]:
    """Write all four deliverables under ``out_dir``; return per-file row counts.

    Parquet is written only when pyarrow is installed (CSV + lineage always are). The lineage JSONL
    holds one record per exported fact across all three tables, keyed by ``fact_id``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet = _pyarrow_available()
    resource_map = bundle.resource_map

    state_rows = [
        state_row(f, state_names=bundle.state_names, resource_map=resource_map)
        for f in bundle.state_facts
    ]
    _write_table(
        out_dir, "state_annual_series", state_rows, STATE_COLUMNS, _STATE_SORT, parquet=parquet
    )

    national_rows = [national_row(f, resource_map=resource_map) for f in bundle.national_facts]
    _write_table(
        out_dir,
        "national_annual_series",
        national_rows,
        NATIONAL_COLUMNS,
        _NATIONAL_SORT,
        parquet=parquet,
    )

    district_rows = [
        district_row(
            f,
            state_names=bundle.state_names,
            district_names=bundle.district_names,
            resource_map=resource_map,
        )
        for f in bundle.district_facts
    ]
    _write_table(
        out_dir,
        "district_flagship",
        district_rows,
        DISTRICT_COLUMNS,
        _DISTRICT_SORT,
        parquet=parquet,
    )

    all_facts = [*bundle.state_facts, *bundle.national_facts, *bundle.district_facts]
    lineage = [lineage_record(f, resource_map=resource_map) for f in all_facts]
    (out_dir / "lineage.jsonl").write_bytes(jsonl_bytes(lineage, sort_by="fact_id"))

    return {
        "state_annual_series": len(state_rows),
        "national_annual_series": len(national_rows),
        "district_flagship": len(district_rows),
        "lineage": len(lineage),
    }
