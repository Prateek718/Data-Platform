"""Stage 4 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

The reconciliation agreement tolerance (R4-REC-01). Architect decision (2026-07-02): a single
0.5% band across metrics, with EXACT equality required for pure integer counts. Config-carried so
the band can be tuned per metric without touching the reconciliation logic.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

# Default agreement band: two sources within this percentage of each other "agree".
DEFAULT_TOLERANCE_PCT: Final = Decimal("0.5")

# Pure integer-count metrics: agreement requires EXACT equality, not a percentage band.
# NOTE: persondays_generated is a count but the RS tables publish it rounded to lakh precision, so
# it is reconciled on the percentage band (an exact rule would flag every rounding as a conflict).
EXACT_MATCH_METRICS: Final[frozenset[str]] = frozenset(
    {
        "households_employed",
        "households_completed_100_days",
        "active_workers",
    }
)


def tolerance_for(metric: str) -> Decimal | None:
    """The agreement tolerance (%) for a metric, or ``None`` when exact equality is required."""
    return None if metric in EXACT_MATCH_METRICS else DEFAULT_TOLERANCE_PCT


# R4-REC-07 scale-error detection: the dropped-/added-digit factors a value may be off by (10^k).
SCALE_ERROR_FACTORS: Final[tuple[Decimal, ...]] = (Decimal(10), Decimal(100), Decimal(1_000))


# Canonical metric names (DATA_CONTRACT §2.3) and their canonical units. Starter 3 first, then the
# other 6 (mechanical repetition). The canonical unit is what every source is normalized to.
PERSONDAYS_GENERATED: Final = "persondays_generated"
AVG_WAGE_RATE_PER_DAY: Final = "avg_wage_rate_per_day"
TOTAL_EXPENDITURE: Final = "total_expenditure"
HOUSEHOLDS_EMPLOYED: Final = "households_employed"
HOUSEHOLDS_COMPLETED_100_DAYS: Final = "households_completed_100_days"
ACTIVE_WORKERS: Final = "active_workers"
WAGES_EXPENDITURE: Final = "wages_expenditure"
MATERIAL_SKILLED_EXPENDITURE: Final = "material_skilled_expenditure"
ADMIN_EXPENDITURE: Final = "admin_expenditure"

CANONICAL_UNIT: Final[dict[str, str]] = {
    PERSONDAYS_GENERATED: "person-days",
    AVG_WAGE_RATE_PER_DAY: "INR",
    TOTAL_EXPENDITURE: "INR lakh",
    HOUSEHOLDS_EMPLOYED: "count",
    HOUSEHOLDS_COMPLETED_100_DAYS: "count",
    ACTIVE_WORKERS: "count",
    WAGES_EXPENDITURE: "INR lakh",
    MATERIAL_SKILLED_EXPENDITURE: "INR lakh",
    ADMIN_EXPENDITURE: "INR lakh",
}


# R4-REC-08 materiality: a disagreement is MATERIAL only if its largest pairwise spread is
# significant in BOTH absolute and relative terms — clearing an absolute floor AND a percentage
# floor. This filters two kinds of manufactured conflict on the count metrics: a near-zero-
# denominator swing (77 vs 174 completers = 126% but a ~100-hh spread → fails the absolute floor)
# and a rounding-level split on a large base (two RS vintages of 21.74 vs 21.76 lakh = a 2,000-hh
# spread on 2.1M → clears absolute but fails the 1% floor). Config-carried, per metric; expenditure
# and rates keep 0/0 (their 0.5% agreement band already governs), so their behaviour is unchanged.
_COUNT_MATERIALITY_ABS: Final = Decimal(1_000)
_COUNT_MATERIALITY_REL_PCT: Final = Decimal(1)
_COUNT_METRICS: Final = (
    HOUSEHOLDS_EMPLOYED,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    ACTIVE_WORKERS,
    PERSONDAYS_GENERATED,
)
MATERIALITY_ABS_FLOOR: Final[dict[str, Decimal]] = {
    m: _COUNT_MATERIALITY_ABS for m in _COUNT_METRICS
}
MATERIALITY_REL_PCT: Final[dict[str, Decimal]] = {
    m: _COUNT_MATERIALITY_REL_PCT for m in _COUNT_METRICS
}


def materiality_floor_for(metric: str) -> Decimal:
    """Absolute spread below which a disagreement is immaterial (0 = no absolute gate)."""
    return MATERIALITY_ABS_FLOOR.get(metric, Decimal(0))


def materiality_rel_pct_for(metric: str) -> Decimal:
    """Percentage spread below which a disagreement is immaterial (0 = no relative gate)."""
    return MATERIALITY_REL_PCT.get(metric, Decimal(0))
