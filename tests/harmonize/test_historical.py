"""Unit tests for the pre-2018 historical extractors (no archive needed).

Covers the two truthfulness fixes on top of the plain stem→metric mapping:
* period-narrowing (partial-year) columns are NOT promoted into a full-year cell;
* count values carry a precision-derived ``rounding_epsilon`` (R4-REC-01a), so a lakh-rounded RS
  count agrees with a MoSPI raw count within the RS rounding granularity instead of being flagged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.config import HOUSEHOLDS_EMPLOYED
from data_platform.harmonize.historical import (
    MOSPI_IMPLEMENTATION_RULES,
    NATIONAL_IMPLEMENTATION_RULES,
    RS_HOUSEHOLDS_RULES,
    extract_historical_state,
    extract_national_wide,
)
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch, ResolvedRecord

_AS_OF = datetime(2020, 1, 1, tzinfo=UTC)


def _batch(records: list[ResolvedRecord], *, source_id: str = "SRC_RS") -> ResolvedBatch:
    return ResolvedBatch(
        source_id=source_id,
        resource_id="test",
        ingested_at=_AS_OF,
        source_as_of=_AS_OF,
        schema_version="v1",
        source_grain="state+annual",
        pull_completeness="full",
        records=records,
        quarantined=[],
    )


def _state_record(
    row_index: int, state_id: str, geo_level: GeoLevel = GeoLevel.STATE
) -> ResolvedRecord:
    return ResolvedRecord(
        row_index=row_index,
        scheme_canonical_id="MGNREGA",
        geo_level=geo_level,
        state_canonical_id=state_id if geo_level is GeoLevel.STATE else None,
        state_canonical_name=None,
        district_canonical_id=None,
        district_canonical_name=None,
        geo_resolution=None,
        present_in=["SRC_RS"],
        sources_seen=1,
    )


def test_partial_year_state_row_is_not_promoted() -> None:
    # A melted RS household row carrying a period qualifier ("upto ...") is a partial-year value —
    # it must NOT enter the full-year (state, FY, metric) cell.
    cells: dict[int, dict[str, CleanCell]] = {
        0: {
            "_metric": "household_provided_employment",
            "_fin_year": "2015-16",
            "_value": Decimal("32.11"),
            "_period_qualifier": "upto 30 09 2015",
        }
    }
    out = extract_historical_state(
        _batch([_state_record(0, "28")]),
        cells,
        RS_HOUSEHOLDS_RULES,
        source_as_of=_AS_OF,
        authority_rank=10,
    )
    assert out == []


def test_full_year_state_row_is_promoted_with_lakh_precision_epsilon() -> None:
    # A full-year RS household value (in lakh, 2 decimals → granularity 1,000 count) is promoted and
    # carries rounding_epsilon = 500 (half the declared 0.01-lakh step).
    cells: dict[int, dict[str, CleanCell]] = {
        0: {
            "_metric": "household_provided_employment",
            "_fin_year": "2015-16",
            "_value": Decimal("36.07"),
            "_period_qualifier": None,
        }
    }
    out = extract_historical_state(
        _batch([_state_record(0, "28")]),
        cells,
        RS_HOUSEHOLDS_RULES,
        source_as_of=_AS_OF,
        authority_rank=10,
    )
    assert len(out) == 1
    key, sv = out[0]
    assert key.metric == HOUSEHOLDS_EMPLOYED and key.fin_year == "2015-16"
    assert sv.value == Decimal("3607000.00")
    assert sv.rounding_epsilon == Decimal("500")


def test_raw_count_state_row_has_zero_epsilon() -> None:
    # MoSPI raw counts are exact → epsilon 0 (a raw count is not lakh-rounded).
    cells: dict[int, dict[str, CleanCell]] = {
        0: {
            "_metric": "No.of households provided employment",
            "_fin_year": "2015-16",
            "_value": Decimal("3606783"),
            "_period_qualifier": None,
        }
    }
    out = extract_historical_state(
        _batch([_state_record(0, "28")], source_id="SRC_MOSPI"),
        cells,
        MOSPI_IMPLEMENTATION_RULES,
        source_as_of=_AS_OF,
        authority_rank=10,
    )
    assert len(out) == 1
    _key, sv = out[0]
    assert sv.value == Decimal("3606783")
    assert sv.rounding_epsilon == Decimal("0")


def test_partial_year_national_column_is_skipped() -> None:
    # A wide national partial-year column (period-narrowing in the header) is not extracted.
    cells: dict[int, dict[str, CleanCell]] = {
        0: {
            "fin_year": "2015-16",
            "households_provided_employment": Decimal("3606783"),
            "households_provided_employment_upto_30_09_2015": Decimal("3211000"),
        }
    }
    out = extract_national_wide(
        _batch([_state_record(0, "0", geo_level=GeoLevel.NATIONAL)], source_id="SRC_MOSPI"),
        cells,
        NATIONAL_IMPLEMENTATION_RULES,
        fy_column="fin_year",
        source_as_of=_AS_OF,
        authority_rank=10,
    )
    # only the full-year column is promoted
    assert len(out) == 1
    _key, sv = out[0]
    assert sv.value == Decimal("3606783")
