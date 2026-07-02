"""Stage 3 orchestrator — ``resolve_batch``.

Pure, deterministic transform: a Stage 2 :class:`NormalizedBatch` + an LGD-built
:class:`GeoResolver` in, a :class:`ResolvedBatch` out. Config is per-resource (keyed by
``resource_id``), and the geographic grain drives dispatch — a ragged hierarchy resolved at the
level the resource publishes:

1. **R3-SCHEME-01** — resolve the source's scheme label to canonical ``MGNREGA`` for every grain;
   unknown → quarantine ``unknown_scheme``. (Sources carry no scheme column; the declared label
   from config is run through the same rule.)
2. **grain dispatch** —
   * ``NATIONAL``: no geography exists to resolve (LGD starts at state); the record is filed with
     ``geo_level=national`` and NO LGD code — an honest ``None``, never a sentinel (R3-GEO-04).
   * ``STATE``: resolve the state NAME to an LGD state (R3-GEO-02/03); district stays ``None``.
   * ``DISTRICT``: resolve state, then district within it. Source codes are never matched directly
     (DATA_CONTRACT §2.2); they are recorded in lineage as the source side of MIS→LGD (R3-GEO-04).
3. **R3-GEO-05** — a state/district that resolves to neither exact nor alias → quarantine
   ``unresolved_geography`` (never a guess), with the row's normalized cells preserved.

Resolved records carry canonical LGD identity only; source names/codes survive solely in the
``geo_resolution`` lineage. ``present_in`` (R3-SET-01) lists the carrying source and
``sources_seen`` the peer count (``1`` per single-source batch) that Stage-4 reconciliation keys on.
"""

from __future__ import annotations

import re

from data_platform.normalize.models import CleanCell, NormalizedBatch, NormalizedRecord
from data_platform.resolve.aliases import (
    GEO_QUARANTINE_NOTES,
    HISTORICAL_DISTRICT_GEOGRAPHIES,
    HISTORICAL_STATE_GEOGRAPHIES,
    MERGED_UT_NORMALIZED,
    MERGER_FLOOR_FY_START,
)
from data_platform.resolve.config import RESOLVE_CONFIG, ResourceResolveConfig
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.models import (
    GeoFieldResolution,
    GeoLevel,
    GeoMatch,
    GeoResolution,
    ResolutionQuarantine,
    ResolutionQuarantineReason,
    ResolvedBatch,
    ResolvedRecord,
)
from data_platform.resolve.normalize_name import normalize_geo_name
from data_platform.resolve.scheme import resolve_scheme


def resolve_batch(
    batch: NormalizedBatch,
    resolver: GeoResolver,
    config: ResourceResolveConfig | None = None,
) -> ResolvedBatch:
    """Resolve a normalized batch to canonical scheme + geography identity at its grain.

    ``config`` defaults to the per-resource entry looked up by ``batch.resource_id``; it may be
    passed explicitly (dependency injection, like ``resolver``) to resolve a resource whose config
    is supplied by the caller rather than the shared registry.
    """
    if config is None:
        config = RESOLVE_CONFIG.get(batch.resource_id)
    if config is None:
        raise ValueError(f"no Stage 3 config for resource {batch.resource_id!r}")

    records: list[ResolvedRecord] = []
    quarantined: list[ResolutionQuarantine] = []
    for record in batch.records:
        resolved, failure = _resolve_record(record, resolver, config, batch.source_id)
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
    config: ResourceResolveConfig,
    source_id: str,
) -> tuple[ResolvedRecord | None, ResolutionQuarantine | None]:
    if resolve_scheme(config.scheme_label) is None:
        return None, _quarantine(
            record, ResolutionQuarantineReason.UNKNOWN_SCHEME, f"scheme:{config.scheme_label!r}"
        )

    if config.geo_level is GeoLevel.NATIONAL:
        return _national_record(record, source_id), None
    return _geo_anchored_record(record, resolver, config, source_id)


def _national_record(record: NormalizedRecord, source_id: str) -> ResolvedRecord:
    """A national-grain fact: no geography to resolve, so no LGD code (honest None, no sentinel)."""
    return ResolvedRecord(
        row_index=record.row_index,
        scheme_canonical_id="MGNREGA",
        geo_level=GeoLevel.NATIONAL,
        state_canonical_id=None,
        state_canonical_name=None,
        district_canonical_id=None,
        district_canonical_name=None,
        geo_resolution=None,
        present_in=[source_id],
        sources_seen=1,
    )


