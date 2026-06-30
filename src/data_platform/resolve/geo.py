"""Geography resolver (stub; state resolution implemented next commit)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from data_platform.resolve.lgd import LGDDistrict, LGDState
from data_platform.resolve.models import GeoMatch


@dataclass(frozen=True)
class GeoResolver:
    """Resolves flagship state/district names to canonical LGD identity."""

    _state_by_norm: dict[str, LGDState]

    @classmethod
    def from_reference(
        cls, states: Iterable[LGDState], districts: Iterable[LGDDistrict]
    ) -> GeoResolver:
        return cls(_state_by_norm={})

    def resolve_state(self, name: str | None) -> GeoMatch | None:
        return None
