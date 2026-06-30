"""R3-GEO-02 / R3-GEO-03 at DISTRICT grain — resolve within an already-resolved LGD state.

The caller resolves the state first, then resolves the district scoped to that LGD state code.
Exact normalized match (R3-GEO-02) covers ~88% of flagship districts; a curated alias table
(R3-GEO-03) covers the verified spelling/transliteration/rename/token-order variants. A district
that matches neither resolves to ``None`` (R3-GEO-05 quarantine) — never a guess, and never a
silent merge of two distinct places.
"""

from __future__ import annotations

from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import LGDDistrict, LGDState

_STATES = [
    LGDState(code="23", name="Madhya Pradesh"),
    LGDState(code="29", name="Karnataka"),
    LGDState(code="19", name="West Bengal"),
]
_DISTRICTS = [
    LGDDistrict(state_code="23", code="461", name="Niwari"),
    LGDDistrict(state_code="29", code="540", name="Bengaluru Urban"),
    LGDDistrict(state_code="29", code="541", name="Bengaluru Rural"),
    LGDDistrict(state_code="19", code="330", name="North 24 Parganas"),
    LGDDistrict(state_code="19", code="331", name="South 24 Parganas"),
]
_RESOLVER = GeoResolver.from_reference(states=_STATES, districts=_DISTRICTS)


def test_exact_district_resolves_with_r3_geo_02() -> None:
    match = _RESOLVER.resolve_district("23", "NIWARI")
    assert match is not None
    assert match.code == "461"
    assert match.name == "Niwari"
    assert match.rule_id == "R3-GEO-02"


def test_alias_district_resolves_with_r3_geo_03() -> None:
    # Flagship bare "BENGALURU" -> LGD "Bengaluru Urban" (Rural is published separately).
    match = _RESOLVER.resolve_district("29", "BENGALURU")
    assert match is not None
    assert match.code == "540"
    assert match.name == "Bengaluru Urban"
    assert match.rule_id.startswith("R3-GEO-03")


def test_directional_aliases_do_not_swap() -> None:
    # The one thing conservative normalization protects: North/South stay distinct.
    north = _RESOLVER.resolve_district("19", "24 PARGANAS (NORTH)")
    south = _RESOLVER.resolve_district("19", "24 PARGANAS SOUTH")
    assert north is not None and north.name == "North 24 Parganas"
    assert south is not None and south.name == "South 24 Parganas"


def test_unresolved_district_returns_none() -> None:
    # "Bengaluru South" — a new district absent from LGD, and not in the alias table.
    assert _RESOLVER.resolve_district("29", "BENGALURU SOUTH") is None


def test_alias_is_state_scoped() -> None:
    # The "bengaluru" alias key must NOT fire for a different state code.
    assert _RESOLVER.resolve_district("19", "BENGALURU") is None


def test_null_or_empty_district_returns_none() -> None:
    assert _RESOLVER.resolve_district("23", None) is None
    assert _RESOLVER.resolve_district("23", "   ") is None
