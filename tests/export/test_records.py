"""Hermetic unit tests for the pure export transforms (records.py).

No archive, no I/O: synthetic SeriesFacts exercise fact_id determinism, flat-row shape (state /
national / district), the CSV↔lineage join key, null≠0 handling, and byte-identical serialization.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from data_platform.export.records import (
    DISTRICT_COLUMNS,
    NATIONAL_COLUMNS,
    STATE_COLUMNS,
    csv_bytes,
    district_row,
    fact_id,
    jsonl_bytes,
    lineage_record,
    national_row,
    state_row,
)
from data_platform.harmonize.models import (
    CanonicalKey,
    Disagreement,
    Reconciliation,
    SourceValue,
)
from data_platform.harmonize.series import Basis, Confidence, SeriesFact
from data_platform.resolve.models import GeoLevel

_AS_OF = datetime(2025, 3, 7)


def _sv(source_id: str, value: str, **kw: object) -> SourceValue:
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit=str(kw.pop("original_unit", "count")),
        source_as_of=_AS_OF,
        authority_rank=int(kw.pop("authority_rank", 10)),  # type: ignore[call-overload]
        **kw,  # type: ignore[arg-type]
    )


def _state_key(state: str, fy: str, metric: str) -> CanonicalKey:
    return CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code=state,
        district_code=None,
        fin_year=fy,
        month=None,
        metric=metric,
    )


def _fact(
    key: CanonicalKey,
    value: str | None,
    *,
    basis: Basis,
    confidence: Confidence,
    reconciliation: Reconciliation,
    quarantined: bool = False,
    quarantine_reason: str | None = None,
) -> SeriesFact:
    return SeriesFact(
        key=key,
        value=None if value is None else Decimal(value),
        unit="count",
        basis=basis,
        confidence=confidence,
        reconciliation=reconciliation,
        quarantined=quarantined,
        quarantine_reason=quarantine_reason,
    )


def _single_source_fact() -> tuple[SeriesFact, dict[int, str]]:
    sv = _sv("SRC_FLAGSHIP", "500", authority_rank=0)
    rec = Reconciliation(
        canonical_value=Decimal("500"),
        source_id="SRC_FLAGSHIP",
        sources_seen=[sv],
        disagreement=None,
        resolution_rule_id="R4-REC-04",
        adjudicated=True,
    )
    fact = _fact(
        _state_key("28", "2019-20", "households_employed"),
        "500",
        basis=Basis.FLAGSHIP_ROLLUP,
        confidence=Confidence.SINGLE_SOURCE,
        reconciliation=rec,
    )
    return fact, {id(sv): "ee03643a-flagship"}


# --- fact_id ------------------------------------------------------------------------------------


def test_fact_id_is_deterministic_and_stable() -> None:
    key = _state_key("28", "2019-20", "households_employed")
    first = fact_id(key)
    assert first == fact_id(key)  # deterministic within a run
    assert first == fact_id(_state_key("28", "2019-20", "households_employed"))  # equal key → equal
    assert len(first) == 16 and all(c in "0123456789abcdef" for c in first)


def test_fact_id_is_sensitive_to_every_key_field() -> None:
    base = _state_key("28", "2019-20", "households_employed")
    variants = [
        _state_key("29", "2019-20", "households_employed"),  # state
        _state_key("28", "2020-21", "households_employed"),  # fin_year
        _state_key("28", "2019-20", "persondays_generated"),  # metric
        CanonicalKey(  # geo_level / district
            scheme="MGNREGA",
            geo_level=GeoLevel.NATIONAL,
            state_code=None,
            district_code=None,
            fin_year="2019-20",
            month=None,
            metric="households_employed",
        ),
    ]
    ids = {fact_id(base)} | {fact_id(v) for v in variants}
    assert len(ids) == 1 + len(variants)  # all distinct


# --- flat rows ----------------------------------------------------------------------------------


def test_state_row_has_geography_and_derived_columns() -> None:
    fact, rmap = _single_source_fact()
    row = state_row(fact, state_names={"28": "Andhra Pradesh"}, resource_map=rmap)
    assert list(row) == STATE_COLUMNS
    assert row["state_lgd_code"] == "28"
    assert row["state_name"] == "Andhra Pradesh"
    assert row["financial_year"] == "2019-20"
    assert row["metric"] == "households_employed"
    assert row["value"] == Decimal("500")
    assert row["era_basis"] == "flagship-rollup"
    assert row["confidence"] == "single-source"
    assert row["sources_seen_count"] == 1
    assert row["contributing_resource_ids"] == "ee03643a-flagship"
    assert row["fact_id"] == fact_id(fact.key)


def test_national_row_drops_geography() -> None:
    sv = _sv("SRC_MOSPI", "1000")
    rec = Reconciliation(
        canonical_value=Decimal("1000"),
        source_id="SRC_MOSPI",
        sources_seen=[sv],
        disagreement=None,
        resolution_rule_id="R4-REC-04",
        adjudicated=True,
    )
    key = CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.NATIONAL,
        state_code=None,
        district_code=None,
        fin_year="2006-07",
        month=None,
        metric="persondays_generated",
    )
    fact = _fact(
        key,
        "1000",
        basis=Basis.HISTORICAL_SINGLE,
        confidence=Confidence.SINGLE_SOURCE,
        reconciliation=rec,
    )
    row = national_row(fact, resource_map={id(sv): "mospi-nat"})
    assert list(row) == NATIONAL_COLUMNS
    assert "state_lgd_code" not in row and "state_name" not in row
    assert row["era_basis"] == "historical"
    assert row["contributing_resource_ids"] == "mospi-nat"


def test_district_row_is_single_grain_district_annual() -> None:
    # district_flagship is single-grain (district-annual): no `month` column, `grain` is the
    # constant "district-annual". avg_wage_rate is published at FY-final annual grain like the rest.
    sv = _sv("SRC_FLAGSHIP", "103.392742752098", original_unit="INR", authority_rank=0)
    rec = Reconciliation(
        canonical_value=Decimal("103.392742752098"),
        source_id="SRC_FLAGSHIP",
        sources_seen=[sv],
        disagreement=None,
        resolution_rule_id="R4-REC-04",
        adjudicated=True,
    )
    key = CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.DISTRICT,
        state_code="28",
        district_code="500",
        fin_year="2018-19",
        month=None,
        metric="avg_wage_rate_per_day",
    )
    row = district_row(
        _fact(
            key,
            "103.392742752098",
            basis=Basis.FLAGSHIP_ROLLUP,
            confidence=Confidence.SINGLE_SOURCE,
            reconciliation=rec,
        ),
        state_names={"28": "Andhra Pradesh"},
        district_names={("28", "500"): "Anantapur"},
        resource_map={id(sv): "flagship"},
    )
    assert list(row) == DISTRICT_COLUMNS
    assert "month" not in row  # the month column is dropped — the file is single-grain
    assert row["district_name"] == "Anantapur"
    assert row["grain"] == "district-annual"
    assert row["value"] == Decimal("103.392742752098")


def test_null_value_is_preserved_not_zeroed() -> None:
    # An UNADJUDICATED cell has value None — must export as null, never 0 (TIER-1 rule 4).
    a = _sv("SRC_MOSPI", "100")
    b = _sv("SRC_MOSPI", "200")
    rec = Reconciliation(
        canonical_value=None,
        source_id=None,
        sources_seen=[a, b],
        disagreement=Disagreement(
            pct=Decimal("100"), rejected_sources=["SRC_MOSPI"], rule_id="R4-REC-09"
        ),
        resolution_rule_id="R4-REC-09",
        adjudicated=False,
    )
    fact = _fact(
        _state_key("28", "2015-16", "persondays_generated"),
        None,
        basis=Basis.HISTORICAL_MULTI,
        confidence=Confidence.SINGLE_PUBLISHER_DIVERGENCE,
        reconciliation=rec,
    )
    rmap = {id(a): "m1", id(b): "m2"}
    row = state_row(fact, state_names={"28": "Andhra Pradesh"}, resource_map=rmap)
    assert row["value"] is None
    assert row["sources_seen_count"] == 2
    assert row["contributing_resource_ids"] == "m1;m2"  # deduped + sorted, ';'-joined


def test_contributing_resource_ids_are_deduped_and_sorted() -> None:
    a = _sv("SRC_MOSPI", "100")
    b = _sv("SRC_MOSPI", "100")  # same publisher, different edition file
    c = _sv("SRC_RS", "100")
    rec = Reconciliation(
        canonical_value=Decimal("100"),
        source_id="SRC_MOSPI",
        sources_seen=[a, b, c],
        disagreement=None,
        resolution_rule_id="R4-REC-01",
        adjudicated=True,
    )
    fact = _fact(
        _state_key("28", "2014-15", "households_employed"),
        "100",
        basis=Basis.HISTORICAL_MULTI,
        confidence=Confidence.CROSS_PUBLISHER,
        reconciliation=rec,
    )
    rmap = {id(a): "z-mospi", id(b): "z-mospi", id(c): "a-rs"}  # a,b same resource id
    row = state_row(fact, state_names={"28": "Andhra Pradesh"}, resource_map=rmap)
    assert row["contributing_resource_ids"] == "a-rs;z-mospi"  # sorted, deduped
    assert row["sources_seen_count"] == 3  # count is of source VALUES, not distinct resources


# --- lineage ------------------------------------------------------------------------------------


def test_lineage_record_joins_on_fact_id_and_carries_deep_lineage() -> None:
    a = _sv("SRC_MOSPI", "539024", edition_span_end="2017-18")
    superseded = _sv("SRC_MOSPI", "53890", edition_span_end="2015-16", is_edition_terminal=True)
    rec = Reconciliation(
        canonical_value=Decimal("539024"),
        source_id="SRC_MOSPI",
        sources_seen=[a, superseded],
        disagreement=None,
        resolution_rule_id="R4-REC-10",
        adjudicated=True,
        edition_superseded=[superseded],
    )
    fact = _fact(
        _state_key("2", "2013-14", "households_employed"),
        "539024",
        basis=Basis.HISTORICAL_MULTI,
        confidence=Confidence.EDITION_SUPERSEDED,
        reconciliation=rec,
    )
    rmap = {id(a): "syb2018", id(superseded): "syb2016"}
    record: dict[str, Any] = lineage_record(fact, resource_map=rmap)
    assert record["fact_id"] == fact_id(fact.key)
    assert record["value"] == "539024"  # Decimal serialized as string, not float
    assert record["resolution_rule_id"] == "R4-REC-10"
    assert record["confidence"] == "edition-superseded"
    assert record["key"]["metric"] == "households_employed"
    seen_ids = {s["resource_id"] for s in record["sources_seen"]}
    assert seen_ids == {"syb2018", "syb2016"}
    assert [s["resource_id"] for s in record["edition_superseded"]] == ["syb2016"]
    assert record["disagreement"] is None


def test_lineage_record_serializes_disagreement_and_coverage() -> None:
    from data_platform.harmonize.models import AggregateCoverage

    winner = _sv("SRC_MOSPI", "94674")
    rejected = _sv(
        "SRC_RS",
        "129000",
        aggregate_coverage=AggregateCoverage(
            units_summed=10, units_in_source_universe=12, units_in_lgd=13
        ),
    )
    rec = Reconciliation(
        canonical_value=Decimal("94674"),
        source_id="SRC_MOSPI",
        sources_seen=[winner, rejected],
        disagreement=Disagreement(
            pct=Decimal("26"), rejected_sources=["SRC_RS"], rule_id="R4-REC-02"
        ),
        resolution_rule_id="R4-REC-02",
        adjudicated=True,
    )
    fact = _fact(
        _state_key("28", "2014-15", "households_employed"),
        "94674",
        basis=Basis.HISTORICAL_MULTI,
        confidence=Confidence.FLAGGED_DISAGREEMENT,
        reconciliation=rec,
    )
    record: dict[str, Any] = lineage_record(
        fact, resource_map={id(winner): "mospi", id(rejected): "rs"}
    )
    assert record["disagreement"]["pct"] == "26"
    assert record["disagreement"]["rejected_sources"] == ["SRC_RS"]
    assert record["disagreement"]["material"] is True
    cov = next(s["aggregate_coverage"] for s in record["sources_seen"] if s["resource_id"] == "rs")
    assert cov["status"] == "structural_gap"  # 12 < 13


# --- serialization determinism ------------------------------------------------------------------


def test_csv_bytes_are_sorted_and_byte_identical_across_runs() -> None:
    rows: list[dict[str, Any]] = [
        {"financial_year": "2019-20", "metric": "persondays_generated", "value": Decimal("2")},
        {"financial_year": "2006-07", "metric": "households_employed", "value": None},
        {"financial_year": "2006-07", "metric": "persondays_generated", "value": Decimal("1")},
    ]
    cols = ["financial_year", "metric", "value"]
    out1 = csv_bytes(rows, columns=cols, sort_by=("financial_year", "metric"))
    out2 = csv_bytes(rows, columns=cols, sort_by=("financial_year", "metric"))
    assert out1 == out2  # byte-identical
    text = out1.decode()
    lines = text.split("\n")
    assert lines[0] == "financial_year,metric,value"
    # sorted: 2006-07/households first, then 2006-07/persondays, then 2019-20/persondays
    assert lines[1] == "2006-07,households_employed,"  # None → empty, never 0
    assert lines[2] == "2006-07,persondays_generated,1"
    assert lines[3] == "2019-20,persondays_generated,2"


def test_jsonl_bytes_are_byte_identical_and_one_object_per_line() -> None:
    records: list[dict[str, Any]] = [
        {"fact_id": "b", "value": "2"},
        {"fact_id": "a", "value": None},
    ]
    out1 = jsonl_bytes(records, sort_by="fact_id")
    out2 = jsonl_bytes(records, sort_by="fact_id")
    assert out1 == out2
    lines = out1.decode().rstrip("\n").split("\n")
    assert len(lines) == 2
    assert lines[0].startswith('{"fact_id": "a"')  # sorted by fact_id
