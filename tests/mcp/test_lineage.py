"""Unit tests for get_lineage (Stage 7 step 4)."""

from __future__ import annotations

from collections import Counter
from typing import Any, cast

import pytest

from data_platform.mcp import lineage, loader
from data_platform.mcp.query import query as run_query
from tests.mcp.conftest import SyntheticDist


def _load(sd: SyntheticDist) -> loader.Dataset:
    return loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path)


def _records(result: dict[str, object]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], result["records"])


def _one(ds: loader.Dataset, fact_id: str) -> dict[str, Any]:
    recs = _records(lineage.get_lineage(ds, fact_id))
    assert len(recs) == 1
    return recs[0]


def test_get_lineage_corroborated_fact(synthetic_dist: SyntheticDist) -> None:
    rec = _one(_load(synthetic_dist), "st01")
    assert rec["found"] is True
    assert rec["metric"] == "persondays_generated"
    assert rec["reconciliation_status"] == "corroborated"
    resource_ids = {s["resource_id"] for s in rec["sources"]}
    assert resource_ids == {"r1", "r2"}
    assert rec["materiality"] is None
    assert rec["null_reason"] is None


def test_get_lineage_sources_carry_resource_id_and_as_of(synthetic_dist: SyntheticDist) -> None:
    rec = _one(_load(synthetic_dist), "st01")
    for source in rec["sources"]:
        assert source["resource_id"]
        assert source["as_of"] == "2024-01-01"
        assert "source_id" in source


def test_get_lineage_flagged_has_rejected_value_and_materiality(
    synthetic_dist: SyntheticDist,
) -> None:
    rec = _one(_load(synthetic_dist), "st03")
    assert rec["reconciliation_status"] == "flagged conflict"
    rejected = rec["rejected"]
    assert len(rejected) == 1
    assert rejected[0]["source_id"] == "rajya_sabha"
    assert rejected[0]["value"] == "4025000"
    mat = rec["materiality"]
    assert mat["relative_pct"] == "4.17"
    assert mat["absolute"] == "175000"
    assert mat["unit_class"] == "count"
    assert mat["material"] is True


def test_get_lineage_null_cell_reasons(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    assert _one(ds, "st02")["value"] is None
    assert _one(ds, "st02")["null_reason"]["reason"] == "unadjudicated"
    assert _one(ds, "st04")["null_reason"]["reason"] == "partial-period-only"
    # a non-null fact has no null_reason
    assert _one(ds, "st01")["null_reason"] is None


def test_get_lineage_batch_returns_all(synthetic_dist: SyntheticDist) -> None:
    result = lineage.get_lineage(_load(synthetic_dist), ["st01", "nt02", "ds02"])
    recs = {r["fact_id"]: r for r in _records(result)}
    assert set(recs) == {"st01", "nt02", "ds02"}
    assert all(r["found"] for r in recs.values())


def test_get_lineage_unknown_id_is_found_false(synthetic_dist: SyntheticDist) -> None:
    rec = _one(_load(synthetic_dist), "does_not_exist")
    assert rec["found"] is False


def test_get_lineage_one_hop_from_query(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = run_query(ds, "state_annual_series", metrics=["households_employed"])
    assert isinstance(env, dict)
    fact_id = cast(list[dict[str, Any]], env["rows"])[0]["fact_id"]
    rec = _one(ds, fact_id)
    assert rec["fact_id"] == fact_id
    assert rec["found"] is True


@pytest.mark.golden
def test_golden_goa_persondays_lineage_has_concrete_source() -> None:
    ds = loader.load_dataset()
    env = run_query(
        ds,
        "state_annual_series",
        metrics=["persondays_generated"],
        states=["Goa"],
        fy_from="2022-23",
        fy_to="2022-23",
    )
    assert isinstance(env, dict)
    rows = cast(list[dict[str, Any]], env["rows"])
    assert len(rows) == 1
    rec = _one(ds, rows[0]["fact_id"])
    assert rec["found"] is True
    concrete = [
        s for s in rec["sources"] if s["resource_id"] and s["as_of"] and s["value"] is not None
    ]
    assert concrete, "expected at least one source with a resource_id, as-of date, and value"


@pytest.mark.golden
def test_golden_pre2018_flagged_disagreements() -> None:
    ds = loader.load_dataset()
    fact_ids = [
        r[0]
        for r in ds.con.execute(
            "SELECT fact_id FROM state_annual_series "
            "WHERE confidence = 'flagged-disagreement' AND financial_year < '2018-19'"
        ).fetchall()
    ]
    recs = _records(lineage.get_lineage(ds, fact_ids))
    assert len(recs) == 9
    assert all(r["rejected"] for r in recs)  # each carries its rejected value
    by_metric = Counter(r["metric"] for r in recs)
    assert by_metric["households_employed"] == 4
    assert by_metric["total_expenditure"] == 5


@pytest.mark.golden
def test_golden_lineage_fact_ids_are_unique() -> None:
    # get_lineage assumes one provenance record per fact: it returns a single record per fact_id
    # and callers read rec["sources"] as that fact's complete source set. A duplicate fact_id would
    # silently split a fact's provenance across records, so the sealed dist must carry none.
    ds = loader.load_dataset()
    row = ds.con.execute("SELECT count(*), count(DISTINCT fact_id) FROM lineage").fetchone()
    assert row is not None
    total, distinct = row
    assert total == distinct, f"lineage has {total - distinct} duplicate fact_id record(s)"
    assert total > 0


@pytest.mark.golden
def test_golden_174_null_cells_split_by_reason() -> None:
    ds = loader.load_dataset()
    fact_ids = [
        r[0]
        for r in ds.con.execute(
            "SELECT fact_id FROM state_annual_series WHERE value IS NULL"
        ).fetchall()
    ]
    assert len(fact_ids) == 174
    recs = _records(lineage.get_lineage(ds, fact_ids))
    reasons = Counter(r["null_reason"]["reason"] for r in recs)
    assert reasons == {"partial-period-only": 164, "unadjudicated": 10}
