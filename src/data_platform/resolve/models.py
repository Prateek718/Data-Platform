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
    """The ``geo_resolution`` lineage field (DATA_CONTRACT §4): state + district resolution."""

    state: GeoFieldResolution
    district: GeoFieldResolution


class ResolvedRecord(_Frozen):
    """One source row resolved to canonical scheme + geography identity (LGD codes/names).

    Source names/codes are dropped from this golden identity (kept only in ``geo_resolution``).
    ``present_in`` (R3-SET-01) lists the sources carrying this geography — a single entry while
    only the flagship is wired, extended cross-source in Stage 4.
    """

    row_index: int
    scheme_canonical_id: str
    state_canonical_id: str
    state_canonical_name: str
    district_canonical_id: str
    district_canonical_name: str
    geo_resolution: GeoResolution
    present_in: list[str]


class ResolutionQuarantineReason(StrEnum):
    """Typed reason a row is quarantined in Stage 3 (kept + queryable, never silently dropped)."""

    UNKNOWN_SCHEME = "unknown_scheme"  # R3-SCHEME-01
    UNRESOLVED_GEOGRAPHY = "unresolved_geography"  # R3-GEO-05


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
