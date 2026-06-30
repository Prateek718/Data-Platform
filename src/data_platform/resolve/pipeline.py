"""Stage 3 orchestrator — ``resolve_batch``.

Pure, deterministic transform: a Stage 2 :class:`NormalizedBatch` + an LGD-built
:class:`GeoResolver` in, a :class:`ResolvedBatch` out. Per record, in source order:

1. **R3-SCHEME-01** — resolve the source's scheme label to canonical ``MGNREGA``; unknown →
   quarantine ``unknown_scheme``. (The flagship carries no scheme column, so its declared label
   from config is run through the same rule.)
2. **R3-GEO-02/03** — resolve the state NAME to an LGD state, then the district NAME within that
   state. Flagship MIS codes are never matched directly (DATA_CONTRACT §2.2); they are recorded
   in lineage as the source side of the MIS→LGD translation (R3-GEO-04).
3. **R3-GEO-05** — a state or district that resolves to neither exact nor alias → quarantine
   ``unresolved_geography`` (never a guess), with the row's normalized cells preserved.

Resolved records carry canonical LGD identity only; source names/codes survive solely in the
``geo_resolution`` lineage. ``present_in`` (R3-SET-01) lists the carrying source.
"""

from __future__ import annotations

from data_platform.normalize.models import CleanCell, NormalizedBatch, NormalizedRecord
from data_platform.resolve.aliases import GEO_QUARANTINE_NOTES
from data_platform.resolve.config import SOURCE_GEO_COLUMNS, SOURCE_SCHEME, GeoColumns
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.models import (
    GeoFieldResolution,
    GeoResolution,
    ResolutionQuarantine,
    ResolutionQuarantineReason,
    ResolvedBatch,
    ResolvedRecord,
)
from data_platform.resolve.normalize_name import normalize_geo_name
from data_platform.resolve.scheme import resolve_scheme


def resolve_batch(batch: NormalizedBatch, resolver: GeoResolver) -> ResolvedBatch:
    """Resolve a normalized batch to canonical scheme + geography identity."""
    geo_columns = SOURCE_GEO_COLUMNS.get(batch.source_id)
    scheme_label = SOURCE_SCHEME.get(batch.source_id)
    if geo_columns is None or scheme_label is None:
        raise ValueError(f"no Stage 3 config for source {batch.source_id!r}")

    records: list[ResolvedRecord] = []
    quarantined: list[ResolutionQuarantine] = []
    for record in batch.records:
        resolved, failure = _resolve_record(
            record, resolver, geo_columns, scheme_label, batch.source_id
        )
        if resolved is not None:
            records.append(resolved)
        else:
            assert failure is not None  # exactly one of the two is set
            quarantined.append(failure)

    return ResolvedBatch(
        source_id=batch.source_id,
        resource_id=batch.resource_id,
        ingested_at=batch.ingested_at,
        source_as_of=batch.source_as_of,
        schema_version=batch.schema_version,
        source_grain=batch.source_grain,
        pull_completeness=batch.pull_completeness,
        records=records,
        quarantined=quarantined,
    )


def _resolve_record(
    record: NormalizedRecord,
    resolver: GeoResolver,
    geo_columns: GeoColumns,
    scheme_label: str,
    source_id: str,
) -> tuple[ResolvedRecord | None, ResolutionQuarantine | None]:
    if resolve_scheme(scheme_label) is None:
        return None, _quarantine(
            record, ResolutionQuarantineReason.UNKNOWN_SCHEME, f"scheme:{scheme_label!r}"
        )

    state_name = _as_name(record.cells.get(geo_columns.state_name))
    state = resolver.resolve_state(state_name)
    if state is None:
        return None, _quarantine(
            record, ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY, f"state:{state_name!r}"
        )

    district_name = _as_name(record.cells.get(geo_columns.district_name))
    district = resolver.resolve_district(state.code, district_name)
    if district is None:
        detail = f"district:{district_name!r} in state {state.name}({state.code})"
        note = _quarantine_note(state.code, district_name)
        if note is not None:
            detail = f"{detail} — {note}"
        return None, _quarantine(record, ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY, detail)

    geo_resolution = GeoResolution(
        state=GeoFieldResolution(
            rule_id=state.rule_id,
            source_code=_as_name(record.cells.get(geo_columns.state_code)),
            source_name=state_name,
            lgd_code=state.code,
        ),
        district=GeoFieldResolution(
            rule_id=district.rule_id,
            source_code=_as_name(record.cells.get(geo_columns.district_code)),
            source_name=district_name,
            lgd_code=district.code,
        ),
    )
    resolved = ResolvedRecord(
        row_index=record.row_index,
        scheme_canonical_id="MGNREGA",
        state_canonical_id=state.code,
        state_canonical_name=state.name,
        district_canonical_id=district.code,
        district_canonical_name=district.name,
        geo_resolution=geo_resolution,
        present_in=[source_id],
    )
    return resolved, None


def _as_name(cell: CleanCell) -> str | None:
    """A geography cell is a string identifier or null; any other type is not a usable name."""
    return cell if isinstance(cell, str) else None


def _quarantine_note(lgd_state_code: str, district_name: str | None) -> str | None:
    """Rich, honest description for a known non-resolvable geography (R3-GEO-05), if curated."""
    normalized = normalize_geo_name(district_name)
    if normalized is None:
        return None
    return GEO_QUARANTINE_NOTES.get((lgd_state_code, normalized))


def _quarantine(
    record: NormalizedRecord, reason: ResolutionQuarantineReason, detail: str
) -> ResolutionQuarantine:
    return ResolutionQuarantine(
        row_index=record.row_index, cells=record.cells, reason=reason, detail=detail
    )
