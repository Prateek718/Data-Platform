"""R4-DEF-01 — total_expenditure by derive-and-compare.

Architect decision (Fork B): the canonical total is DERIVED (wages + material/skilled + admin), not
taken from a source's own "total" field. Where the source also carries its own total, the two are
compared; if they differ beyond tolerance the gap is recorded as a :class:`DefinitionDiscrepancy`
in lineage — the derived value stays canonical, and the inconsistency is surfaced, not hidden.
Pure; ``None`` source total (no total published) simply yields no comparison.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from data_platform.harmonize.models import DefinitionDiscrepancy


def derive_and_compare(
    components: Sequence[Decimal], source_total: Decimal | None, *, tolerance: Decimal
) -> tuple[Decimal, DefinitionDiscrepancy | None]:
    """Return ``(derived_total, discrepancy_or_None)``: sum the components; compare to the source's
    own total when present and record a discrepancy only when it exceeds ``tolerance`` (percent)."""
    derived = sum(components, Decimal(0))
    if source_total is None:
        return derived, None
    pct = _pct_diff(derived, source_total)
    if pct <= tolerance:
        return derived, None
    return derived, DefinitionDiscrepancy(
        derived=derived, source_provided=source_total, pct=pct, rule_id="R4-DEF-01"
    )


def _pct_diff(derived: Decimal, source_total: Decimal) -> Decimal:
    """Percentage gap of the source's total from the derived total (0-derived handled)."""
    if derived == 0:
        return Decimal(0) if source_total == 0 else abs(source_total) * 100
    return abs(derived - source_total) / abs(derived) * 100