def _geo_anchored_record(
    record: NormalizedRecord,
    resolver: GeoResolver,
    config: ResourceResolveConfig,
    source_id: str,
) -> tuple[ResolvedRecord | None, ResolutionQuarantine | None]:
    geo_columns = config.geo_columns
    assert geo_columns is not None  # guaranteed by ResourceResolveConfig for non-national grain

    state_name = _as_name(record.cells.get(geo_columns.state_name))
    state = resolver.resolve_state(state_name)
    if state is None:
        historical = HISTORICAL_STATE_GEOGRAPHIES.get(normalize_geo_name(state_name) or "")
        if historical is not None:
            reason = ResolutionQuarantineReason.HISTORICAL_GEOGRAPHY_NOT_IN_CURRENT_LGD
            return None, _quarantine(record, reason, f"state:{state_name!r} — {historical}")
        return None, _quarantine(
            record, ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY, f"state:{state_name!r}"
        )

    # Period gate for the merged UT: its name only became a real entity at the 2020 merger, so a
    # merged-name row dated before the floor is an anachronism — held, not resolved onto LGD 38.
    if normalize_geo_name(state_name) == MERGED_UT_NORMALIZED:
        fy_start = _period_start_year(record)
        if fy_start is None or fy_start < MERGER_FLOOR_FY_START:
            reason = ResolutionQuarantineReason.HISTORICAL_GEOGRAPHY_NOT_IN_CURRENT_LGD
            detail = (
                f"state:{state_name!r} — merged-UT name on a pre-merger period "
                f"(fin_year start {fy_start}); the merged UT did not exist before FY2019-20"
            )
            return None, _quarantine(record, reason, detail)

    state_field = GeoFieldResolution(
        rule_id=state.rule_id,
        source_code=_cell_name(record, geo_columns.state_code),
        source_name=state_name,
        lgd_code=state.code,
    )

    if config.geo_level is GeoLevel.STATE:
        return (
            _resolved(
                record,
                GeoLevel.STATE,
                state,
                district=None,
                geo_resolution=GeoResolution(state=state_field, district=None),
                source_id=source_id,
            ),
            None,
        )

    # DISTRICT grain.
    district_name = _cell_name(record, geo_columns.district_name)
    district = resolver.resolve_district(state.code, district_name)
    if district is None:
        detail = f"district:{district_name!r} in state {state.name}({state.code})"
        historical = HISTORICAL_DISTRICT_GEOGRAPHIES.get(
            (state.code, normalize_geo_name(district_name) or "")
        )
        if historical is not None:
            reason = ResolutionQuarantineReason.HISTORICAL_GEOGRAPHY_NOT_IN_CURRENT_LGD
            return None, _quarantine(record, reason, f"{detail} — {historical}")
        note = _quarantine_note(state.code, district_name)
        if note is not None:
            detail = f"{detail} — {note}"
        return None, _quarantine(record, ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY, detail)

    district_field = GeoFieldResolution(
        rule_id=district.rule_id,
        source_code=_cell_name(record, geo_columns.district_code),
        source_name=district_name,
        lgd_code=district.code,
    )
    return (
        _resolved(
            record,
            GeoLevel.DISTRICT,
            state,
            district=district,
            geo_resolution=GeoResolution(state=state_field, district=district_field),
            source_id=source_id,
        ),
        None,
    )


def _resolved(
    record: NormalizedRecord,
    geo_level: GeoLevel,
    state: GeoMatch,
    *,
    district: GeoMatch | None,
    geo_resolution: GeoResolution,
    source_id: str,
) -> ResolvedRecord:
    return ResolvedRecord(
        row_index=record.row_index,
        scheme_canonical_id="MGNREGA",
        geo_level=geo_level,
        state_canonical_id=state.code,
        state_canonical_name=state.name,
        district_canonical_id=district.code if district is not None else None,
        district_canonical_name=district.name if district is not None else None,
        geo_resolution=geo_resolution,
        present_in=[source_id],
        sources_seen=1,
    )


def _cell_name(record: NormalizedRecord, column: str | None) -> str | None:
    """The string value of an optional geo column, or None when absent/unconfigured."""
    if column is None:
        return None
    return _as_name(record.cells.get(column))


def _as_name(cell: CleanCell) -> str | None:
    """A geography cell is a string identifier or null; any other type is not a usable name."""
    return cell if isinstance(cell, str) else None


def _period_start_year(record: NormalizedRecord) -> int | None:
    """The starting calendar year of the row's financial year (``2019-20`` → ``2019``), or None.

    Read from the synthesized ``_fin_year`` column (present on every reshaped/period-injected
    resource). Used only by the merged-UT period gate; absence is treated as unknown → held.
    """
    value = record.cells.get("_fin_year")
    if not isinstance(value, str):
        return None
    match = re.match(r"(\d{4})", value)
    return int(match.group(1)) if match is not None else None


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
