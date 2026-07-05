"""R4-Q-01 — impossible-value guard for canonical facts.

A harmonized value that cannot be real is quarantined with a typed reason (excluded from the golden
store but kept queryable), never silently corrected. Two checks: a single-value one (every canonical
MGNREGA metric is non-negative, so a negative value is impossible) and a CROSS-metric one over the
assembled fact set (person-days for a geography-year cannot exceed active-workers × days-in-year —
each worker can generate at most one person-day per day).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from enum import StrEnum

from data_platform.harmonize.config import ACTIVE_WORKERS, PERSONDAYS_GENERATED
from data_platform.harmonize.models import CanonicalFact, CanonicalKey

# A generous upper bound on days in a financial year (366 covers leap years); used only as an
# impossibility ceiling, so being lenient avoids false positives at the boundary.
_DAYS_IN_FINANCIAL_YEAR = 366


class HarmonizeQuarantineReason(StrEnum):
    """Typed reason a harmonized value is quarantined at Stage 4 (kept + queryable, not dropped)."""

    NEGATIVE_VALUE = "negative_value"  # a metric that cannot be < 0 arrived negative
    IMPLAUSIBLE_PERSONDAYS = "implausible_persondays"  # persondays > active_workers × days-in-year


def impossible_reason(value: Decimal | int | None) -> HarmonizeQuarantineReason | None:
    """Return the quarantine reason for an impossible single value, or ``None`` if admissible.

    ``None`` (a missing value) is not impossible — it is honest absence, handled elsewhere.
    """
    if value is not None and value < 0:
        return HarmonizeQuarantineReason.NEGATIVE_VALUE
    return None


def flag_implausible_persondays(facts: list[CanonicalFact]) -> list[CanonicalFact]:
    """Cross-metric R4-Q-01: quarantine a person-days fact that exceeds the physical ceiling.

    For each geography-period, person-days cannot exceed active_workers × days-in-year. When both
    facts are present and the ceiling is breached, the person-days fact is returned quarantined
    (its value preserved, kept queryable); everything else passes through unchanged.
    """
    by_geo_period: dict[tuple[str, object, str | None, str | None, str], dict[str, CanonicalFact]]
    by_geo_period = defaultdict(dict)
    for fact in facts:
        key = fact.key
        group_key = (key.scheme, key.geo_level, key.state_code, key.district_code, key.fin_year)
        by_geo_period[group_key][key.metric] = fact

    breached: set[CanonicalKey] = set()
    for metrics in by_geo_period.values():
        persondays = metrics.get(PERSONDAYS_GENERATED)
        workers = metrics.get(ACTIVE_WORKERS)
        if (
            persondays is not None
            and workers is not None
            and persondays.value is not None
            and workers.value is not None
            and not persondays.quarantined
            and persondays.value > workers.value * _DAYS_IN_FINANCIAL_YEAR
        ):
            breached.add(persondays.key)

    if not breached:
        return facts
    return [
        fact.model_copy(
            update={
                "quarantined": True,
                "quarantine_reason": HarmonizeQuarantineReason.IMPLAUSIBLE_PERSONDAYS.value,
            }
        )
        if fact.key in breached
        else fact
        for fact in facts
    ]
