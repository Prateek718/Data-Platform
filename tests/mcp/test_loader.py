"""Unit tests for the checksum gate + in-memory DuckDB loader (Stage 7 step 1)."""

from __future__ import annotations

import json

import pytest

from data_platform.mcp import loader
from tests.conftest import SyntheticDist


def _load(sd: SyntheticDist) -> loader.Dataset:
    return loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path)


def test_load_reports_fixture_row_counts(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    assert ds.row_counts == synthetic_dist.counts
    assert ds.row_counts == {
        "state_annual_series": 4,
        "national_annual_series": 2,
        "district_flagship": 2,
        "lineage": 8,
    }


def test_all_four_tables_queryable(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    for table, expected in synthetic_dist.counts.items():
        (count,) = ds.con.execute(f"SELECT count(*) FROM {table}").fetchone()  # type: ignore[misc]
        assert count == expected


def test_value_column_preserves_null_and_number(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    (null_value,) = ds.con.execute(
        "SELECT value FROM state_annual_series WHERE fact_id = 'st02'"
    ).fetchone()  # type: ignore[misc]
    assert null_value is None  # null cell stays null, never 0
    (num,) = ds.con.execute(
        "SELECT value FROM state_annual_series WHERE fact_id = 'st01'"
    ).fetchone()  # type: ignore[misc]
    assert num == 1000000.0


def test_lineage_record_is_json_keyed_by_fact_id(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    (record,) = ds.con.execute("SELECT record FROM lineage WHERE fact_id = 'st03'").fetchone()  # type: ignore[misc]
    parsed = json.loads(record)
    assert parsed["fact_id"] == "st03"
    assert parsed["disagreement"]["rejected_sources"] == ["rajya_sabha"]


def test_checksum_gate_refuses_tampered_file(synthetic_dist: SyntheticDist) -> None:
    target = synthetic_dist.dir / "district_flagship.parquet"
    target.write_bytes(target.read_bytes() + b"\x00")  # one appended byte
    with pytest.raises(loader.ChecksumMismatchError) as exc:
        _load(synthetic_dist)
    msg = str(exc.value)
    assert "district_flagship.parquet" in msg
    assert "expected" in msg and "actual" in msg


def test_checksum_gate_refuses_missing_file(synthetic_dist: SyntheticDist) -> None:
    (synthetic_dist.dir / "lineage.jsonl").unlink()
    with pytest.raises(loader.MissingArtifactError) as exc:
        _load(synthetic_dist)
    assert "lineage.jsonl" in str(exc.value)


def test_parse_manifest_skips_comments_and_blanks() -> None:
    parsed = loader.parse_manifest(loader.DEFAULT_MANIFEST)
    assert set(parsed) == {
        "state_annual_series.csv",
        "state_annual_series.parquet",
        "national_annual_series.csv",
        "national_annual_series.parquet",
        "district_flagship.csv",
        "district_flagship.parquet",
        "lineage.jsonl",
    }
    assert all(len(digest) == 64 for digest in parsed.values())


@pytest.mark.golden
def test_golden_real_dist_row_counts() -> None:
    ds = loader.load_dataset()
    assert ds.row_counts == {
        "state_annual_series": 4219,
        "national_annual_series": 148,
        "district_flagship": 57181,
        "lineage": 61548,
    }
