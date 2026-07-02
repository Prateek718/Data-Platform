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

from pydantic import BaseModel, ConfigDict

from data_platform.resolve.models import GeoLevel


class _Frozen(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)


class SourceValue(_Frozen):
    """One source's value for a canonical key, in the canonical unit.

    ``authority_rank`` orders sources by data-production standing FOR THIS period (lower = more
    authoritative; e.g. the primary district-monthly series outranks a downstream state-annual
    summary where it covers the period — DATA_CONTRACT §3). ``original_unit`` records the unit the
    value arrived in before normalization (lineage).
    """

    source_id: str
    value: Decimal
    original_unit: str
    source_as_of: datetime | None
    authority_rank: int


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

    ``canonical_value``/``source_id`` are the chosen value and the source it came from;
    ``sources_seen`` lists every source that carried the fact (with its value) so the count and the
    spread are auditable; ``disagreement`` is ``None`` when sources agreed (or only one existed);
    ``resolution_rule_id`` is the rule that produced the outcome.
    """

    canonical_value: Decimal
    source_id: str
    sources_seen: list[SourceValue]
    disagreement: Disagreement | None
    resolution_rule_id: str


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
    their values, any recorded disagreement, the rule). ``quarantined`` marks a value excluded from
    the golden store by R4-Q-01 (kept queryable) with its typed reason.
    """

    key: CanonicalKey
    value: Decimal
    unit: str
    reconciliation: Reconciliation
    quarantined: bool
    quarantine_reason: str | None
