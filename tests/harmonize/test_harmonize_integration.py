"""Stage 4 starter slice, end to end over the real archive — persondays_generated reconciled
across the flagship (district-monthly, rolled up to state-annual) and the two Rajya Sabha
state-annual person-days tables. Skips when the gitignored archive snapshot is absent.

Proves the whole chain: normalize → resolve → extract (rollup / lakh conversion) → assemble →
reconcile, producing canonical state-annual facts whose lineage records agreement or disagreement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.harmonize.assemble import assemble
from data_platform.harmonize.extract import (
    flagship_state_annual_persondays,
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


@pytest.fixture(scope="module")
def facts() -> list[CanonicalFact]:
    resolver = _resolver()
    keyed: list[tuple[CanonicalKey, SourceValue]] = []

    fb = read_archive_batch(
        resource_id=FLAGSHIP_RESOURCE_ID,
        source_id=SRC_FLAGSHIP,
        source_grain="district+monthly",
        path=_FLAGSHIP_FILE,
    )
    fn = normalize_batch(fb, config=NORMALIZE_CONFIG[FLAGSHIP_RESOURCE_ID])
    fr: ResolvedBatch = resolve_batch(fn, resolver, config=RESOLVE_CONFIG[FLAGSHIP_RESOURCE_ID])
    keyed += flagship_state_annual_persondays(fr, _cells(fn), source_as_of=fb.source_as_of)

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
        keyed += rs_state_annual_persondays(rr, _cells(rn), source_as_of=rb.source_as_of)

    return assemble(keyed)


def test_goa_2022_23_reconciles_and_agrees(facts: list[CanonicalFact]) -> None:
    goa = [f for f in facts if f.key.state_code == _GOA and f.key.fin_year == _FY]
    assert len(goa) == 1
    fact = goa[0]
    # Flagship (~94,004) and RS (0.94 lakh = 94,000) agree within 0.5% → R4-REC-01, flagship wins.
    assert fact.reconciliation.resolution_rule_id == "R4-REC-01"
    assert fact.reconciliation.disagreement is None
    assert fact.reconciliation.source_id == SRC_FLAGSHIP
    assert len(fact.reconciliation.sources_seen) >= 2  # corroborated by RS
    assert 93_000 <= fact.value <= 95_000


def test_multi_source_facts_and_recorded_disagreements_both_exist(
    facts: list[CanonicalFact],
) -> None:
    multi = [f for f in facts if len(f.reconciliation.sources_seen) >= 2]
    disagreements = [f for f in facts if f.reconciliation.disagreement is not None]
    assert multi, "expected cross-source (flagship+RS) reconciled facts"
    # The evidence showed a real ~16-20% conflict tail — it must surface as recorded disagreements.
    assert disagreements, "expected some beyond-tolerance disagreements to be recorded"
    for f in disagreements:
        disagreement = f.reconciliation.disagreement
        assert disagreement is not None
        assert disagreement.rejected_sources  # rejected sources named, not dropped


def test_no_impossible_values_slip_through_unflagged(facts: list[CanonicalFact]) -> None:
    for f in facts:
        if f.value < 0:
            assert f.quarantined and f.quarantine_reason == "negative_value"
