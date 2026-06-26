"""T2.2 — R2-FMT-01 numeric/format cleaning (tests first, red checkpoint).

R2-FMT-01: strip thousands-commas from numeric strings, map blank/NA/"-" to null
(never zero), preserve all other values verbatim, leave non-string scalars untouched.
Every invariant below is a guarding test; the green commit implements apply_fmt.
"""

from __future__ import annotations

from data_platform.normalize.fmt import apply_fmt


def test_strips_thousands_commas_from_integer_string() -> None:
    out = apply_fmt("1,234")
    assert out.value == "1234"
    assert out.note == "R2-FMT-01:strip_commas"


def test_strips_commas_from_decimal_string() -> None:
    out = apply_fmt("1,234.56")
    assert out.value == "1234.56"
    assert out.note == "R2-FMT-01:strip_commas"


def test_plain_numeric_string_unchanged_no_note() -> None:
    assert apply_fmt("34679") == ("34679", None)
    assert apply_fmt("397.314743793074") == ("397.314743793074", None)


def test_na_maps_to_null_not_zero() -> None:
    out = apply_fmt("NA")
    assert out.value is None  # null...
    assert out.value != 0  # ...explicitly not zero
    assert out.note == "R2-FMT-01:NA→null"


def test_na_is_case_insensitive() -> None:
    assert apply_fmt("na").value is None
    assert apply_fmt(" Na ").value is None  # surrounding whitespace tolerated


def test_dash_maps_to_null() -> None:
    out = apply_fmt("-")
    assert out.value is None
    assert out.note == "R2-FMT-01:dash→null"


def test_blank_and_whitespace_map_to_null() -> None:
    assert apply_fmt("") == (None, "R2-FMT-01:blank→null")
    assert apply_fmt("   ") == (None, "R2-FMT-01:blank→null")


def test_text_preserved_verbatim() -> None:
    assert apply_fmt("GOA") == ("GOA", None)
    assert apply_fmt("NORTH GOA") == ("NORTH GOA", None)


def test_negative_number_is_not_dash_null() -> None:
    # "-" alone is null, but a signed number is a number, not a missing marker.
    assert apply_fmt("-5") == ("-5", None)


def test_comma_in_non_numeric_text_is_not_stripped() -> None:
    # comma-stripping is numeric cleaning only — never mangle text.
    assert apply_fmt("Hello, World") == ("Hello, World", None)


def test_fy_string_is_text_not_numeric() -> None:
    # "2022-2023" is not a number (R2-DATE-01 handles it); FMT leaves it verbatim.
    assert apply_fmt("2022-2023") == ("2022-2023", None)


def test_numeric_with_surrounding_whitespace_is_trimmed() -> None:
    out = apply_fmt(" 34679 ")
    assert out.value == "34679"
    assert out.note == "R2-FMT-01:trim"


def test_non_string_scalars_pass_through_untouched() -> None:
    # bare numbers/bools (from unreliable upstream type metadata) and null are left as-is;
    # coercion is R2-TYPE-01's job, not FMT's.
    assert apply_fmt(2523) == (2523, None)
    assert apply_fmt(3884.10) == (3884.10, None)
    assert apply_fmt(True) == (True, None)
    assert apply_fmt(None) == (None, None)
