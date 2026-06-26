"""T2.4 — R2-DATE-01 date/FY normalization (tests first, red checkpoint).

Q2: canonical FY = "YYYY-YY", month = zero-padded "01".."12". Single-row only — no
cross-source period logic. Un-parseable temporal cell -> null + 'parse_failed'. Every
invariant is a guarding test.
"""

from __future__ import annotations

from data_platform.normalize.dates import normalize_fy, normalize_month

# --- FY (R2-DATE-01) --------------------------------------------------------------


def test_fy_four_plus_four_canonicalizes_to_yyyy_yy() -> None:
    out = normalize_fy("2022-2023")
    assert out.value == "2022-23"
    assert isinstance(out.value, str)
    assert out.note == "R2-DATE-01:2022-2023→2022-23"


def test_fy_already_canonical_is_unchanged_no_note() -> None:
    assert normalize_fy("2021-22") == ("2021-22", None)
    assert normalize_fy("2023-24") == ("2023-24", None)


def test_fy_non_consecutive_years_fail_to_null() -> None:
    # a financial year spans consecutive years; "2022-2024" is not a valid FY.
    assert normalize_fy("2022-2024") == (None, "R2-DATE-01:parse_failed")


def test_fy_garbage_fails_to_null() -> None:
    assert normalize_fy("2022/2023") == (None, "R2-DATE-01:parse_failed")
    assert normalize_fy("FY2022") == (None, "R2-DATE-01:parse_failed")


def test_fy_none_stays_none() -> None:
    assert normalize_fy(None) == (None, None)


def test_fy_non_string_fails_to_null() -> None:
    assert normalize_fy(2022) == (None, "R2-DATE-01:parse_failed")


# --- Month (R2-DATE-01) -----------------------------------------------------------


def test_month_abbreviation_maps_to_zero_padded() -> None:
    assert normalize_month("Jan") == ("01", "R2-DATE-01:Jan→01")
    assert normalize_month("Dec") == ("12", "R2-DATE-01:Dec→12")


def test_month_full_name_maps() -> None:
    assert normalize_month("January") == ("01", "R2-DATE-01:January→01")


def test_month_is_case_insensitive_and_trims() -> None:
    assert normalize_month("jan").value == "01"
    assert normalize_month(" Jan ").value == "01"


def test_month_numeric_is_zero_padded() -> None:
    assert normalize_month("1") == ("01", "R2-DATE-01:1→01")
    assert normalize_month("01") == ("01", None)  # already canonical


def test_month_none_stays_none() -> None:
    assert normalize_month(None) == (None, None)


def test_month_out_of_range_and_garbage_fail_to_null_not_zero() -> None:
    bad = normalize_month("Foo")
    assert bad.value is None  # null...
    assert bad.value != 0  # ...never zero
    assert bad.note == "R2-DATE-01:parse_failed"
    assert normalize_month("13") == (None, "R2-DATE-01:parse_failed")
