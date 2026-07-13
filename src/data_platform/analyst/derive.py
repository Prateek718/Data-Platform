"""Derived figures — the only arithmetic the report is allowed to do.

Some claims are ratios, sums or differences over retrieved facts rather than values a single
``query`` returns. Those are computed HERE, by deterministic code over explicitly listed input
facts, and never by the LLM. Each derivation records its operation and its input ``fact_id``s, so
the verifier can recompute it from the same inputs and block on any mismatch.

Exact arithmetic (:class:`~decimal.Decimal`) throughout: a report figure that fails to reconcile
because of binary floating-point drift would be indistinguishable from one the drafter invented.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

SUM: Final = "sum"
DIFFERENCE: Final = "difference"
RATIO: Final = "ratio"
RATIO_2DP: Final = "ratio_2dp"

# A ratio of two exact decimals runs to 28 significant digits ("4.288494297577824085634669313
# times"), which is precision the claim does not have and no reader wants. Rounding it HERE, as a
# named operation the verifier recomputes, keeps the drafter out of the arithmetic: the drafter
# still may not round anything — the report's rounding is a declared, reproducible step.
_RATIO_QUANTUM: Final = Decimal("0.01")


def _sum(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("sum needs at least one input")
    return sum(values, Decimal(0))


def _difference(values: Sequence[Decimal]) -> Decimal:
    if len(values) != 2:
        raise ValueError(f"difference needs exactly 2 inputs, got {len(values)}")
    return values[0] - values[1]


def _ratio(values: Sequence[Decimal]) -> Decimal:
    if len(values) != 2:
        raise ValueError(f"ratio needs exactly 2 inputs, got {len(values)}")
    if values[1] == 0:
        raise ValueError("ratio has a zero denominator")
    return values[0] / values[1]


def _ratio_2dp(values: Sequence[Decimal]) -> Decimal:
    return _ratio(values).quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_UP)


OPERATIONS: Final[dict[str, Callable[[Sequence[Decimal]], Decimal]]] = {
    SUM: _sum,
    DIFFERENCE: _difference,
    RATIO: _ratio,
    RATIO_2DP: _ratio_2dp,
}


def compute(operation: str, values: Sequence[Decimal]) -> Decimal:
    """Apply a named operation to its inputs. An unknown operation is an error, not a guess."""
    op = OPERATIONS.get(operation)
    if op is None:
        raise ValueError(f"unknown operation {operation!r}; known: {sorted(OPERATIONS)}")
    return op(values)
