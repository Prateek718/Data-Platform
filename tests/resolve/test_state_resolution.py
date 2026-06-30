"""R3-GEO-02 / R3-GEO-03 at STATE grain — resolve a flagship state name to an LGD state.

Flagship state names are input aliases; canonical identity is the LGD code, display is the
current LGD name. Most resolve by exact normalized-name match (R3-GEO-02); a small curated alias
set covers the observed variants (R3-GEO-03). A name that matches neither resolves to ``None`` —
the caller quarantines ``unresolved_geography`` (R3-GEO-05), never a guess.
"""

from __future__ import annotations

from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import LGDState

# Minimal LGD state slice covering exact, both observed aliases, and an unrelated state.
_STATES = [
    LGDState(code="30", name="Goa"),
    LGDState(code="23", name="Madhya Pradesh"),
    LGDState(code="35", name="Andaman And Nicobar Islands"),
    LGDState(code="38", name="The Dadra And Nagar Haveli And Daman And Diu"),
]
_RESOLVER = GeoResolver.from_reference(states=_STATES, districts=[])


def test_exact_match_resolves_with_r3_geo_02() -> None:
    # Flagship "MADHYA PRADESH" (MIS code 17) -> LGD code 23 by name, NOT by code.
    match = _RESOLVER.resolve_state("MADHYA PRADESH")
    assert match is not None
    assert match.code == "23"
    assert match.name == "Madhya Pradesh"
    assert match.rule_id == "R3-GEO-02"


def test_andaman_alias_resolves_with_r3_geo_03() -> None:
    match = _RESOLVER.resolve_state("ANDAMAN AND NICOBAR")
    assert match is not None
    assert match.code == "35"
    assert match.name == "Andaman And Nicobar Islands"
    assert match.rule_id.startswith("R3-GEO-03")


def test_dnh_dd_alias_resolves_with_r3_geo_03() -> None:
    # OBSERVED abbreviation (R3-GEO-01 docstring example).
    match = _RESOLVER.resolve_state("DN HAVELI AND DD")
    assert match is not None
    assert match.code == "38"
    assert match.rule_id.startswith("R3-GEO-03")


def test_unknown_state_is_unresolved() -> None:
    assert _RESOLVER.resolve_state("ATLANTIS") is None


def test_null_junk_state_is_unresolved() -> None:
    # Flagship "NA" -> Stage-2 NULL_TOKENS already nulled it; arrives here as None.
    assert _RESOLVER.resolve_state(None) is None
    # And the literal junk token, were it ever to survive, also does not resolve.
    assert _RESOLVER.resolve_state("NA") is None
