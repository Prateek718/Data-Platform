"""R4-REC — cross-source reconciliation: agree, disagree-and-record, single-source, exact counts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from data_platform.harmonize.models import SourceValue
from data_platform.harmonize.reconcile import reconcile

_AS_OF = datetime(2025, 3, 7, tzinfo=UTC)


def _sv(source_id: str, value: str, rank: int) -> SourceValue:
    return SourceValue(
        source_id=source_id,
        value=Decimal(value),
        original_unit="lakh",
        source_as_of=_AS_OF,
        authority_rank=rank,
    )


def test_no_values_returns_none() -> None:
    assert reconcile([], metric="persondays_generated") is None


def test_single_source_is_taken_with_no_disagreement() -> None:
    out = reconcile([_sv("SRC_FLAGSHIP", "94004", 0)], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("94004")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.disagreement is None
    assert len(out.sources_seen) == 1
    assert out.resolution_rule_id == "R4-REC-04"


def test_within_tolerance_agrees_and_takes_authoritative() -> None:
    # 94,004 vs 94,000 = 0.004% < 0.5% → agree; flagship (rank 0) wins over RS (rank 1).
    flagship = _sv("SRC_FLAGSHIP", "94004", 0)
    rs = _sv("SRC_RS", "94000", 1)
    out = reconcile([rs, flagship], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("94004")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.disagreement is None
    assert out.resolution_rule_id == "R4-REC-01"
    assert {s.source_id for s in out.sources_seen} == {"SRC_FLAGSHIP", "SRC_RS"}


def test_beyond_tolerance_records_disagreement_but_keeps_authoritative() -> None:
    # 100 vs 130 = 30% > 0.5% → disagree; authoritative flagship value still chosen, RS recorded.
    flagship = _sv("SRC_FLAGSHIP", "100", 0)
    rs = _sv("SRC_RS", "130", 1)
    out = reconcile([flagship, rs], metric="persondays_generated")
    assert out is not None
    assert out.canonical_value == Decimal("100")
    assert out.source_id == "SRC_FLAGSHIP"
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.disagreement is not None
    assert out.disagreement.pct == Decimal("30")
    assert out.disagreement.rejected_sources == ["SRC_RS"]


def test_pure_count_requires_exact_equality() -> None:
    # active_workers is a pure count: a 1-unit difference is a disagreement, not agreement.
    a = _sv("SRC_FLAGSHIP", "1000", 0)
    b = _sv("SRC_RS", "1001", 1)
    out = reconcile([a, b], metric="active_workers")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-02"
    assert out.disagreement is not None


def test_pure_count_exact_match_agrees() -> None:
    a = _sv("SRC_FLAGSHIP", "1000", 0)
    b = _sv("SRC_RS", "1000", 1)
    out = reconcile([a, b], metric="active_workers")
    assert out is not None
    assert out.resolution_rule_id == "R4-REC-01"
    assert out.disagreement is None
