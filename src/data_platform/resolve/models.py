"""Stage 3 resolution result models.

Small, frozen, strict — like the Stage 1/2 models. A :class:`GeoMatch` is the outcome of
resolving ONE geography field (state or district) to its canonical LGD identity, carrying the
rule id that established it (for the ``geo_resolution`` lineage field, DATA_CONTRACT §4). Richer
record/lineage/quarantine models are added when the batch pipeline lands (T3.5).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from data_platform.ingest.landing import PullCompleteness
from data_platform.normalize.models import CleanCell


class _Frozen(BaseModel):
    """Base for Stage 3 models: immutable and strict (no coercion at the boundary)."""

    model_config = ConfigDict(strict=True, frozen=True)


class GeoLevel(StrEnum):
    """The geographic aggregation level of a resolved fact (a ragged hierarchy).

    MGNREGA facts are published at three depths of one hierarchy — national ⊃ state ⊃ district,
    all measuring the same metric set. A single :class:`ResolvedRecord` carries this level with the
    finer keys nulled at coarser levels (DATA_CONTRACT §1 grain: geography is nullable *fields* on a
    row, not a type). ``NATIONAL`` rows carry NO LGD code — none exists (LGD starts at state);
    that absence is honest ``None``, never a sentinel (R3-GEO-04).
    """

    NATIONAL = "national"
    STATE = "state"
    DISTRICT = "district"


class GeoMatch(_Frozen):
    """A geography field resolved to canonical LGD identity, with the rule that did it.

    ``rule_id`` is ``"R3-GEO-02"`` for an exact normalized-name match, or
    ``"R3-GEO-03:<normalized-source-name>"`` when the curated alias table resolved it.
    """

    code: str
    name: str
    rule_id: str


class GeoFieldResolution(_Frozen):
    """How ONE geography field (state or district) was canonicalized — the §4 audit unit.

    Records the rule that fired, the source's verbatim input alias + MIS code (preserved in
    lineage though dropped from the golden record, DATA_CONTRACT §2.2), and the LGD code they
    were translated to. The ``source_code → lgd_code`` pair IS the per-source MIS→LGD translation
    R3-GEO-04 requires be recorded in ``geo_resolution``.
    """

    rule_id: str
    source_code: str | None
    source_name: str | None
    lgd_code: str


class GeoResolution(_Frozen):
    """The ``geo_resolution`` lineage field (DATA_CONTRACT §4): state + (optional) district.

    ``district`` is ``None`` for a state-grain fact (state resolved, no district present); the whole
    ``geo_resolution`` is ``None`` on a national-grain fact (no geography resolved at all).
    """

    state: GeoFieldResolution
    district: GeoFieldResolution | None = None


class ResolvedRecord(_Frozen):
    """One source row resolved to canonical scheme + geography identity (LGD codes/names).

    Geography is nullable *fields* keyed by ``geo_level`` (a ragged hierarchy, DATA_CONTRACT §1),
    not a per-grain type: national → state/district both ``None`` (no LGD code exists — honest
    ``None``, never a sentinel); state → state set, district ``None``; district → both set. Source
    names/codes are dropped from this golden identity (kept only in ``geo_resolution``).

    ``present_in`` (R3-SET-01) lists the sources carrying this geography; ``sources_seen`` is the
    peer count Stage-4 reconciliation keys on — ``1`` here (each batch is one source), and it is
    driven by peer count ALONE, never by a source's A/B destination label (which would leak a
    descriptive classification into reconciliation behaviour).
    """

    row_index: int
    scheme_canonical_id: str
    geo_level: GeoLevel
    state_canonical_id: str | None
    state_canonical_name: str | None
    district_canonical_id: str | None
    district_canonical_name: str | None
    geo_resolution: GeoResolution | None
    present_in: list[str]
    sources_seen: int


class ResolutionQuarantineReason(StrEnum):
    """Typed reason a row is quarantined in Stage 3 (kept + queryable, never silently dropped)."""

    UNKNOWN_SCHEME = "unknown_scheme"  # R3-SCHEME-01
    UNRESOLVED_GEOGRAPHY = "unresolved_geography"  # R3-GEO-05
    # A geography absent from the CURRENT LGD snapshot because it predates it (a district/state
    # that existed in a historical period but was since renamed, split, or merged away). Distinct
    # from UNRESOLVED_GEOGRAPHY so coverage/trust reporting reads as "predates today's LGD", not a
    # data bug or a generic miss. The current-only LGD reference cannot date-resolve it (validity
    # dates are deferred to the store layer), so it is quarantined honestly rather than forced onto
    # a current successor — which would misattribute an old aggregate (R3-SET-02 never-forward-map).
    HISTORICAL_GEOGRAPHY_NOT_IN_CURRENT_LGD = "historical_geography_not_in_current_lgd"


class ResolutionQuarantine(_Frozen):
    """A row Stage 3 could not resolve, preserved with its normalized cells and a typed reason."""

    row_index: int
    cells: dict[str, CleanCell]
    reason: ResolutionQuarantineReason
    detail: str


class ResolvedBatch(_Frozen):
    """Stage 3 output for one batch: provenance carried from Stage 2 + resolved + quarantined."""

    source_id: str
    resource_id: str
    ingested_at: datetime
    source_as_of: datetime | None
    schema_version: str
    source_grain: str
    pull_completeness: PullCompleteness
    records: list[ResolvedRecord]
    quarantined: list[ResolutionQuarantine]
