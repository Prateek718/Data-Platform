"""R3-GEO-01 — geo name normalization (the conservative match key).

Normalization is deliberately MINIMAL: lowercase, trim, collapse internal whitespace, strip
punctuation to single spaces, fold unicode width. Anything beyond that (directional reorders,
suffix stripping, spelling fixes) is an EXPLICIT alias entry, never code — generic cleverness
here would risk merging two distinct places (e.g. North vs South 24 Parganas). These tests pin
that boundary: real flagship spellings that SHOULD collapse to the same key do, and pairs that
must stay distinct do not.
"""

from __future__ import annotations

from data_platform.resolve.normalize_name import normalize_geo_name


def test_lowercases_and_trims() -> None:
    assert normalize_geo_name("  MADHYA PRADESH  ") == "madhya pradesh"


def test_collapses_internal_whitespace() -> None:
    # OBSERVED: flagship ships trailing/!double spaces inside district cells.
    assert normalize_geo_name("BHATINDA                  ") == "bhatinda"
    assert normalize_geo_name("RANGA   REDDY") == "ranga reddy"


def test_strips_punctuation_to_single_space() -> None:
    # Hyphens, parens, dots all fold to a space and collapse.
    assert normalize_geo_name("South Salmara-Mankachar") == "south salmara mankachar"
    assert normalize_geo_name("Kumram Bheem(Asifabad)") == "kumram bheem asifabad"
    assert normalize_geo_name("S.A.S Nagar") == "s a s nagar"


def test_digits_are_preserved() -> None:
    # "24 Parganas" must keep its number — it is identity, not noise.
    assert normalize_geo_name("24 PARGANAS (NORTH)") == "24 parganas north"


def test_none_returns_none() -> None:
    # A nulled cell (Stage-2 NULL_TOKENS) stays null — never coerced to "".
    assert normalize_geo_name(None) is None


def test_empty_and_whitespace_only_normalize_to_empty_string() -> None:
    assert normalize_geo_name("") == ""
    assert normalize_geo_name("   ") == ""


def test_does_not_reorder_or_strip_direction_tokens() -> None:
    # CONSERVATIVE: these stay DISTINCT keys; only an explicit alias may map them.
    assert normalize_geo_name("24 PARGANAS (NORTH)") != normalize_geo_name("24 PARGANAS SOUTH")
    assert normalize_geo_name("North 24 Parganas") != normalize_geo_name("South 24 Parganas")
