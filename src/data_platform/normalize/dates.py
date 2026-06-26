"""R2-DATE-01 — date/FY normalization (T2.4 STUB — red checkpoint).

Single-row temporal formatting (no cross-source logic): canonicalize a financial-year string
to ``YYYY-YY`` and a month to zero-padded ``01``..``12`` (Q2). An un-parseable temporal cell
becomes null and is flagged ``R2-DATE-01:parse_failed`` (mirrors the Q1 cell-null principle).
Implemented in the green commit ``feat(stage2): …``.
"""

from __future__ import annotations

from typing import NamedTuple

from data_platform.normalize.models import RawCell


class DateOutcome(NamedTuple):
    """The canonical temporal string (or ``None``) plus a lineage note."""

    value: str | None
    note: str | None


def normalize_fy(value: RawCell) -> DateOutcome:
    """Canonicalize a financial year to ``YYYY-YY``. STUB — raises until the green commit."""
    raise NotImplementedError("T2.4 R2-DATE-01 (FY) — implemented in the green commit")


def normalize_month(value: RawCell) -> DateOutcome:
    """Canonicalize a month to ``01``..``12``. STUB — raises until the green commit."""
    raise NotImplementedError("T2.4 R2-DATE-01 (month) — implemented in the green commit")
