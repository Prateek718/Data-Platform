"""R4-UNIT-01 — money unit normalization to the canonical INR lakh.

Cross-source expenditure fields arrive in different scales (rupees, thousands, lakh, crore); to be
comparable they are all converted to one canonical unit — **INR lakh** (1 lakh = 100,000 rupees).
Pure and exact (``Decimal``, no float): the original unit and the conversion are recorded in
lineage so nothing is silently rescaled. A source unit the platform does not recognize is NOT
guessed — the caller quarantines it (never invent a unit the source does not support).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import NamedTuple


class MoneyUnit(StrEnum):
    """A declared money scale. ``LAKH`` is canonical; the rest convert into it."""

    RUPEE = "rupee"
    THOUSAND = "thousand"
    LAKH = "lakh"
    CRORE = "crore"


CANONICAL_MONEY_UNIT = MoneyUnit.LAKH

# Rupees in one of each unit — the exact conversion basis (1 lakh = 1e5, 1 crore = 1e7).
_RUPEES_PER_UNIT: dict[MoneyUnit, Decimal] = {
    MoneyUnit.RUPEE: Decimal(1),
    MoneyUnit.THOUSAND: Decimal(1_000),
    MoneyUnit.LAKH: Decimal(100_000),
    MoneyUnit.CRORE: Decimal(10_000_000),
}
_RUPEES_PER_LAKH = _RUPEES_PER_UNIT[MoneyUnit.LAKH]


class MoneyOutcome(NamedTuple):
    """The value in canonical lakh, the original unit (for lineage), and a conversion note."""

    value_lakh: Decimal | None
    original_unit: str
    note: str | None


def to_canonical_lakh(value: Decimal | None, source_unit: MoneyUnit) -> MoneyOutcome:
    """Convert a money value from its declared unit to canonical INR lakh.

    ``None`` (a missing value) passes through as ``None`` — null is never coerced to zero. The
    ``note`` is set only when a real conversion happened (an already-lakh value is unchanged).
    """
    if value is None:
        return MoneyOutcome(None, source_unit.value, None)
    value_lakh = value * _RUPEES_PER_UNIT[source_unit] / _RUPEES_PER_LAKH
    note = None if source_unit is CANONICAL_MONEY_UNIT else f"R4-UNIT-01:{source_unit.value}→lakh"
    return MoneyOutcome(value_lakh, source_unit.value, note)
