"""Rich quarantine detail for known sub-district / non-LGD geographies (no unique data lost).

Some flagship labels cannot resolve to an LGD district AND must not be aliased to one — a
sub-district administrative fragment (e.g. the Darjeeling Gorkha Hill Council, only PART of LGD
Darjeeling) resolved as the whole district would under-count, and summing fragments would
fabricate a total the source never published. R3-GEO-05 quarantine is therefore correct, but the
detail must be HONEST and specific: name the entity and which LGD district it fragments, so the
rows stay presented and queryable rather than buried behind a generic message.

Investigated fact this guards: in the flagship archive, Darjeeling district is published only as
two sub-district fragments — DGHC/GTA (hill subdivisions) and Siliguri Mahakuma Parisad (plains) —
while Kalimpong is published cleanly under its own name and DOES resolve. GTA is never the sole
carrier of the region, and there is no clean district-grain Darjeeling row to recover.
"""

from __future__ import annotations

from datetime import UTC, datetime

from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.models import (
    CleanCell,
    DedupeLineage,
    NormalizationLineage,
    NormalizedBatch,
    NormalizedRecord,
)
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import LGDDistrict, LGDState
from data_platform.resolve.models import ResolutionQuarantineReason
from data_platform.resolve.pipeline import resolve_batch

_RESOLVER = GeoResolver.from_reference(
    states=[LGDState(code="19", name="West Bengal")],
    districts=[
        LGDDistrict(state_code="19", code="701", name="Darjeeling"),
        LGDDistrict(state_code="19", code="702", name="Kalimpong"),
    ],
)


def _record(row_index: int, **cells: CleanCell) -> NormalizedRecord:
    return NormalizedRecord(
        row_index=row_index, cells=cells, normalization=NormalizationLineage(per_column={})
    )


def _batch(*records: NormalizedRecord) -> NormalizedBatch:
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


def _quarantine_for(district_name: str) -> str:
    out = resolve_batch(
        _batch(_record(0, state_name="WEST BENGAL", district_name=district_name)), _RESOLVER
    )
    assert out.records == []
    assert len(out.quarantined) == 1
    q = out.quarantined[0]
    assert q.reason is ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY
    return q.detail


def test_dghc_quarantine_detail_is_honest_and_specific() -> None:
    detail = _quarantine_for("Darjeeling Gorkha Hill Council (DGHC)")
    assert "Darjeeling Gorkha Hill Council (DGHC)" in detail  # the verbatim source label
    assert "Darjeeling" in detail  # the LGD district it fragments
    assert "sub-district" in detail
    assert "Siliguri" in detail  # names the sibling fragment so the split is explicit


def test_gta_quarantine_detail_names_successor_relationship() -> None:
    detail = _quarantine_for("GORKHALAND TERRITORIAL ADMINISTRATION (GTA)")
    assert "Darjeeling" in detail
    assert "DGHC" in detail  # GTA is the successor body to DGHC (same flagship unit)


def test_siliguri_quarantine_detail_names_parent_district() -> None:
    detail = _quarantine_for("SILIGURI MAHAKUMA PARISAD")
    assert "Darjeeling" in detail
    assert "sub-district" in detail


def test_kalimpong_resolves_and_is_not_quarantined() -> None:
    out = resolve_batch(
        _batch(_record(0, state_name="WEST BENGAL", district_name="KALIMPONG")), _RESOLVER
    )
    assert out.quarantined == []
    assert out.records[0].district_canonical_name == "Kalimpong"


def test_unknown_geography_keeps_generic_detail() -> None:
    # A label with no curated note still quarantines, with a generic (non-empty) detail.
    detail = _quarantine_for("SOMEPLACE THAT DOES NOT EXIST")
    assert "SOMEPLACE THAT DOES NOT EXIST" in detail
    assert "West Bengal" in detail
