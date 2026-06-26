"""Stage 2 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

Per the registry pattern: the tunable inputs Stage 2 rules consume live here as named
constants, never as magic values inside the transforms. Grows per task (NULL_TOKENS for
R2-FMT-01; the column-type spec for R2-TYPE-01/R2-DATE-01; grain keys + dedupe id for
R2-DEDUP-01). Nothing here invents schema — column lists come from Stage 0 (sources.md).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

# R2-FMT-01 — tokens (compared case-insensitively after stripping) that mean "missing",
# mapped to null, NEVER zero. A whitespace-only / empty cell is also null (handled in fmt).
NULL_TOKENS: Final = frozenset({"NA", "-"})


class ColumnType(StrEnum):
    """The real type a source column is coerced/normalized to (Q4 — config-carried, not inferred).

    ``STRING`` covers identifiers (``state_code``/``district_code``) and free text — kept as
    ``str`` even when they look numeric. ``INT``/``DECIMAL`` are R2-TYPE-01's domain (Q6: counts
    int, money/rate Decimal); ``FY``/``MONTH`` are R2-DATE-01's domain (canonical strings, Q2).
    """

    STRING = "string"
    INT = "int"
    DECIMAL = "decimal"
    FY = "fy"
    MONTH = "month"


# R2-DATE-01 — month name/abbreviation (lowercased) -> canonical zero-padded "01".."12" (Q2).
_MONTH_NAMES: Final = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
MONTH_TO_CANONICAL: Final[dict[str, str]] = {
    **{name: f"{i:02d}" for i, name in enumerate(_MONTH_NAMES, start=1)},
    **{name[:3]: f"{i:02d}" for i, name in enumerate(_MONTH_NAMES, start=1)},
}
