"""Derived figures — the only arithmetic the report is allowed to do.

Two families, both computed HERE by deterministic code over explicitly listed input facts, and
never by the LLM. Each derivation records its operation and its input ``fact_id``s, so the verifier
can recompute it from the same inputs and block on any mismatch.

**Analytical** operations state a relationship the data supports: a sum, a difference, a ratio.

**Presentation** operations state the same served value in the form a reader can hold: 3,881,318,918
person-days is *3.88 billion*; 10,999,798.601773694 INR lakh is *Rs 1.10 lakh crore*. These exist so
the prose can be readable WITHOUT loosening verification: a presentation form is a declared
derivation the verifier recomputes from the served figure, not the drafter rounding a number it was
told not to round. Undeclared rounding in prose still blocks. The exact served value always appears
in the section's figure table underneath.

Exact arithmetic (:class:`~decimal.Decimal`) throughout: a report figure that fails to reconcile
because of binary floating-point drift would be indistinguishable from one the drafter invented.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

# --- analytical -------------------------------------------------------------------------------
SUM: Final = "sum"
DIFFERENCE: Final = "difference"
RATIO: Final = "ratio"
RATIO_2DP: Final = "ratio_2dp"

# --- presentation -----------------------------------------------------------------------------
TO_MILLIONS: Final = "to_millions"
TO_BILLIONS: Final = "to_billions"
LAKH_TO_CRORE: Final = "lakh_to_crore"
LAKH_TO_LAKH_CRORE: Final = "lakh_to_lakh_crore"
ROUND_SIGFIG_3: Final = "round_sigfig_3"
ROUND_2DP: Final = "round_2dp"

# A ratio of two exact decimals runs to 28 significant digits ("4.288494297577824085634669313
# times"), which is precision the claim does not have and no reader wants. Rounding it HERE, as a
# named operation the verifier recomputes, keeps the drafter out of the arithmetic.
_TWO_DP: Final = Decimal("0.01")

# Indian money units, as the sources and the country use them: 1 crore = 100 lakh, and
# 1 lakh crore = 10,000,000 lakh (the unit national budgets are quoted in).
_LAKH_PER_CRORE: Final = Decimal(100)
_LAKH_PER_LAKH_CRORE: Final = Decimal(10_000_000)

_PER_MILLION: Final = Decimal(1_000_000)
_PER_BILLION: Final = Decimal(1_000_000_000)

_SIGNIFICANT_FIGURES: Final = 3


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
    return _ratio(values).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def _only(values: Sequence[Decimal], operation: str) -> Decimal:
    if len(values) != 1:
        raise ValueError(f"{operation} needs exactly 1 input, got {len(values)}")
    return values[0]


def _scaled_2dp(values: Sequence[Decimal], *, divisor: Decimal, operation: str) -> Decimal:
    return (_only(values, operation) / divisor).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def _to_millions(values: Sequence[Decimal]) -> Decimal:
    return _scaled_2dp(values, divisor=_PER_MILLION, operation=TO_MILLIONS)


def _to_billions(values: Sequence[Decimal]) -> Decimal:
    return _scaled_2dp(values, divisor=_PER_BILLION, operation=TO_BILLIONS)


def _lakh_to_crore(values: Sequence[Decimal]) -> Decimal:
    return _scaled_2dp(values, divisor=_LAKH_PER_CRORE, operation=LAKH_TO_CRORE)


def _lakh_to_lakh_crore(values: Sequence[Decimal]) -> Decimal:
    return _scaled_2dp(values, divisor=_LAKH_PER_LAKH_CRORE, operation=LAKH_TO_LAKH_CRORE)


def _round_2dp(values: Sequence[Decimal]) -> Decimal:
    """383.782169313422 INR reads as 383.78 — a declared rounding, recomputed by the verifier."""
    return _only(values, ROUND_2DP).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def _round_sigfig_3(values: Sequence[Decimal]) -> Decimal:
    """Round to three significant figures — 905,054,000 reads as 905,000,000."""
    value = _only(values, ROUND_SIGFIG_3)
    if value == 0:
        return value
    exponent = value.adjusted()  # power of ten of the leading digit
    quantum = Decimal(1).scaleb(exponent - (_SIGNIFICANT_FIGURES - 1))
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


OPERATIONS: Final[dict[str, Callable[[Sequence[Decimal]], Decimal]]] = {
    SUM: _sum,
    DIFFERENCE: _difference,
    RATIO: _ratio,
    RATIO_2DP: _ratio_2dp,
    TO_MILLIONS: _to_millions,
    TO_BILLIONS: _to_billions,
    LAKH_TO_CRORE: _lakh_to_crore,
    LAKH_TO_LAKH_CRORE: _lakh_to_lakh_crore,
    ROUND_SIGFIG_3: _round_sigfig_3,
    ROUND_2DP: _round_2dp,
}

# The operations that only restate a served value in a readable form. Recorded in report.json so a
# reader can tell "the same fact, another unit" from "a new claim about the data".
PRESENTATION_OPERATIONS: Final[frozenset[str]] = frozenset(
    {TO_MILLIONS, TO_BILLIONS, LAKH_TO_CRORE, LAKH_TO_LAKH_CRORE, ROUND_SIGFIG_3, ROUND_2DP}
)


def compute(operation: str, values: Sequence[Decimal]) -> Decimal:
    """Apply a named operation to its inputs. An unknown operation is an error, not a guess."""
    op = OPERATIONS.get(operation)
    if op is None:
        raise ValueError(f"unknown operation {operation!r}; known: {sorted(OPERATIONS)}")
    return op(values)
