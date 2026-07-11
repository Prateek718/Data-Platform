"""Unit tests for pure extraction helpers (no archive needed)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.config import AVG_WAGE_RATE_PER_DAY, HOUSEHOLDS_EMPLOYED
from data_platform.harmonize.extract import (
    flagship_district_annual_avg_wage,
    roll_to_national,
)
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch, ResolvedRecord

_AS_OF = datetime(2025, 3, 7, tzinfo=UTC)


def _state_kv(
    state: str, value: str, *, fin_year: str = "2019-20"
) -> tuple[CanonicalKey, SourceValue]:
    key = CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code=state,
        district_code=None,
        fin_year=fin_year,
        month=None,
        metric=HOUSEHOLDS_EMPLOYED,
    )
    sv = SourceValue(
        source_id="SRC_FLAGSHIP",
        value=Decimal(value),
        original_unit="count",
        source_as_of=_AS_OF,
        authority_rank=0,
    )
    return key, sv


def test_roll_to_national_sums_reporting_states() -> None:
    out = roll_to_national(
        [_state_kv("28", "100"), _state_kv("29", "250")],
        source_id="SRC_FLAGSHIP",
        authority_rank=0,
    )
    assert len(out) == 1
    key, sv = out[0]
    assert key.geo_level is GeoLevel.NATIONAL and key.state_code is None
    assert key.fin_year == "2019-20" and key.metric == HOUSEHOLDS_EMPLOYED
    assert sv.value == Decimal("350")
    assert sv.authority_rank == 0


def test_roll_to_national_groups_by_year() -> None:
    # A non-reporting state contributes no source value; totals are per (fin_year, metric).
    out = roll_to_national(
        [_state_kv("28", "100"), _state_kv("29", "40", fin_year="2020-21")],
        source_id="SRC_FLAGSHIP",
        authority_rank=0,
    )
    by_year = {key.fin_year: sv.value for key, sv in out}
    assert by_year == {"2019-20": Decimal("100"), "2020-21": Decimal("40")}


# --- flagship_district_annual_avg_wage (avg_wage_rate is a cumulative-YTD ratio → FY-final only) --


def _district_batch(records: list[ResolvedRecord]) -> ResolvedBatch:
    return ResolvedBatch(
        source_id="SRC_FLAGSHIP",
        resource_id="ee03643a",
        ingested_at=_AS_OF,
        source_as_of=_AS_OF,
        schema_version="v1",
        source_grain="district+monthly",
        pull_completeness="full",
        records=records,
        quarantined=[],
    )


def _district_record(row_index: int, state_id: str, district_id: str) -> ResolvedRecord:
    return ResolvedRecord(
        row_index=row_index,
        scheme_canonical_id="MGNREGA",
        geo_level=GeoLevel.DISTRICT,
        state_canonical_id=state_id,
        state_canonical_name=None,
        district_canonical_id=district_id,
        district_canonical_name=None,
        geo_resolution=None,
        present_in=["SRC_FLAGSHIP"],
        sources_seen=1,
    )


def _wage_cell(fin_year: str, month: str, wage: str, persondays: str) -> dict[str, CleanCell]:
    return {
        "fin_year": fin_year,
        "month": month,  # canonical "01".."12"; "03" = March is the FY-final month
        "Average_Wage_rate_per_day_per_person": Decimal(wage),
        "Persondays_of_Central_Liability_so_far": Decimal(persondays),
    }


def test_district_annual_avg_wage_takes_the_fy_final_month_value() -> None:
    # The column is cumulative-YTD wages ÷ cumulative-YTD persondays: only its FY-final (March)
    # value is the true annual rate. April's value (₹18,623/day here — arrears on a near-zero
    # persondays base) must NOT win; the value is neither summed nor averaged across months.
    records = [_district_record(0, "10", "111"), _district_record(1, "10", "111")]
    cells: dict[int, dict[str, CleanCell]] = {
        0: _wage_cell("2018-19", "04", "18623.25759", "12050"),  # April, YTD ratio
        1: _wage_cell("2018-19", "03", "103.392742752098", "5232066"),  # March, the annual rate
    }
    out = flagship_district_annual_avg_wage(_district_batch(records), cells, source_as_of=_AS_OF)
    assert len(out) == 1
    key, sv = out[0]
    assert key.geo_level is GeoLevel.DISTRICT
    assert key.state_code == "10" and key.district_code == "111"
    assert key.fin_year == "2018-19"
    assert key.month is None  # DISTRICT-ANNUAL grain, not monthly
    assert key.metric == AVG_WAGE_RATE_PER_DAY
    assert sv.value == Decimal("103.392742752098")  # FY-final (= 103.39274 to 5dp), not April
    assert sv.original_unit == "INR"


def test_district_annual_avg_wage_absent_when_fy_final_persondays_zero() -> None:
    # Where the FY-final row has zero cumulative persondays the rate is undefined (0/0): the fact is
    # honestly ABSENT — never 0, and never a stale earlier month (null ≠ 0, TIER-1 rule 4).
    records = [_district_record(0, "10", "222"), _district_record(1, "10", "222")]
    cells: dict[int, dict[str, CleanCell]] = {
        0: _wage_cell("2018-19", "04", "250.0", "1000"),  # April had activity
        1: _wage_cell("2018-19", "03", "0", "0"),  # FY-final March: no persondays → rate undefined
    }
    out = flagship_district_annual_avg_wage(_district_batch(records), cells, source_as_of=_AS_OF)
    assert out == []


def test_district_annual_avg_wage_absent_when_final_month_not_march() -> None:
    # A cumulative-YTD ratio is a genuine ANNUAL rate only for a COMPLETE financial year (March
    # present). FY2026-27 is April-only and PERMANENTLY partial — MGNREGA was repealed 30 Jun 2026,
    # so that FY never completes; its arrears-contaminated early-YTD ratio is not an annual rate and
    # the fact is honestly absent (R4-DEF-03).
    records = [_district_record(0, "10", "333")]
    cells: dict[int, dict[str, CleanCell]] = {
        0: _wage_cell("2026-27", "04", "18623.25759", "12050"),  # April only — FY never completes
    }
    out = flagship_district_annual_avg_wage(_district_batch(records), cells, source_as_of=_AS_OF)
    assert out == []
