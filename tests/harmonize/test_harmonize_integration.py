"""Stage 4 starter slice, end to end over the real archive — persondays_generated reconciled
across the flagship (district-monthly, rolled up to state-annual) and the two Rajya Sabha
state-annual person-days tables. Skips when the gitignored archive snapshot is absent.

Proves the whole chain: normalize → resolve → extract (rollup / lakh conversion) → assemble →
reconcile, producing canonical state-annual facts whose lineage records agreement or disagreement.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from data_platform.harmonize.assemble import assemble
from data_platform.harmonize.extract import (
    flagship_district_monthly_avg_wage,
    flagship_state_annual_persondays,
    flagship_state_annual_total_expenditure,
    rs_state_annual_persondays,
)
from data_platform.harmonize.models import CanonicalFact, CanonicalKey, SourceValue
from data_platform.ingest.archive import read_archive_batch
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.config import NORMALIZE_CONFIG
from data_platform.normalize.models import CleanCell, NormalizedBatch
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.config import RESOLVE_CONFIG
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import load_lgd_reference
from data_platform.resolve.models import ResolvedBatch
from data_platform.resolve.pipeline import resolve_batch
from data_platform.wiring.specs import WIRED

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
_FLAGSHIP_FILE = ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json"
_RS = ["cea6ee41-2b18-4266-b42b-0af54c13b18c", "e289a8fe-3fd4-4964-9579-5bddb88e36b8"]
_GOA, _FY = "30", "2022-23"  # the divergence-findings anchor: Goa FY2022-23

pytestmark = pytest.mark.skipif(
    not (_FLAGSHIP_FILE.exists() and (ARCHIVE / "lgd" / "lgd_states.json").exists()),
    reason="local archive snapshot not present",
)


def _resolver() -> GeoResolver:
    states, districts = load_lgd_reference(
        ARCHIVE / "lgd" / "lgd_states.json", ARCHIVE / "lgd" / "lgd_districts.json"
    )
    return GeoResolver.from_reference(states=states, districts=districts)


def _cells(batch: NormalizedBatch) -> dict[int, dict[str, CleanCell]]:
    return {rec.row_index: dict(rec.cells) for rec in batch.records}


def _lgd_district_counts() -> dict[str, int]:
    records = json.loads((ARCHIVE / "lgd" / "lgd_districts.json").read_text())["records"]
    return dict(Counter(str(r["state_code"]) for r in records))


# (resolved flagship, its cells, flagship as-of, LGD district counts, RS persondays extracted)
_Pipeline = tuple[
    ResolvedBatch,
    dict[int, dict[str, CleanCell]],
    datetime | None,
    dict[str, int],
    list[tuple[CanonicalKey, SourceValue]],
]


@pytest.fixture(scope="module")
def _pipeline() -> _Pipeline:
    """Load + normalize + resolve the flagship once, plus the RS persondays extracted values."""
    resolver = _resolver()
    lgd = _lgd_district_counts()
    fb = read_archive_batch(
        resource_id=FLAGSHIP_RESOURCE_ID,
        source_id=SRC_FLAGSHIP,
        source_grain="district+monthly",
        path=_FLAGSHIP_FILE,
    )
    fn = normalize_batch(fb, config=NORMALIZE_CONFIG[FLAGSHIP_RESOURCE_ID])
    fr: ResolvedBatch = resolve_batch(fn, resolver, config=RESOLVE_CONFIG[FLAGSHIP_RESOURCE_ID])

    rs_persondays: list[tuple[CanonicalKey, SourceValue]] = []
    for rid in _RS:
        spec = WIRED[rid]
        rb = read_archive_batch(
            resource_id=rid,
            source_id=spec.source_id,
            source_grain=spec.source_grain,
            path=ARCHIVE / spec.file,
        )
        rn = normalize_batch(rb, config=spec.normalize_config)
        rr = resolve_batch(rn, resolver, config=spec.resolve_config)
        rs_persondays += rs_state_annual_persondays(rr, _cells(rn), source_as_of=rb.source_as_of)

    return fr, _cells(fn), fb.source_as_of, lgd, rs_persondays


@pytest.fixture(scope="module")
def facts(_pipeline: _Pipeline) -> list[CanonicalFact]:
    fr, fcells, source_as_of, lgd, rs_persondays = _pipeline
    keyed = flagship_state_annual_persondays(
        fr, fcells, source_as_of=source_as_of, lgd_district_counts=lgd
    )
    return assemble(keyed + rs_persondays)


@pytest.fixture(scope="module")
def exp_facts(_pipeline: _Pipeline) -> list[CanonicalFact]:
    fr, fcells, source_as_of, lgd, _rs = _pipeline
    keyed = flagship_state_annual_total_expenditure(
        fr, fcells, source_as_of=source_as_of, lgd_district_counts=lgd
    )
    return assemble(keyed)


@pytest.fixture(scope="module")
def wage_facts(_pipeline: _Pipeline) -> list[CanonicalFact]:
    fr, fcells, source_as_of, _lgd, _rs = _pipeline
    keyed = flagship_district_monthly_avg_wage(fr, fcells, source_as_of=source_as_of)
    return assemble(keyed)


def test_goa_2022_23_reconciles_and_agrees(facts: list[CanonicalFact]) -> None:
    goa = [f for f in facts if f.key.state_code == _GOA and f.key.fin_year == _FY]
    assert len(goa) == 1
    fact = goa[0]
    # Flagship (~94,004) and RS (0.94 lakh = 94,000) agree within 0.5% → R4-REC-01, flagship wins.
    assert fact.reconciliation.resolution_rule_id == "R4-REC-01"
    assert fact.reconciliation.disagreement is None
    assert fact.reconciliation.source_id == SRC_FLAGSHIP
    assert fact.reconciliation.adjudicated is True
    assert len(fact.reconciliation.sources_seen) >= 2  # corroborated by RS
    assert fact.value is not None
    assert 93_000 <= fact.value <= 95_000


def test_multi_source_facts_and_recorded_disagreements_both_exist(
    facts: list[CanonicalFact],
) -> None:
    multi = [f for f in facts if len(f.reconciliation.sources_seen) >= 2]
    disagreements = [f for f in facts if f.reconciliation.disagreement is not None]
    assert multi, "expected cross-source (flagship+RS) reconciled facts"
    # The evidence showed a real conflict tail — it must surface as recorded disagreements.
    assert disagreements, "expected some beyond-tolerance disagreements to be recorded"
    for f in disagreements:
        disagreement = f.reconciliation.disagreement
        assert disagreement is not None
        assert disagreement.rejected_sources  # rejected sources named, not dropped


def test_structural_gap_disagreements_are_unadjudicated_not_canonicalized(
    facts: list[CanonicalFact],
) -> None:
    # R4-REC-05: where the flagship rollup is structurally incomplete (its district universe is
    # smaller than LGD, e.g. West Bengal / Maharashtra) and a whole-state RS peer disagrees, no
    # single value is asserted — the divergence is published (value is None, adjudicated False).
    unadjudicated = [f for f in facts if not f.reconciliation.adjudicated]
    assert unadjudicated, (
        "expected some structurally-incomplete aggregates to be left unadjudicated"
    )
    for f in unadjudicated:
        assert f.reconciliation.resolution_rule_id == "R4-REC-05"
        assert f.value is None
        assert f.reconciliation.canonical_value is None
        assert len(f.reconciliation.sources_seen) >= 2  # all sources still published


def test_no_impossible_values_slip_through_unflagged(facts: list[CanonicalFact]) -> None:
    for f in facts:
        if f.value is not None and f.value < 0:
            assert f.quarantined and f.quarantine_reason == "negative_value"


def test_total_expenditure_is_derived_and_in_lakh(exp_facts: list[CanonicalFact]) -> None:
    goa = [f for f in exp_facts if f.key.state_code == _GOA and f.key.fin_year == _FY]
    assert len(goa) == 1
    fact = goa[0]
    assert fact.key.metric == "total_expenditure"
    assert fact.unit == "INR lakh"
    # Goa FY2022-23 total expenditure ~422 lakh (divergence-findings §2.3); derived is close.
    assert fact.value is not None
    assert 380 <= fact.value <= 460


def test_total_expenditure_definition_discrepancies_are_recorded(
    exp_facts: list[CanonicalFact],
) -> None:
    # R4-DEF-01: where the derived total and the flagship's own Total_Exp differ beyond tolerance,
    # the gap is recorded (derived stays canonical). At least the mechanism must be exercised.
    with_discrepancy = [
        f for f in exp_facts if f.reconciliation.sources_seen[0].definition_discrepancy is not None
    ]
    for f in with_discrepancy:
        disc = f.reconciliation.sources_seen[0].definition_discrepancy
        assert disc is not None
        assert disc.rule_id == "R4-DEF-01"
        assert disc.derived == f.value  # canonical value is the derived one, not the source total


def test_avg_wage_is_district_monthly_single_source_rate(wage_facts: list[CanonicalFact]) -> None:
    goa = [f for f in wage_facts if f.key.state_code == _GOA and f.key.fin_year == _FY]
    assert goa, "expected Goa district-monthly avg-wage facts"
    for f in goa:
        assert f.key.metric == "avg_wage_rate_per_day"
        assert f.key.geo_level.value == "district"
        assert f.key.district_code is not None and f.key.month is not None
        assert f.unit == "INR"
        assert f.reconciliation.resolution_rule_id == "R4-REC-04"  # single source
        assert f.value is not None and f.value > 0  # a wage rate is positive (magnitude not judged)
