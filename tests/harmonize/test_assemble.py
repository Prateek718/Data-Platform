"""Assembly core — per-source values grouped by canonical key, reconciled into canonical facts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.assemble import assemble
from data_platform.harmonize.config import PERSONDAYS_GENERATED
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.resolve.models import GeoLevel

_AS_OF = datetime(2025, 3, 7, tzinfo=UTC)


def _key(state: str, fy: str) -> CanonicalKey:
    return CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code=state,
        district_code=None,
        fin_year=fy,
        month=None,
        metric=PERSONDAYS_GENERATED,
    )


def _sv(source_id: str, value: str, rank: int) -> SourceValue:
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit="person-days",
        source_as_of=_AS_OF,
        authority_rank=rank,
    )


def test_groups_by_key_and_reconciles_agreeing_sources() -> None:
    goa = _key("30", "2022-23")
    facts = assemble(
        [
            (goa, _sv("SRC_FLAGSHIP", "94004", 0)),
            (goa, _sv("SRC_RS", "94000", 1)),
        ]
    )
    assert len(facts) == 1
    fact = facts[0]
    assert fact.key == goa
    assert fact.value == Decimal("94004")
    assert fact.unit == "person-days"
    assert fact.reconciliation.resolution_rule_id == "R4-REC-01"
    assert fact.quarantined is False
    assert fact.quarantine_reason is None


def test_separate_keys_produce_separate_facts() -> None:
    facts = assemble(
        [
            (_key("30", "2022-23"), _sv("SRC_FLAGSHIP", "94004", 0)),
            (_key("30", "2023-24"), _sv("SRC_FLAGSHIP", "42000", 0)),
            (_key("29", "2022-23"), _sv("SRC_FLAGSHIP", "5000000", 0)),
        ]
    )
    assert len(facts) == 3
    assert {f.key.fin_year for f in facts if f.key.state_code == "30"} == {"2022-23", "2023-24"}


def test_disagreement_beyond_tolerance_is_carried_onto_the_fact() -> None:
    goa = _key("30", "2023-24")
    facts = assemble([(goa, _sv("SRC_FLAGSHIP", "42000", 0)), (goa, _sv("SRC_RS", "43000", 1))])
    assert len(facts) == 1
    assert facts[0].reconciliation.disagreement is not None
    assert facts[0].reconciliation.disagreement.rule_id == "R4-REC-02"


def test_negative_value_is_flagged_quarantined_r4_q_01() -> None:
    goa = _key("30", "2022-23")
    facts = assemble([(goa, _sv("SRC_FLAGSHIP", "-5", 0))])
    assert len(facts) == 1
    assert facts[0].quarantined is True
    assert facts[0].quarantine_reason == "negative_value"
