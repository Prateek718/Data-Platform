"""Unit tests for pure extraction helpers (no archive needed)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.config import HOUSEHOLDS_EMPLOYED
from data_platform.harmonize.extract import roll_to_national
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.resolve.models import GeoLevel

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
