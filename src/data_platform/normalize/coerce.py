"""R2-TYPE-01 — type coercion.

Coerce an R2-FMT-01-cleaned cell to its config-declared real type (Q4/Q6): counts to ``int``,
money/rate to ``Decimal`` (full precision — never via ``float``, which would drift before
Stage 4's tolerance math), identifiers/text to ``str`` (numeric-looking identifiers stay
strings). An un-coercible cell becomes null and is flagged ``R2-TYPE-01:coercion_failed`` —
the row is kept (Q1). FY/MONTH are R2-DATE-01's domain and are rejected here.

The lineage note records ``<delivered-python-type>→<target>`` (e.g. ``str→decimal``): Stage 1
deliberately dropped the source envelope's (unreliable) declared types, so the honest record of
what was coerced is the type the value actually arrived as.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from data_platform.normalize.config import ColumnType
from data_platform.normalize.models import CleanCell, RawCell


class CoerceOutcome(NamedTuple):
    """The coerced value plus a lineage note (``None`` when nothing was coerced)."""

    value: CleanCell
    note: str | None


_FAILED = "R2-TYPE-01:coercion_failed"


def coerce_cell(value: RawCell, target: ColumnType) -> CoerceOutcome:
    """Coerce one cleaned cell to ``target``.

    ``None`` stays ``None`` (already nulled by R2-FMT-01). A ``bool`` is never read as a number.
    """
    if value is None:
        return CoerceOutcome(None, None)

    if target is ColumnType.STRING:
        if isinstance(value, str):
            return CoerceOutcome(value, None)
        return CoerceOutcome(str(value), f"R2-TYPE-01:{type(value).__name__}→str")

    if target is ColumnType.INT:
        return _to_int(value)

    if target is ColumnType.DECIMAL:
        return _to_decimal(value)

    raise ValueError(f"coerce_cell does not handle temporal type {target!r}")


def _as_decimal(value: str | int | float) -> Decimal | None:
    """Parse a non-bool scalar to ``Decimal``, or ``None`` if un-parseable."""
    if isinstance(value, bool):  # bool is an int subclass — reject it as a number
        return None
    try:
        return Decimal(value if isinstance(value, str) else str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: str | int | float | bool) -> CoerceOutcome:
    if isinstance(value, int) and not isinstance(value, bool):
        return CoerceOutcome(value, None)  # already a clean int
    parsed = _as_decimal(value)
    if parsed is None or parsed != parsed.to_integral_value():
        return CoerceOutcome(None, _FAILED)
    return CoerceOutcome(int(parsed), f"R2-TYPE-01:{type(value).__name__}→int")


def _to_decimal(value: str | int | float | bool) -> CoerceOutcome:
    parsed = _as_decimal(value)
    if parsed is None:
        return CoerceOutcome(None, _FAILED)
    return CoerceOutcome(parsed, f"R2-TYPE-01:{type(value).__name__}→decimal")
