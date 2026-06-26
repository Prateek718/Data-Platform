"""R2-FMT-01 — numeric/format cleaning (T2.2 STUB — red checkpoint).

Pure, single-cell, type-AGNOSTIC format cleaning that runs before type coercion: strip
thousands-commas from numeric strings, map blank / ``NA`` / ``-`` to null (NOT zero), and
preserve everything else verbatim. Implemented in the green commit ``feat(stage2): …``.
"""

from __future__ import annotations

from typing import NamedTuple

from data_platform.normalize.models import RawCell


class FmtOutcome(NamedTuple):
    """The cleaned value plus a lineage note (``None`` when the cell was unchanged)."""

    value: RawCell
    note: str | None


def apply_fmt(value: RawCell) -> FmtOutcome:
    """Apply R2-FMT-01 to one cell. STUB — raises until the green commit."""
    raise NotImplementedError("T2.2 R2-FMT-01 — implemented in the green commit")
