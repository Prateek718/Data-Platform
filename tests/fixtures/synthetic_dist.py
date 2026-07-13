"""Builder for a tiny synthetic ``dist/v1.0`` used by the MCP unit tests.

A few rows per table, written with the REAL export serializers (:mod:`data_platform.export`)
so the fixture's column schema and Parquet types cannot drift from the shipped dataset. Every
loader / checksum-gate / query / refusal / null-semantics test runs against this fixture instead
of the gitignored real ``dist/v1.0`` — so the whole suite runs in CI.

The rows are hand-chosen to exercise the semantics the tests assert: a corroborated fact, a
flagged cross-publisher disagreement with a rejected peer value, an ``unadjudicated`` null and a
``partial-period-only`` null (the two null reasons), and a district ``avg_wage_rate_per_day``.
``build_synthetic_dist`` also writes a real ``SHA256SUMS.txt`` over the seven files.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from data_platform.export.records import (
    DISTRICT_COLUMNS,
    NATIONAL_COLUMNS,
    STATE_COLUMNS,
    csv_bytes,
    jsonl_bytes,
)
from data_platform.export.write import parquet_bytes

_STATE_SORT = ("state_lgd_code", "financial_year", "metric")
_NATIONAL_SORT = ("financial_year", "metric")
_DISTRICT_SORT = ("state_lgd_code", "district_lgd_code", "financial_year", "metric")

# --- rows (a few per table) -------------------------------------------------------------------

STATE_ROWS: tuple[dict[str, object], ...] = (
    {
        "state_lgd_code": "01",
        "state_name": "Jammu and Kashmir",
        "financial_year": "2018-19",
        "metric": "persondays_generated",
        "value": Decimal("1000000"),
        "unit": "person-days",
        "era_basis": "flagship-rollup",
        "confidence": "cross-publisher",
        "sources_seen_count": 2,
        "contributing_resource_ids": "r1;r2",
        "fact_id": "st01",
    },
    {
        "state_lgd_code": "01",
        "state_name": "Jammu and Kashmir",
        "financial_year": "2018-19",
        "metric": "total_expenditure",
        "value": None,  # unadjudicated structural-gap null
        "unit": "INR lakh",
        "era_basis": "flagship-rollup",
        "confidence": "unadjudicated",
        "sources_seen_count": 1,
        "contributing_resource_ids": "r1",
        "fact_id": "st02",
    },
    {
        "state_lgd_code": "27",
        "state_name": "Maharashtra",
        "financial_year": "2015-16",
        "metric": "households_employed",
        "value": Decimal("4200000"),
        "unit": "count",
        "era_basis": "historical",
        "confidence": "flagged-disagreement",
        "sources_seen_count": 2,
        "contributing_resource_ids": "r3;r4",
        "fact_id": "st03",
    },
    {
        "state_lgd_code": "32",
        "state_name": "Kerala",
        "financial_year": "2017-18",
        "metric": "persondays_generated",
        "value": None,  # partial-period-only null
        "unit": "person-days",
        "era_basis": "historical",
        "confidence": "partial-period-only",
        "sources_seen_count": 1,
        "contributing_resource_ids": "r5",
        "fact_id": "st04",
    },
)

NATIONAL_ROWS: tuple[dict[str, object], ...] = (
    {
        "financial_year": "2006-07",
        "metric": "households_employed",
        "value": Decimal("21000000"),
        "unit": "count",
        "era_basis": "historical",
        "confidence": "single-source",
        "sources_seen_count": 1,
        "contributing_resource_ids": "r6",
        "fact_id": "nt01",
    },
    {
        "financial_year": "2012-13",
        "metric": "persondays_generated",
        "value": None,  # national single-publisher divergence null
        "unit": "person-days",
        "era_basis": "historical",
        "confidence": "single-publisher divergence",
        "sources_seen_count": 2,
        "contributing_resource_ids": "r6;r7",
        "fact_id": "nt02",
    },
)

DISTRICT_ROWS: tuple[dict[str, object], ...] = (
    {
        "state_lgd_code": "01",
        "state_name": "Jammu and Kashmir",
        "district_lgd_code": "0001",
        "district_name": "Anantnag",
        "financial_year": "2018-19",
        "metric": "persondays_generated",
        "value": Decimal("300000"),
        "unit": "person-days",
        "grain": "district-annual",
        "confidence": "single-source",
        "sources_seen_count": 1,
        "contributing_resource_ids": "r1",
        "fact_id": "ds01",
    },
    {
        "state_lgd_code": "01",
        "state_name": "Jammu and Kashmir",
        "district_lgd_code": "0001",
        "district_name": "Anantnag",
        "financial_year": "2018-19",
        "metric": "avg_wage_rate_per_day",
        "value": Decimal("103.392742752098"),
        "unit": "INR",
        "grain": "district-annual",
        "confidence": "single-source",
        "sources_seen_count": 1,
        "contributing_resource_ids": "r1",
        "fact_id": "ds02",
    },
)


def _source_ref(
    source_id: str,
    resource_id: str,
    value: str | None,
    *,
    as_of: str | None = "2024-01-01",
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "resource_id": resource_id,
        "value": value,
        "original_unit": "raw",
        "source_as_of": as_of,
        "authority_rank": 1,
        "rounding_epsilon": "0",
        "edition_span_end": None,
        "is_edition_terminal": True,
        "aggregate_coverage": None,
        "definition_discrepancy": None,
    }


def _lineage(
    fact_id: str,
    *,
    metric: str,
    value: str | None,
    confidence: str,
    sources_seen: Sequence[Mapping[str, object]],
    disagreement: Mapping[str, object] | None = None,
    resolution_rule_id: str | None = None,
) -> dict[str, object]:
    return {
        "fact_id": fact_id,
        "key": {
            "scheme": "mgnrega",
            "geo_level": "state",
            "state_code": None,
            "district_code": None,
            "fin_year": "2018-19",
            "month": None,
            "metric": metric,
        },
        "value": value,
        "unit": "raw",
        "basis": "flagship-rollup",
        "confidence": confidence,
        "resolution_rule_id": resolution_rule_id,
        "adjudicated": disagreement is not None,
        "quarantined": False,
        "quarantine_reason": None,
        "sources_seen": list(sources_seen),
        "disagreement": dict(disagreement) if disagreement is not None else None,
        "coverage_absent": [],
        "scale_quarantined": [],
        "edition_superseded": [],
        "partial_period": [],
    }


LINEAGE_RECORDS: tuple[dict[str, object], ...] = (
    _lineage(
        "st01",
        metric="persondays_generated",
        value="1000000",
        confidence="cross-publisher",
        sources_seen=[
            _source_ref("mospi", "r1", "1000000"),
            _source_ref("rajya_sabha", "r2", "1000000"),
        ],
    ),
    _lineage(
        "st02",
        metric="total_expenditure",
        value=None,
        confidence="unadjudicated",
        sources_seen=[_source_ref("flagship", "r1", "999999")],
        resolution_rule_id="R4-REC-05",
    ),
    _lineage(
        "st03",
        metric="households_employed",
        value="4200000",
        confidence="flagged-disagreement",
        sources_seen=[
            _source_ref("mospi", "r3", "4200000"),
            _source_ref("rajya_sabha", "r4", "4025000"),
        ],
        disagreement={
            "pct": "4.17",
            "rejected_sources": ["rajya_sabha"],
            "rule_id": "R4-REC-04",
            "material": True,
        },
        resolution_rule_id="R4-REC-04",
    ),
    _lineage(
        "st04",
        metric="persondays_generated",
        value=None,
        confidence="partial-period-only",
        sources_seen=[_source_ref("mospi", "r5", "500000")],
        resolution_rule_id="R4-REC-11",
    ),
    _lineage(
        "nt01",
        metric="households_employed",
        value="21000000",
        confidence="single-source",
        sources_seen=[_source_ref("mospi", "r6", "21000000")],
    ),
    _lineage(
        "nt02",
        metric="persondays_generated",
        value=None,
        confidence="single-publisher divergence",
        sources_seen=[
            _source_ref("mospi", "r6", "1800000000"),
            _source_ref("mospi", "r7", "2100000000"),
        ],
        resolution_rule_id="R4-REC-09",
    ),
    _lineage(
        "ds01",
        metric="persondays_generated",
        value="300000",
        confidence="single-source",
        sources_seen=[_source_ref("flagship", "r1", "300000")],
    ),
    _lineage(
        "ds02",
        metric="avg_wage_rate_per_day",
        value="103.392742752098",
        confidence="single-source",
        sources_seen=[_source_ref("flagship", "r1", "103.392742752098")],
    ),
)


def _write_sha256sums(out_dir: Path, names: Sequence[str]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_synthetic_dist(out_dir: Path) -> dict[str, int]:
    """Materialize the synthetic ``dist/v1.0`` (7 files + SHA256SUMS.txt); return row counts."""
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = (
        ("state_annual_series", STATE_ROWS, STATE_COLUMNS, _STATE_SORT),
        ("national_annual_series", NATIONAL_ROWS, NATIONAL_COLUMNS, _NATIONAL_SORT),
        ("district_flagship", DISTRICT_ROWS, DISTRICT_COLUMNS, _DISTRICT_SORT),
    )
    for name, rows, columns, sort_by in tables:
        (out_dir / f"{name}.csv").write_bytes(csv_bytes(rows, columns=columns, sort_by=sort_by))
        (out_dir / f"{name}.parquet").write_bytes(
            parquet_bytes(rows, columns=columns, sort_by=sort_by)
        )
    (out_dir / "lineage.jsonl").write_bytes(jsonl_bytes(LINEAGE_RECORDS, sort_by="fact_id"))

    _write_sha256sums(
        out_dir,
        [
            "state_annual_series.csv",
            "state_annual_series.parquet",
            "national_annual_series.csv",
            "national_annual_series.parquet",
            "district_flagship.csv",
            "district_flagship.parquet",
            "lineage.jsonl",
        ],
    )
    return {
        "state_annual_series": len(STATE_ROWS),
        "national_annual_series": len(NATIONAL_ROWS),
        "district_flagship": len(DISTRICT_ROWS),
        "lineage": len(LINEAGE_RECORDS),
    }
