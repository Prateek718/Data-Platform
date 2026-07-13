"""Unit tests for list_datasets + get_schema (Stage 7 step 2)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from data_platform.export.records import (
    DISTRICT_COLUMNS,
    NATIONAL_COLUMNS,
    STATE_COLUMNS,
)
from data_platform.export.write import _FLOAT_COLUMNS, _INT_COLUMNS
from data_platform.harmonize import config as hconfig
from data_platform.mcp import catalog, loader, refusals, schema
from tests.mcp.conftest import SyntheticDist


def _load(sd: SyntheticDist) -> loader.Dataset:
    return loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path)


def _catalog(sd: SyntheticDist) -> dict[str, dict[str, Any]]:
    return {cast(str, row["table"]): row for row in catalog.list_datasets(_load(sd))}


def _schema(table: str) -> dict[str, Any]:
    result = catalog.get_schema(table)
    assert isinstance(result, dict)
    return cast(dict[str, Any], result)


def test_list_datasets_lists_four_tables_with_counts(synthetic_dist: SyntheticDist) -> None:
    by = _catalog(synthetic_dist)
    assert set(by) == {
        "state_annual_series",
        "national_annual_series",
        "district_flagship",
        "lineage",
    }
    for table, count in synthetic_dist.counts.items():
        assert by[table]["row_count"] == count
        assert by[table]["join_key"] == "fact_id"


def test_list_datasets_grains(synthetic_dist: SyntheticDist) -> None:
    by = _catalog(synthetic_dist)
    assert by["state_annual_series"]["grain"] == "state-annual"
    assert by["national_annual_series"]["grain"] == "national-annual"
    assert by["district_flagship"]["grain"] == "district-annual"


def test_list_datasets_fy_range_computed_from_data(synthetic_dist: SyntheticDist) -> None:
    by = _catalog(synthetic_dist)
    assert (by["state_annual_series"]["fy_from"], by["state_annual_series"]["fy_to"]) == (
        "2015-16",
        "2018-19",
    )
    assert (by["national_annual_series"]["fy_from"], by["national_annual_series"]["fy_to"]) == (
        "2006-07",
        "2012-13",
    )
    # lineage spans the union of the three data tables
    assert (by["lineage"]["fy_from"], by["lineage"]["fy_to"]) == ("2006-07", "2018-19")


def test_list_datasets_metric_counts(synthetic_dist: SyntheticDist) -> None:
    by = _catalog(synthetic_dist)
    assert len(by["state_annual_series"]["metrics"]) == 8
    assert len(by["national_annual_series"]["metrics"]) == 8
    assert len(by["district_flagship"]["metrics"]) == 9
    assert "avg_wage_rate_per_day" in by["district_flagship"]["metrics"]
    assert "avg_wage_rate_per_day" not in by["state_annual_series"]["metrics"]


def test_get_schema_state_columns_and_grain() -> None:
    result = _schema("state_annual_series")
    assert result["grain"] == "state-annual"
    assert result["join_key"] == "fact_id"
    assert [c["name"] for c in result["columns"]] == list(STATE_COLUMNS)


def test_get_schema_national_and_district_columns() -> None:
    assert [c["name"] for c in _schema("national_annual_series")["columns"]] == list(
        NATIONAL_COLUMNS
    )
    assert [c["name"] for c in _schema("district_flagship")["columns"]] == list(DISTRICT_COLUMNS)


def test_get_schema_metric_units_and_unit_class() -> None:
    metrics = {m["name"]: m for m in _schema("district_flagship")["metrics"]}
    assert metrics["households_employed"]["unit"] == "count"
    assert metrics["households_employed"]["unit_class"] == schema.UnitClass.COUNT.value
    assert metrics["wages_expenditure"]["unit"] == "INR lakh"
    assert metrics["wages_expenditure"]["unit_class"] == schema.UnitClass.MONEY.value
    assert metrics["persondays_generated"]["unit"] == "person-days"
    assert metrics["persondays_generated"]["unit_class"] == schema.UnitClass.PERSON_DAYS.value
    assert metrics["avg_wage_rate_per_day"]["unit"] == "INR"
    assert metrics["avg_wage_rate_per_day"]["unit_class"] == schema.UnitClass.RATE.value


def test_get_schema_null_semantics_present() -> None:
    null_sem = _schema("state_annual_series")["null_semantics"]
    assert "never" in null_sem["principle"].lower()
    assert "partial-period-only" in null_sem["null_reasons"]
    assert "unadjudicated" in null_sem["null_reasons"]


def test_get_schema_unknown_table_refuses() -> None:
    result = catalog.get_schema("bogus_table")
    assert isinstance(result, refusals.Refusal)
    assert result.code == refusals.UNKNOWN_TABLE
    assert result.options is not None
    assert "state_annual_series" in result.options


def test_schema_metric_set_matches_canonical_config() -> None:
    # Drift guard: schema metrics == the 9 canonical metrics defined in harmonize config.
    assert set(schema.METRICS) == set(hconfig.CANONICAL_UNIT)


def test_schema_column_types_match_export_writer() -> None:
    # Drift guard: number/integer columns agree with the export Parquet writer's typing.
    for col in STATE_COLUMNS + DISTRICT_COLUMNS:
        expected = (
            "number" if col in _FLOAT_COLUMNS else "integer" if col in _INT_COLUMNS else "string"
        )
        assert schema.column_type(col) == expected


@pytest.mark.golden
def test_golden_schema_metrics_match_real_data() -> None:
    ds = loader.load_dataset()
    state_metrics = {
        r[0] for r in ds.con.execute("SELECT DISTINCT metric FROM state_annual_series").fetchall()
    }
    district_metrics = {
        r[0] for r in ds.con.execute("SELECT DISTINCT metric FROM district_flagship").fetchall()
    }
    assert state_metrics == set(schema.TABLES["state_annual_series"].metrics)
    assert district_metrics == set(schema.TABLES["district_flagship"].metrics)
