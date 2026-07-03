"""Series assembly — the continuous canonical MGNREGA series (FY2006-07 → FY2026-27).

The deliverable a stranger downloads: one authoritative value per (state, financial-year, metric) at
state-annual grain, spanning both eras. Reconciliation (Stage 4) is the TRUST TOOL here, not the
product — this module wraps a reconciled outcome with the two things the series needs on top: the
**basis** (which era/source produced the value — the flagship rolled up for 2018+, or historical
sources for pre-2018) and a **confidence** signal derived from how many sources agreed. All the
underlying lineage (sources seen with ids + as-of, any disagreement, the rule) rides along on the
:class:`Reconciliation`; the flagship's finer district-monthly detail for 2018+ is untouched
beneath, reachable via that lineage.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from data_platform.harmonize.models import CanonicalKey, Reconciliation


class Basis(StrEnum):
    """Which era/source the canonical series value rests on (recorded on every fact)."""

    FLAGSHIP_ROLLUP = "flagship (district-monthly, rolled up)"
    HISTORICAL_MULTI = "historical multi-source"
    HISTORICAL_SINGLE = "historical single-source"


class Confidence(StrEnum):
    """How much cross-source support the value has."""

    CORROBORATED = "corroborated"  # >=2 sources agreed within tolerance
    SINGLE_SOURCE = "single-source"  # only one source carried the fact
    FLAGGED_DISAGREEMENT = "flagged-disagreement"  # sources disagreed; winner taken, rest recorded
    UNADJUDICATED = "unadjudicated"  # sources disagreed and none could be chosen (R4-REC-05)


class SeriesFact(BaseModel):
    """One point in the series: value + basis + confidence + full reconciliation lineage."""

    model_config = ConfigDict(strict=True, frozen=True)

    key: CanonicalKey
    value: Decimal | None
    unit: str
    basis: Basis
    confidence: Confidence
    reconciliation: Reconciliation
    quarantined: bool
    quarantine_reason: str | None


def classify(
    reconciliation: Reconciliation, *, flagship_source_id: str
) -> tuple[Basis, Confidence]:
    """Derive (basis, confidence) from a reconciled outcome — no adjudication, just labelling."""
    has_flagship = any(s.source_id == flagship_source_id for s in reconciliation.sources_seen)
    n = len(reconciliation.sources_seen)

    if has_flagship:
        basis = Basis.FLAGSHIP_ROLLUP  # the flagship anchors this year, even if unadjudicated
    elif n >= 2:
        basis = Basis.HISTORICAL_MULTI
    else:
        basis = Basis.HISTORICAL_SINGLE

    if not reconciliation.adjudicated:
        confidence = Confidence.UNADJUDICATED
    elif reconciliation.disagreement is not None:
        confidence = Confidence.FLAGGED_DISAGREEMENT
    elif n >= 2:
        confidence = Confidence.CORROBORATED
    else:
        confidence = Confidence.SINGLE_SOURCE

    return basis, confidence
