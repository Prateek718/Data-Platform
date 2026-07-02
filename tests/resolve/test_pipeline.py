"""T3.5 — ``resolve_batch`` orchestrator: scheme + geography resolution, lineage, quarantine.

Golden path runs the real Stage 1 → Stage 2 → Stage 3 handoff over the Goa flagship fixture
(flagship MIS state code 10 / district codes 1001-1002 → LGD code 30 / North-South Goa by NAME,
proving the join is name-based, not code-based). Constructed records exercise the alias path and
the R3-GEO-05 / R3-SCHEME-01 quarantine paths and the §4 lineage shape.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from data_platform.ingest.adapters.base import SourcePayload
from data_platform.ingest.adapters.flagship import FlagshipAdapter
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.models import (
    CleanCell,
    DedupeLineage,
    NormalizationLineage,
    NormalizedBatch,
    NormalizedRecord,
)
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import LGDDistrict, LGDState
from data_platform.resolve.models import GeoLevel, ResolutionQuarantineReason
from data_platform.resolve.pipeline import resolve_batch

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

# LGD slice covering every case the tests touch.
_STATES = [
    LGDState(code="30", name="Goa"),
    LGDState(code="29", name="Karnataka"),
]
_DISTRICTS = [
    LGDDistrict(state_code="30", code="350", name="North Goa"),
    LGDDistrict(state_code="30", code="351", name="South Goa"),
    LGDDistrict(state_code="29", code="540", name="Bengaluru Urban"),
]
_RESOLVER = GeoResolver.from_reference(states=_STATES, districts=_DISTRICTS)


def _flagship_normalized() -> NormalizedBatch:
    env = json.loads((FIXTURES / "flagship/goa_2022_2023.json").read_text())
    payload = SourcePayload(
        resource_id=FLAGSHIP_RESOURCE_ID,
        fetched_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        source_as_of=datetime.fromisoformat(env["updated_date"]),
        raw=env,
    )
    return normalize_batch(FlagshipAdapter().parse(payload))


def _batch_of(*records: NormalizedRecord) -> NormalizedBatch:
    """Wrap constructed normalized records in a minimal flagship batch."""
    return NormalizedBatch(
        source_id=SRC_FLAGSHIP,
        resource_id=FLAGSHIP_RESOURCE_ID,
        ingested_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        source_as_of=None,
        schema_version="v1",
        source_grain="district+monthly",
        pull_completeness="full",
        column_names=["state_code", "state_name", "district_code", "district_name"],
        records=list(records),
        quarantined=[],
        dedupe=DedupeLineage(
            duplicates_collapsed=0, collapsed_row_indexes=[], tie_break_rule_id="x"
        ),
    )


def _record(row_index: int, **cells: CleanCell) -> NormalizedRecord:
    return NormalizedRecord(
        row_index=row_index, cells=cells, normalization=NormalizationLineage(per_column={})
    )


def test_golden_goa_resolves_by_name_not_code() -> None:
    out = resolve_batch(_flagship_normalized(), _RESOLVER)
    assert out.source_id == SRC_FLAGSHIP
    assert out.source_grain == "district+monthly"
    assert out.quarantined == []
    # All Goa rows resolve to LGD state 30 (flagship MIS code was 10) and North/South Goa.
    assert {r.state_canonical_id for r in out.records} == {"30"}
    assert {r.district_canonical_name for r in out.records} == {"North Goa", "South Goa"}
    rec = out.records[0]
    assert rec.scheme_canonical_id == "MGNREGA"
    # District grain: geo_level is district and this is a single-source fact.
    assert rec.geo_level is GeoLevel.DISTRICT
    assert rec.sources_seen == 1
    assert rec.geo_resolution is not None
    assert rec.geo_resolution.district is not None
    # §2.2: source name is an input alias, dropped from identity but kept in lineage.
    assert rec.geo_resolution.state.source_name == "GOA"
    # R3-GEO-04: the MIS→LGD code translation is recorded (10 → 30).
    assert rec.geo_resolution.state.source_code == "10"
    assert rec.geo_resolution.state.lgd_code == "30"
    assert rec.geo_resolution.state.rule_id == "R3-GEO-02"
    assert rec.geo_resolution.district.rule_id == "R3-GEO-02"
    # R3-SET-01: present_in carries the source.
    assert rec.present_in == [SRC_FLAGSHIP]


def test_alias_district_resolution_records_r3_geo_03() -> None:
    batch = _batch_of(
        _record(
            0,
            state_code="15",
            state_name="KARNATAKA",
            district_code="2901",
            district_name="BENGALURU",
        )
    )
    out = resolve_batch(batch, _RESOLVER)
    assert len(out.records) == 1
    rec = out.records[0]
    assert rec.district_canonical_name == "Bengaluru Urban"
    assert rec.geo_resolution is not None
    assert rec.geo_resolution.district is not None
    assert rec.geo_resolution.district.rule_id.startswith("R3-GEO-03")
    assert rec.geo_resolution.district.source_code == "2901"
    assert rec.geo_resolution.district.lgd_code == "540"


def test_unresolved_district_is_quarantined() -> None:
    batch = _batch_of(
        _record(
            0,
            state_code="15",
            state_name="KARNATAKA",
            district_code="9999",
            district_name="BENGALURU SOUTH",
        )
    )
    out = resolve_batch(batch, _RESOLVER)
    assert out.records == []
    assert len(out.quarantined) == 1
    q = out.quarantined[0]
    assert q.reason is ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY
    assert q.row_index == 0
    assert q.cells["district_name"] == "BENGALURU SOUTH"  # preserved, queryable


def test_unresolved_state_is_quarantined() -> None:
    batch = _batch_of(
        _record(0, state_code=None, state_name=None, district_code=None, district_name=None)
    )
    out = resolve_batch(batch, _RESOLVER)
    assert out.records == []
    assert out.quarantined[0].reason is ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY
