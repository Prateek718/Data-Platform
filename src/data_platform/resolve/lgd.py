"""LGD reference — the authoritative canonical geography (states + districts).

The Local Government Directory (LGD) is the canonical code authority (DATA_CONTRACT §2.2,
R3-GEO-04). These frozen models are the reference rows the resolver matches against; the loader
(:func:`load_lgd_reference`) reads the archived LGD JSON from disk — the ONE impure entry point,
kept apart from the pure resolution transform so tests construct a reference inline and the
hermetic suite never touches the filesystem fixture.

Codes are carried as ``str`` (canonical identity is an opaque id, never arithmetic) — the LGD
JSON ships ``state_code`` as an int and ``district_code`` as a string; both are normalized to
``str`` here so identity comparison is uniform.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)


class LGDState(_Frozen):
    """One LGD state: canonical code + current canonical (English) display name."""

    code: str
    name: str


class LGDDistrict(_Frozen):
    """One LGD district: canonical code + current name, scoped to its LGD state code."""

    state_code: str
    code: str
    name: str


def load_lgd_reference(
    states_path: Path, districts_path: Path
) -> tuple[list[LGDState], list[LGDDistrict]]:
    """Load the archived LGD JSON into reference rows (impure: reads disk)."""
    states_raw = json.loads(states_path.read_text())["records"]
    districts_raw = json.loads(districts_path.read_text())["records"]
    states = [LGDState(code=str(r["state_code"]), name=r["state_name_english"]) for r in states_raw]
    districts = [
        LGDDistrict(
            state_code=str(r["state_code"]),
            code=str(r["district_code"]),
            name=r["district_name_english"],
        )
        for r in districts_raw
    ]
    return states, districts
