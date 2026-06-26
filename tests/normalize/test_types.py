"""T2.3 — R2-TYPE-01 type coercion (tests first, red checkpoint).

coerce_cell maps a cleaned cell to its config-declared real type (Q6: counts int, money/rate
Decimal; Q4: identifiers stay str). Un-coercible -> null + 'coercion_failed' (Q1, keep row).
FY/MONTH are out of scope here (R2-DATE-01). Every invariant is a guarding test.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from data_platform.normalize.coerce import coerce_cell
from data_platform.normalize.config import ColumnType


def test_int_string_coerces_to_int() -> None:
    out = coerce_cell("34679", ColumnType.INT)
    assert out.value == 34679
    assert isinstance(out.value, int)
    assert out.note == "R2-TYPE-01:str→int"


def test_integral_decimal_string_coerces_to_int() -> None:
    assert coerce_cell("34679.0", ColumnType.INT).value == 34679


def test_non_integer_string_fails_int_coercion_to_null() -> None:
    out = coerce_cell("397.31", ColumnType.INT)
    assert out.value is None
    assert out.note == "R2-TYPE-01:coercion_failed"


def test_garbage_fails_coercion_to_null_not_zero() -> None:
    out = coerce_cell("not-a-number", ColumnType.INT)
    assert out.value is None  # null...
    assert out.value != 0  # ...never zero (Q1 / null != 0)
    assert out.note == "R2-TYPE-01:coercion_failed"


def test_decimal_string_coerces_to_decimal_with_full_precision() -> None:
    out = coerce_cell("397.314743793074", ColumnType.DECIMAL)
    assert out.value == Decimal("397.314743793074")
    assert isinstance(out.value, Decimal)
    assert out.note == "R2-TYPE-01:str→decimal"


def test_integer_string_coerces_to_decimal_when_target_is_decimal() -> None:
    out = coerce_cell("100", ColumnType.DECIMAL)
    assert out.value == Decimal("100")
    assert isinstance(out.value, Decimal)


def test_decimal_garbage_fails_to_null() -> None:
    assert coerce_cell("abc", ColumnType.DECIMAL) == (None, "R2-TYPE-01:coercion_failed")


def test_identifier_string_stays_string_unchanged() -> None:
    # numeric-looking identifier under a STRING column is NOT turned into a number (Q4).
    assert coerce_cell("10", ColumnType.STRING) == ("10", None)
    assert coerce_cell("1001", ColumnType.STRING) == ("1001", None)


def test_bare_scalar_in_string_column_is_stringified() -> None:
    out = coerce_cell(10, ColumnType.STRING)
    assert out.value == "10"
    assert isinstance(out.value, str)
    assert out.note == "R2-TYPE-01:int→str"


def test_bare_int_in_int_column_passes_through_no_note() -> None:
    assert coerce_cell(2523, ColumnType.INT) == (2523, None)


def test_null_stays_null_for_every_target() -> None:
    for target in (ColumnType.STRING, ColumnType.INT, ColumnType.DECIMAL):
        assert coerce_cell(None, target) == (None, None)


def test_bool_is_not_a_number() -> None:
    # a bool must never be silently read as 1/0 in a numeric column.
    assert coerce_cell(True, ColumnType.INT).value is None
    assert coerce_cell(True, ColumnType.DECIMAL).value is None


def test_temporal_types_are_not_handled_here() -> None:
    # FY/MONTH belong to R2-DATE-01; routing one here is a programming error.
    with pytest.raises(ValueError, match="temporal"):
        coerce_cell("2022-23", ColumnType.FY)
    with pytest.raises(ValueError, match="temporal"):
        coerce_cell("Jan", ColumnType.MONTH)
