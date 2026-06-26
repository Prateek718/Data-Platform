"""R2-FMT-01 — numeric/format cleaning.

Pure, single-cell, type-AGNOSTIC format cleaning that runs BEFORE type coercion (R2-TYPE-01):
strip thousands-commas from numeric strings, map blank / ``NA`` / ``-`` to null (NOT zero;
``null != 0``), and preserve everything else verbatim. It never coerces a type and never
mangles text — comma-stripping applies only when the de-comma'd value is itself numeric, and
non-numeric text (district names, ``fin_year``, ``month``) is returned exactly as seen
(trim/collapse for matching is Stage 3 geo, date parsing is R2-DATE-01).
"""

from __future__ import annotations

import re
from typing import NamedTuple

from data_platform.normalize.config import NULL_TOKENS
from data_platform.normalize.models import RawCell

# A bare integer or decimal, optionally signed — the only shape we treat as a number to clean.
_NUMERIC_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")
_NULL_TOKENS_UPPER = frozenset(token.upper() for token in NULL_TOKENS)


class FmtOutcome(NamedTuple):
    """The cleaned value plus a lineage note (``None`` when the cell was unchanged)."""

    value: RawCell
    note: str | None


def apply_fmt(value: RawCell) -> FmtOutcome:
    """Apply R2-FMT-01 to one cell.

    Non-string scalars (bare ``int``/``float``/``bool``) and ``None`` pass through untouched —
    there is nothing to format-clean and coercion is R2-TYPE-01's job. For strings: a blank or
    a null-token (case-insensitive) becomes ``None``; a numeric string is de-comma'd/trimmed to
    expose the number; any other text is returned verbatim.
    """
    if not isinstance(value, str):
        return FmtOutcome(value, None)

    stripped = value.strip()
    if stripped == "":
        return FmtOutcome(None, "R2-FMT-01:blank→null")
    if stripped == "-":
        return FmtOutcome(None, "R2-FMT-01:dash→null")
    if stripped.upper() in _NULL_TOKENS_UPPER:
        return FmtOutcome(None, "R2-FMT-01:NA→null")

    decommaed = stripped.replace(",", "")
    if _NUMERIC_RE.fullmatch(decommaed):
        if "," in stripped:
            return FmtOutcome(decommaed, "R2-FMT-01:strip_commas")
        if stripped != value:
            return FmtOutcome(decommaed, "R2-FMT-01:trim")
        return FmtOutcome(decommaed, None)

    # Non-numeric text: preserve exactly as seen.
    return FmtOutcome(value, None)
