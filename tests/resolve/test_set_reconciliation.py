"""R3-SET-01 / R3-SET-02 — district-set reconciliation invariants (guarding tests).

These pin the LOCKED behaviour rather than new logic — the guarantees emerge from name-based
resolution + R3-GEO-05 quarantine, and must stay true:

* **R3-SET-01** — a district that resolves is kept (with ``present_in``); a district is
  quarantined ONLY when it cannot be geo-resolved at all, never merely because it is absent from
  some other source.
* **R3-SET-02 (keep-both-with-validity)** — split successors resolve to SEPARATE LGD identities
  (never merged into one), and a record naming a geography absent from the current LGD snapshot is
  quarantined (never forward-mapped onto a successor — that would fabricate an allocation).

The ``valid_from``/``valid_to`` validity DATES are out of scope for v1: the archived LGD reference
is a current snapshot with no split-date columns, so populating real dates would be invention
(TIER-1). The rule's integrity requirement — never merge, never forward-map — is enforced
structurally and is what these tests guard.
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

# Two LGD successor districts in one state (the "kept-both" target of a split).
_RESOLVER = GeoResolver.from_reference(
    states=[LGDState(code="29", name="Karnataka")],
    districts=[
        LGDDistrict(state_code="29", code="540", name="Bengaluru Urban"),
        LGDDistrict(state_code="29", code="541", name="Bengaluru Rural"),
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


def test_set02_successors_resolve_to_separate_identities_never_merged() -> None:
    out = resolve_batch(
        _batch(
            _record(0, state_name="KARNATAKA", district_name="BENGALURU"),  # -> Urban (alias)
            _record(1, state_name="KARNATAKA", district_name="BENGALURU RURAL"),  # -> Rural (exact)
        ),
        _RESOLVER,
    )
    assert out.quarantined == []
    ids = {r.district_canonical_id for r in out.records}
    # Two distinct LGD identities — the split is kept-both, never collapsed to one.
    assert ids == {"540", "541"}
    assert len(out.records) == 2


def test_set02_geography_absent_from_lgd_is_quarantined_not_forward_mapped() -> None:
    out = resolve_batch(
        _batch(_record(0, state_name="KARNATAKA", district_name="BENGALURU SOUTH")),
        _RESOLVER,
    )
    # Never silently mapped onto an existing successor (no fabricated allocation).
    assert out.records == []
    assert out.quarantined[0].reason is ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY


def test_set01_resolved_district_is_kept_with_present_in() -> None:
    out = resolve_batch(
        _batch(_record(0, state_name="KARNATAKA", district_name="BENGALURU RURAL")),
        _RESOLVER,
    )
    assert len(out.records) == 1
    assert out.records[0].present_in == [SRC_FLAGSHIP]
