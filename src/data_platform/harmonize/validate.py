"""R4-Q-01 — impossible-value guard for canonical facts.

A harmonized value that cannot be real is quarantined with a typed reason (excluded from the golden
store but kept queryable), never silently corrected. Every canonical MGNREGA metric — person-days,
counts, wage rate, expenditure — is non-negative, so a negative value is impossible. (The
cross-metric plausibility check, persondays ≤ active-workers × days-in-period, needs the assembled
metric set for a key and is applied during fact assembly, not here.)
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class HarmonizeQuarantineReason(StrEnum):
    """Typed reason a harmonized value is quarantined at Stage 4 (kept + queryable, not dropped)."""

    NEGATIVE_VALUE = "negative_value"  # a metric that cannot be < 0 arrived negative


def impossible_reason(value: Decimal | int | None) -> HarmonizeQuarantineReason | None:
    """Return the quarantine reason for an impossible value, or ``None`` if it is admissible.

    ``None`` (a missing value) is not impossible — it is honest absence, handled elsewhere.
    """
    if value is not None and value < 0:
        return HarmonizeQuarantineReason.NEGATIVE_VALUE
    return None
