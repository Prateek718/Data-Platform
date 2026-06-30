"""Geography resolver — flagship state/district names → canonical LGD identity.

The PRIMARY Stage-3 mechanism. Flagship's own state/district codes are source-internal (MIS)
codes, NOT LGD codes (every one differs — DATA_CONTRACT §2.2), so identity is established by a
NAME join against the LGD reference: conservative normalization + exact match (R3-GEO-02), with a
curated alias table for the observed variants (R3-GEO-03). A name that resolves to neither
returns ``None`` — the caller quarantines ``unresolved_geography`` (R3-GEO-05), never a guess.

The resolver is built once from the LGD reference and is pure/deterministic thereafter; tests
construct it from a small inline reference. District resolution lands in T3.4.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from data_platform.resolve.aliases import STATE_ALIASES
from data_platform.resolve.lgd import LGDDistrict, LGDState
from data_platform.resolve.models import GeoMatch
from data_platform.resolve.normalize_name import normalize_geo_name


@dataclass(frozen=True)
class GeoResolver:
    """Resolves flagship state/district names to canonical LGD identity."""

    _state_by_norm: dict[str, LGDState]
    _district_by_norm: dict[tuple[str, str], LGDDistrict]

    @classmethod
    def from_reference(
        cls, states: Iterable[LGDState], districts: Iterable[LGDDistrict]
    ) -> GeoResolver:
        """Build the resolver's lookup indexes from the LGD reference rows."""
        state_by_norm = {normalize_geo_name(s.name): s for s in states}
        if None in state_by_norm:  # defensive: an LGD row with a null name is a corrupt reference
            raise ValueError("LGD state with null name in reference")
        district_by_norm: dict[tuple[str, str], LGDDistrict] = {}
        for d in districts:
            key = normalize_geo_name(d.name)
            if key is None:
                raise ValueError("LGD district with null name in reference")
            district_by_norm[(d.state_code, key)] = d
        return cls(
            _state_by_norm={k: v for k, v in state_by_norm.items() if k is not None},
            _district_by_norm=district_by_norm,
        )

    def resolve_state(self, name: str | None) -> GeoMatch | None:
        """Resolve a flagship state name to its LGD state, or ``None`` if unresolved."""
        normalized = normalize_geo_name(name)
        if not normalized:  # None (nulled cell) or "" (empty) — no identity to resolve
            return None
        exact = self._state_by_norm.get(normalized)
        if exact is not None:
            return GeoMatch(code=exact.code, name=exact.name, rule_id="R3-GEO-02")
        aliased = STATE_ALIASES.get(normalized)
        if aliased is not None:
            target = self._state_by_norm.get(aliased)
            if target is not None:
                return GeoMatch(
                    code=target.code, name=target.name, rule_id=f"R3-GEO-03:{normalized}"
                )
        return None

    def resolve_district(self, lgd_state_code: str, name: str | None) -> GeoMatch | None:
        """Resolve a flagship district name within an LGD state (stub; implemented next)."""
        return None
