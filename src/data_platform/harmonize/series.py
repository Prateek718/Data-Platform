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

from data_platform.harmonize.assemble import assemble
from data_platform.harmonize.models import CanonicalFact, CanonicalKey, Reconciliation, SourceValue
from data_platform.harmonize.validate import flag_implausible_persondays


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


def to_series_fact(fact: CanonicalFact, *, flagship_source_id: str) -> SeriesFact:
    """Wrap a reconciled canonical fact as a series point, adding its basis + confidence label."""
    basis, confidence = classify(fact.reconciliation, flagship_source_id=flagship_source_id)
    return SeriesFact(
        key=fact.key,
        value=fact.value,
        unit=fact.unit,
        basis=basis,
        confidence=confidence,
        reconciliation=fact.reconciliation,
        quarantined=fact.quarantined,
        quarantine_reason=fact.quarantine_reason,
    )


def assemble_series(
    keyed_values: list[tuple[CanonicalKey, SourceValue]], *, flagship_source_id: str
) -> list[SeriesFact]:
    """Assemble the continuous series: reconcile every source per key (Stage-4 engine), apply the
    cross-metric person-days guard, then label each with basis + confidence. Era policy is carried
    entirely by the ``authority_rank`` on the input source values — flagship 0, historical higher —
    so 2018+ keys resolve to the flagship and pre-2018 keys to the agreeing historical sources."""
    facts = flag_implausible_persondays(assemble(keyed_values))
    return [to_series_fact(fact, flagship_source_id=flagship_source_id) for fact in facts]


def series_coverage_summary(facts: list[SeriesFact]) -> dict[str, dict[str, int]]:
    """Per-metric coverage counts for the assembly summary: how many state-years fall pre-2018 vs
    2018+, and the confidence mix (corroborated / single-source / flagged / unadjudicated) + how
    many were quarantined. Honest gaps are simply the (metric, era) cells that never appear."""
    _CONF = {
        Confidence.CORROBORATED: "corroborated",
        Confidence.SINGLE_SOURCE: "single_source",
        Confidence.FLAGGED_DISAGREEMENT: "flagged_disagreement",
        Confidence.UNADJUDICATED: "unadjudicated",
    }
    summary: dict[str, dict[str, int]] = {}
    for fact in facts:
        row = summary.setdefault(
            fact.key.metric,
            {
                "pre_2018": 0,
                "y2018_plus": 0,
                "corroborated": 0,
                "single_source": 0,
                "flagged_disagreement": 0,
                "unadjudicated": 0,
                "quarantined": 0,
            },
        )
        row["pre_2018" if fact.key.fin_year < "2018" else "y2018_plus"] += 1
        row[_CONF[fact.confidence]] += 1
        if fact.quarantined:
            row["quarantined"] += 1
    return summary
