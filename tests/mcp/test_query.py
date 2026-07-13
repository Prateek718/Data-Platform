"""Unit tests for the constrained filter query API + refusals + row cap (Stage 7 step 3)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from data_platform.mcp import loader, query, refusals
from data_platform.mcp.query import query as run_query
from tests.mcp.conftest import SyntheticDist


def _load(sd: SyntheticDist) -> loader.Dataset:
    return loader.load_dataset(dist_dir=sd.dir, manifest_path=sd.manifest_path)


def _ok(result: dict[str, object] | refusals.Refusal) -> dict[str, Any]:
    assert isinstance(result, dict), f"expected rows, got refusal: {result}"
    return cast(dict[str, Any], result)


def _refusal(result: dict[str, object] | refusals.Refusal) -> refusals.Refusal:
    assert isinstance(result, refusals.Refusal), f"expected refusal, got rows: {result}"
    return result


def test_query_returns_rows_with_fact_id_and_envelope(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = _ok(run_query(ds, "district_flagship", states=["Jammu and Kashmir"]))
    assert env["table"] == "district_flagship"
    assert env["row_count"] == len(env["rows"])
    assert all("fact_id" in row for row in env["rows"])
    assert env["filters"]["states"] == ["01"]


def test_query_by_metric(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = _ok(run_query(ds, "state_annual_series", metrics=["households_employed"]))
    assert env["row_count"] == 1
    assert env["rows"][0]["fact_id"] == "st03"


def test_query_geo_by_name_matches_by_code(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    by_name = _ok(run_query(ds, "state_annual_series", states=["Kerala"]))
    by_code = _ok(run_query(ds, "state_annual_series", states=["32"]))
    assert by_name["rows"] == by_code["rows"]
    assert by_name["row_count"] == 1


def test_query_null_cell_is_data_not_refusal(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = _ok(run_query(ds, "state_annual_series", metrics=["total_expenditure"], states=["01"]))
    assert env["row_count"] == 1
    assert env["rows"][0]["fact_id"] == "st02"
    assert env["rows"][0]["value"] is None  # null cell returned as data, never a refusal


def test_query_in_coverage_empty_result_is_not_a_refusal(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = _ok(run_query(ds, "district_flagship", fy_from="2019-20", fy_to="2019-20"))
    assert env["row_count"] == 0
    assert env["rows"] == []


def test_query_unknown_metric_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", metrics=["not_a_metric"]))
    assert ref.code == refusals.UNKNOWN_METRIC
    assert ref.options is not None


def test_query_wage_on_state_points_to_district(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", metrics=["avg_wage_rate_per_day"]))
    assert ref.code == refusals.UNKNOWN_METRIC
    assert ref.pointer == "district_flagship"


def test_query_unknown_state_refuses_with_options(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", states=["Atlantis"]))
    assert ref.code == refusals.UNKNOWN_GEOGRAPHY
    assert ref.options is not None and "Kerala" in ref.options


def test_query_district_filter_on_state_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", districts=["Anantnag"]))
    assert ref.code == refusals.UNKNOWN_GEOGRAPHY
    assert ref.pointer == "district_flagship"


def test_query_states_on_national_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "national_annual_series", states=["01"]))
    assert ref.code == refusals.UNKNOWN_GEOGRAPHY


def test_query_post_repeal_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", fy_from="2027-28"))
    assert ref.code == refusals.RECORD_SEALED


def test_query_state_pre_floor_refuses_and_points_to_national(
    synthetic_dist: SyntheticDist,
) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", fy_to="2008-09"))
    assert ref.code == refusals.STATE_SERIES_FLOOR
    assert ref.pointer == "national_annual_series"


def test_query_monthly_wage_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(
        run_query(ds, "district_flagship", metrics=["avg_wage_rate_per_day"], month="2018-04")
    )
    assert ref.code == refusals.MONTHLY_WAGE_UNAVAILABLE


def test_query_row_cap_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(
        run_query(ds, "state_annual_series", metrics=["persondays_generated"], row_cap=1)
    )
    assert ref.code == refusals.ROW_CAP_EXCEEDED


def test_query_lineage_table_points_to_get_lineage(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "lineage"))
    # The table is known but the verb is wrong: a distinct code from an unknown table name.
    assert ref.code == refusals.TABLE_NOT_QUERYABLE
    assert ref.code != refusals.UNKNOWN_TABLE
    assert ref.pointer == "get_lineage"


def test_query_unknown_table_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "bogus"))
    assert ref.code == refusals.UNKNOWN_TABLE


def test_row_cap_default_is_config_carried() -> None:
    assert query.DEFAULT_ROW_CAP == 10000


def test_query_district_pre_flagship_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "district_flagship", fy_to="2017-18"))
    assert ref.code == refusals.DISTRICT_SERIES_FLOOR
    assert ref.pointer == "state_annual_series"


def test_query_national_pre_start_refuses(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "national_annual_series", fy_to="2005-06"))
    assert ref.code == refusals.NATIONAL_SERIES_FLOOR


@pytest.mark.parametrize(
    "bad_fy",
    ["2019", "FY2018-19", "2018-2019", "2018-25", "", "2018-19 ", "２０１８-19"],
)
def test_query_malformed_fy_from_refuses(synthetic_dist: SyntheticDist, bad_fy: str) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", fy_from=bad_fy))
    assert ref.code == refusals.INVALID_PERIOD
    assert "YYYY-YY" in ref.reason  # the reason states the expected format


@pytest.mark.parametrize("bad_fy", ["2019", "FY2018-19", "2018-2019", "2018-25"])
def test_query_malformed_fy_to_refuses(synthetic_dist: SyntheticDist, bad_fy: str) -> None:
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", fy_to=bad_fy))
    assert ref.code == refusals.INVALID_PERIOD


def test_query_malformed_fy_refuses_before_coverage_comparison(
    synthetic_dist: SyntheticDist,
) -> None:
    # Format is checked first: a malformed value never reaches the lexicographic floor/ceiling
    # comparison, which is only chronological for well-formed values.
    ds = _load(synthetic_dist)
    ref = _refusal(run_query(ds, "state_annual_series", fy_from="9999", fy_to="1999"))
    assert ref.code == refusals.INVALID_PERIOD


def test_query_well_formed_fy_passes_validation(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    env = _ok(run_query(ds, "state_annual_series", fy_from="2015-16", fy_to="2018-19"))
    assert env["filters"]["fy_from"] == "2015-16"
    assert env["row_count"] > 0


def test_query_coverage_floor_boundary_years_succeed(synthetic_dist: SyntheticDist) -> None:
    ds = _load(synthetic_dist)
    # The floor year itself is in scope: it must return a (possibly empty) envelope, not refuse.
    district = _ok(run_query(ds, "district_flagship", fy_from="2018-19", fy_to="2018-19"))
    assert district["row_count"] == 2
    national = _ok(run_query(ds, "national_annual_series", fy_from="2006-07", fy_to="2006-07"))
    assert national["row_count"] == 1
    # state floor 2010-11: in scope but the fixture has no rows there — empty, still not a refusal.
    state = _ok(run_query(ds, "state_annual_series", fy_from="2010-11", fy_to="2010-11"))
    assert state["row_count"] == 0


@pytest.mark.golden
def test_golden_anantnag_wage_exact_value() -> None:
    ds = loader.load_dataset()
    env = _ok(
        run_query(
            ds,
            "district_flagship",
            metrics=["avg_wage_rate_per_day"],
            districts=["Anantnag"],
            fy_from="2018-19",
            fy_to="2018-19",
        )
    )
    values = [row["value"] for row in env["rows"]]
    assert values == [103.392742752098]


@pytest.mark.golden
def test_golden_post_repeal_and_monthly_wage_refusals() -> None:
    ds = loader.load_dataset()
    assert _refusal(run_query(ds, "state_annual_series", fy_from="2027-28")).code == (
        refusals.RECORD_SEALED
    )
    assert (
        _refusal(
            run_query(ds, "district_flagship", metrics=["avg_wage_rate_per_day"], month="2019-04")
        ).code
        == refusals.MONTHLY_WAGE_UNAVAILABLE
    )
