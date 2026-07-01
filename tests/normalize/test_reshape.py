"""Stage 3.5 reshape — wide/single-period source rows → long records (pre Stage-2 cleaning).

Pure, source-agnostic transforms driven by per-resource config. The hard one is the compound
melt: a fused ``metric___YYYY_YY`` header must split into BOTH a metric stem and a financial year,
handling 2-digit and 4-digit year forms and never double-counting a full-form ``YYYY-YYYY``
end-year as a separate start year.
"""

from __future__ import annotations

from data_platform.normalize.reshape import (
    Row,
    compound_melt,
    inject_geo,
    inject_period,
    parse_compound_header,
    simple_melt,
)


def test_parse_compound_header_two_digit_end() -> None:
    assert parse_compound_header("households_provided_employment___2015_16") == (
        "households_provided_employment",
        "2015-16",
    )


def test_parse_compound_header_four_digit_end_not_double_counted() -> None:
    # Full-form 2011-2012: the year token is the whole span; the stem is everything before it,
    # and 2012 must NOT be mistaken for a second start year.
    assert parse_compound_header("central_release___2011_2012") == ("central_release", "2011-2012")


def test_parse_compound_header_with_trailing_provisional_marker() -> None:
    # Trailing "_p_" (provisional) after the year is not part of the stem or the year.
    assert parse_compound_header("total_works_takenup__2010_11_p_") == (
        "total_works_takenup",
        "2010-11",
    )


def test_parse_compound_header_no_year_returns_none() -> None:
    assert parse_compound_header("state_ut") is None


def test_simple_melt_year_columns_to_rows() -> None:
    rows: list[Row] = [{"state_ut": "Goa", "_2019_20": 0.34, "_2020_21": 1.1}]
    out, cols = simple_melt(rows, id_columns=["state_ut"], year_columns=["_2019_20", "_2020_21"])
    assert cols == ["state_ut", "_fin_year", "_value"]
    assert out == [
        {"state_ut": "Goa", "_fin_year": "2019-20", "_value": 0.34},
        {"state_ut": "Goa", "_fin_year": "2020-21", "_value": 1.1},
    ]


def test_compound_melt_splits_metric_and_year() -> None:
    rows: list[Row] = [
        {
            "states": "Goa",
            "hh_demanded___2014_15": 10,
            "hh_demanded___2015_16": 12,
            "hh_provided___2014_15": 9,
        }
    ]
    out, cols = compound_melt(rows, id_columns=["states"])
    assert cols == ["states", "_metric", "_fin_year", "_value"]
    assert {(r["_metric"], r["_fin_year"], r["_value"]) for r in out} == {
        ("hh_demanded", "2014-15", 10),
        ("hh_demanded", "2015-16", 12),
        ("hh_provided", "2014-15", 9),
    }
    assert all(r["states"] == "Goa" for r in out)


def test_compound_melt_raises_on_unmeltable_nonid_column() -> None:
    # Zero-data-loss: a non-id column with NO year cannot be melted; refuse rather than drop it.
    rows: list[Row] = [{"states": "Goa", "mystery_column": 5, "hh___2014_15": 1}]
    try:
        compound_melt(rows, id_columns=["states"])
    except ValueError as e:
        assert "mystery_column" in str(e)
    else:
        raise AssertionError("expected ValueError for an unmeltable non-id column")


def test_inject_period_adds_fin_year() -> None:
    rows: list[Row] = [{"state": "Goa", "persondays": 42}]
    out, cols = inject_period(rows, fin_year="2016-17", columns=["state", "persondays"])
    assert cols == ["state", "persondays", "_fin_year"]
    assert out == [{"state": "Goa", "persondays": 42, "_fin_year": "2016-17"}]


def test_inject_geo_adds_state() -> None:
    rows: list[Row] = [{"_fin_year": "2016-17", "persondays": 42}]
    out, cols = inject_geo(rows, state_name="Karnataka", columns=["_fin_year", "persondays"])
    assert cols == ["_fin_year", "persondays", "_state"]
    assert out == [{"_fin_year": "2016-17", "persondays": 42, "_state": "Karnataka"}]
