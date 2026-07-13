"""The verifier — deterministic, no LLM, and the reason the report can be trusted.

It takes drafted prose plus the evidence the retriever gathered, and it blocks the section unless
EVERY numeric claim in the prose is backed:

* every number in the prose must be one of the section's declared figures or derivations, rendered
  exactly as the figure was given (no silent rounding, no unit conversion, no invention);
* every declared figure must carry a lineage reference — a source with a resource id and an as-of
  date. A figure without lineage is a failure, not a warning;
* every derivation is recomputed from its declared input facts, and must match;
* defense in depth: each figure's backing ``query`` is re-executed against the served data, and the
  value and ``fact_id`` must still match what the drafter was given.

Financial-year labels ("2022-23") are not figures: they are periods, and they are checked against
the periods the section actually retrieved (R7-SRV-01 — a label like this is compared as a string,
so it is validated for well-formedness rather than trusted).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from data_platform.analyst import derive
from data_platform.analyst.models import (
    Derivation,
    Figure,
    RetrievedSection,
    VerificationReport,
)
from data_platform.analyst.tools import AnalystTools, Payload

# A financial-year label: stripped from the prose before numbers are read, and validated separately.
FY_LABEL: Final = re.compile(r"\b[0-9]{4}-[0-9]{2}\b")

# A numeric token as prose renders one: 94,004 · 3,881,318,918 · 0.16 · 22.09% · 4.29x
NUMBER: Final = re.compile(r"(?<![\w.])[0-9][0-9,]*(?:\.[0-9]+)?")


def verify(section: RetrievedSection, prose: str, tools: AnalystTools) -> VerificationReport:
    """Check every numeric claim in ``prose`` against the section's evidence and the served data."""
    raise NotImplementedError


def number_tokens(prose: str) -> list[str]:
    """Every numeric token in the prose, with financial-year labels removed first."""
    raise NotImplementedError


def renderings(value: Decimal) -> set[str]:
    """The spellings of a value the prose may legitimately use (raw and comma-grouped)."""
    raise NotImplementedError


def lineage_problems(figure: Figure) -> list[str]:
    """Complaints about a figure's provenance — empty when it carries a usable lineage reference."""
    raise NotImplementedError


def derivation_problems(section: RetrievedSection, derivation: Derivation) -> list[str]:
    """Recompute a derivation from its declared inputs; complain on mismatch."""
    raise NotImplementedError


def replay_problems(figure: Figure, tools: AnalystTools) -> list[str]:
    """Re-execute a figure's backing query; complain if the served data no longer agrees."""
    raise NotImplementedError


def _rows(payload: Payload) -> Sequence[Payload]:
    raise NotImplementedError


def _decimal(value: object) -> Decimal | None:
    raise NotImplementedError


__all__ = [
    "FY_LABEL",
    "NUMBER",
    "derivation_problems",
    "derive",
    "lineage_problems",
    "number_tokens",
    "renderings",
    "replay_problems",
    "verify",
]
