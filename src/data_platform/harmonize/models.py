"""Stage 4 harmonization models — the reconciliation result + its lineage (DATA_CONTRACT §4).

Frozen/strict like every other stage model. A :class:`SourceValue` is one source's value for a
canonical (scheme, geo, period, metric) key, already normalized to the canonical unit and carrying
the authority rank the source-priority rule assigns it. :class:`Reconciliation` is the outcome for
that key: the chosen canonical value, which source won, every source seen (never dropped), and —
when sources disagree beyond tolerance — the recorded :class:`Disagreement`. Divergence is a
first-class output, not a hidden problem (CLAUDE.md harmonization philosophy).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from data_platform.resolve.models import GeoLevel


class _Frozen(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)


class CoverageStatus(StrEnum):
    """Spatial completeness of a value produced by aggregating over a finer grain (R4-REC-05).

    - ``COMPLETE``: every unit the geography has is present in the sum.
    - ``STRUCTURAL_GAP``: the source can NEVER reach the whole geography (its universe < LGD).
    - ``YEAR_GAP``: fewer units than the source's own maximum — missing data OR units created later.
    """

    COMPLETE = "complete"
    STRUCTURAL_GAP = "structural_gap"
    YEAR_GAP = "year_gap"


class AggregateCoverage(_Frozen):
    """How completely an aggregated value covers its geography (for a rolled-up source value).

    Deterministic, computable now: ``units_summed`` this period, ``units_in_source_universe`` the
    distinct units the source ever reports for the geography, ``units_in_lgd`` the current LGD size.
    """

    units_summed: int
    units_in_source_universe: int
    units_in_lgd: int

    @property
    def status(self) -> CoverageStatus:
        if self.units_in_source_universe < self.units_in_lgd:
            return CoverageStatus.STRUCTURAL_GAP
        if self.units_summed < self.units_in_source_universe:
            return CoverageStatus.YEAR_GAP
        return CoverageStatus.COMPLETE


class SourceValue(_Frozen):
    """One source's value for a canonical key, in the canonical unit.

    ``authority_rank`` orders sources by data-production standing FOR THIS period (lower = more
    authoritative; e.g. the primary district-monthly series outranks a downstream state-annual
    summary where it covers the period — DATA_CONTRACT §3). ``original_unit`` records the unit the
    value arrived in before normalization (lineage). ``rounding_epsilon`` is the absolute slack (in
    canonical units) below which a difference from this source is within its own published rounding
    (R4-REC-01a) — 0 for an exact source. ``aggregate_coverage`` is set when the value was rolled up
    from a finer grain, ``None`` for a natively whole-geography value (R4-REC-05).
    """

    source_id: str
    value: Decimal
    original_unit: str
    source_as_of: datetime | None
    authority_rank: int
    rounding_epsilon: Decimal = Decimal(0)
    aggregate_coverage: AggregateCoverage | None = None


class Disagreement(_Frozen):
    """Recorded when sources disagree beyond tolerance and a grounded rule picked the winner.

    ``pct`` is the largest pairwise difference (relative to the winning value) among the sources;
    ``rejected_sources`` are the source ids whose values were not chosen (kept, never discarded);
    ``rule_id`` is the Stage-4 rule that adjudicated.
    """

    pct: Decimal
    rejected_sources: list[str]
    rule_id: str


class Reconciliation(_Frozen):
    """The reconciled outcome for one canonical key.

    ``canonical_value``/``source_id`` are the chosen value and the source it came from — both
    ``None`` when the outcome is UNADJUDICATED (``adjudicated=False``): sources diverge but the
    authoritative source is a structurally-incomplete aggregate, so no single value is asserted and
    the divergence is published instead (R4-REC-05). ``sources_seen`` always lists every source
    (with its value); ``disagreement`` is ``None`` when sources agreed (or only one existed).
    """

    canonical_value: Decimal | None
    source_id: str | None
    sources_seen: list[SourceValue]
    disagreement: Disagreement | None
    resolution_rule_id: str
    adjudicated: bool


class CanonicalKey(_Frozen):
    """The identity of one canonical fact: scheme + geography (at its level) + period + metric.

    ``state_code``/``district_code`` are nullable and follow ``geo_level`` (national → both None;
    state → state set; district → both set), mirroring the resolved-record geography model.
    ``month`` is None for annual-grain facts.
    """

    scheme: str
    geo_level: GeoLevel
    state_code: str | None
    district_code: str | None
    fin_year: str
    month: str | None
    metric: str


class CanonicalFact(_Frozen):
    """One harmonized canonical fact: the reconciled value for a key, its unit, and its lineage.

    ``reconciliation`` carries the cross-source lineage (winning source, all sources seen with
    their values, any recorded disagreement, the rule). ``value`` is ``None`` for an UNADJUDICATED
    fact (divergence published, no single value asserted — R4-REC-05). ``quarantined`` marks a value
    excluded from the golden store by R4-Q-01 (kept queryable) with its typed reason.
    """

    key: CanonicalKey
    value: Decimal | None
    unit: str
    reconciliation: Reconciliation
    quarantined: bool
    quarantine_reason: str | None
