"""R2-TYPE-01 — type coercion (T2.3 STUB — red checkpoint).

Coerce an R2-FMT-01-cleaned cell to its config-declared real type (Q4/Q6): counts to ``int``,
money/rate to ``Decimal``, identifiers/text to ``str``. An un-coercible cell becomes null and
is flagged ``R2-TYPE-01:coercion_failed`` (Q1 — keep the row). FY/MONTH are R2-DATE-01's job.
Implemented in the green commit ``feat(stage2): …``.
"""

from __future__ import annotations

from typing import NamedTuple

from data_platform.normalize.config import ColumnType
from data_platform.normalize.models import CleanCell, RawCell


class CoerceOutcome(NamedTuple):
    """The coerced value plus a lineage note (``None`` when nothing was coerced)."""

    value: CleanCell
    note: str | None


def coerce_cell(value: RawCell, target: ColumnType) -> CoerceOutcome:
    """Coerce one cleaned cell to ``target``. STUB — raises until the green commit."""
    raise NotImplementedError("T2.3 R2-TYPE-01 — implemented in the green commit")
