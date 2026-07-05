"""R4-UNIT-01 — money values normalize to canonical INR lakh, exactly and with lineage."""

from __future__ import annotations

from decimal import Decimal

from data_platform.harmonize.units import CANONICAL_MONEY_UNIT, MoneyUnit, to_canonical_lakh


def test_lakh_is_canonical_and_unchanged() -> None:
    out = to_canonical_lakh(Decimal("3884.10"), MoneyUnit.LAKH)
    assert out.value_lakh == Decimal("3884.10")
    assert out.original_unit == "lakh"
    assert out.note is None  # no conversion happened


def test_crore_converts_to_lakh_times_100() -> None:
    out = to_canonical_lakh(Decimal("4.2218"), MoneyUnit.CRORE)
    assert out.value_lakh == Decimal("422.18")
    assert out.note == "R4-UNIT-01:crore→lakh"


def test_rupees_convert_to_lakh() -> None:
    out = to_canonical_lakh(Decimal("422180"), MoneyUnit.RUPEE)
    assert out.value_lakh == Decimal("4.2218")
    assert out.note == "R4-UNIT-01:rupee→lakh"


def test_thousands_convert_to_lakh() -> None:
    out = to_canonical_lakh(Decimal("100"), MoneyUnit.THOUSAND)
    assert out.value_lakh == Decimal("1")
    assert out.note == "R4-UNIT-01:thousand→lakh"


def test_none_passes_through_as_none_never_zero() -> None:
    out = to_canonical_lakh(None, MoneyUnit.CRORE)
    assert out.value_lakh is None
    assert out.note is None
    assert out.original_unit == "crore"  # original unit still recorded


def test_canonical_unit_is_lakh() -> None:
    assert CANONICAL_MONEY_UNIT is MoneyUnit.LAKH
