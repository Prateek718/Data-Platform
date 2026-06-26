"""R2-DATE-01 — date/FY normalization.

Single-row temporal formatting (no cross-source logic): canonicalize a financial-year string
to ``YYYY-YY`` and a month to zero-padded ``01``..``12`` (Q2). A financial year is a span, not
a calendar date, so it stays a string — we never fabricate a day-of-month. An un-parseable
temporal cell becomes null and is flagged ``R2-DATE-01:parse_failed`` (mirrors the Q1 cell-null
principle: keep the row, lose only the bad cell).
"""

from __future__ import annotations

import re
from typing import NamedTuple

from data_platform.normalize.config import MONTH_TO_CANONICAL
from data_platform.normalize.models import RawCell

_FY_RE = re.compile(r"(\d{4})-(\d{2}|\d{4})")
_PARSE_FAILED = "R2-DATE-01:parse_failed"


class DateOutcome(NamedTuple):
    """The canonical temporal string (or ``None``) plus a lineage note."""

    value: str | None
    note: str | None


def _result(original: str, canonical: str) -> DateOutcome:
    """A successful normalization — note only when the value actually changed."""
    if canonical == original:
        return DateOutcome(canonical, None)
    return DateOutcome(canonical, f"R2-DATE-01:{original}→{canonical}")


def normalize_fy(value: RawCell) -> DateOutcome:
    """Canonicalize a financial year ("2022-2023" / "2021-22") to ``YYYY-YY``.

    The two years must be consecutive (a FY spans one April→March); otherwise it is not a
    financial year and the cell is nulled.
    """
    if value is None:
        return DateOutcome(None, None)
    if not isinstance(value, str):
        return DateOutcome(None, _PARSE_FAILED)

    text = value.strip()
    match = _FY_RE.fullmatch(text)
    if match is None:
        return DateOutcome(None, _PARSE_FAILED)

    start = int(match.group(1))
    end = int(match.group(2))
    end_full = end if end > 99 else (start // 100) * 100 + end
    if end_full != start + 1:
        return DateOutcome(None, _PARSE_FAILED)

    return _result(text, f"{start}-{(start + 1) % 100:02d}")


def normalize_month(value: RawCell) -> DateOutcome:
    """Canonicalize a month name/abbreviation/number to zero-padded ``01``..``12``."""
    if value is None:
        return DateOutcome(None, None)
    if not isinstance(value, str):
        return DateOutcome(None, _PARSE_FAILED)

    text = value.strip()
    canonical = MONTH_TO_CANONICAL.get(text.lower())
    if canonical is None and text.isdigit() and 1 <= int(text) <= 12:
        canonical = f"{int(text):02d}"
    if canonical is None:
        return DateOutcome(None, _PARSE_FAILED)

    return _result(text, canonical)
