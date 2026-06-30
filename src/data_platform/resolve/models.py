"""Stage 3 resolution result models.

Small, frozen, strict — like the Stage 1/2 models. A :class:`GeoMatch` is the outcome of
resolving ONE geography field (state or district) to its canonical LGD identity, carrying the
rule id that established it (for the ``geo_resolution`` lineage field, DATA_CONTRACT §4). Richer
record/lineage/quarantine models are added when the batch pipeline lands (T3.5).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    """Base for Stage 3 models: immutable and strict (no coercion at the boundary)."""

    model_config = ConfigDict(strict=True, frozen=True)


class GeoMatch(_Frozen):
    """A geography field resolved to canonical LGD identity, with the rule that did it.

    ``rule_id`` is ``"R3-GEO-02"`` for an exact normalized-name match, or
    ``"R3-GEO-03:<normalized-source-name>"`` when the curated alias table resolved it.
    """

    code: str
    name: str
    rule_id: str
