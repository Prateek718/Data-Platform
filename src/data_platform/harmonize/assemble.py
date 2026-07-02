"""Assemble per-source values into reconciled canonical facts.

The cross-source core: given every source's value tagged with the canonical key it belongs to,
group by key, run R4-REC reconciliation over each group, and emit a :class:`CanonicalFact` — the
reconciled value, its canonical unit, the full reconciliation lineage, and an R4-Q-01 quarantine
flag for an impossible (negative) value. Source-specific EXTRACTION (rolling the flagship up to
state-annual, converting RS lakh to raw person-days) lives in the extractor functions that feed
this; this function is source-agnostic.
"""

from __future__ import annotations

from collections import defaultdict

from data_platform.harmonize.config import CANONICAL_UNIT
from data_platform.harmonize.models import CanonicalFact, CanonicalKey, SourceValue
from data_platform.harmonize.reconcile import reconcile
from data_platform.harmonize.validate import impossible_reason


def assemble(keyed_values: list[tuple[CanonicalKey, SourceValue]]) -> list[CanonicalFact]:
    """Group per-source values by canonical key, reconcile each, and build canonical facts."""
    groups: dict[CanonicalKey, list[SourceValue]] = defaultdict(list)
    for key, value in keyed_values:
        groups[key].append(value)

    facts: list[CanonicalFact] = []
    for key, values in groups.items():
        result = reconcile(values, metric=key.metric)
        if result is None:  # no values for this key — nothing to assemble
            continue
        reason = impossible_reason(result.canonical_value)
        facts.append(
            CanonicalFact(
                key=key,
                value=result.canonical_value,
                unit=CANONICAL_UNIT[key.metric],
                reconciliation=result,
                quarantined=reason is not None,
                quarantine_reason=reason.value if reason is not None else None,
            )
        )
    return facts
