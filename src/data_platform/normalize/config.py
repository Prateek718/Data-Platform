"""Stage 2 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

Per the registry pattern: the tunable inputs Stage 2 rules consume live here as named
constants, never as magic values inside the transforms. Grows per task (NULL_TOKENS for
R2-FMT-01; the column-type spec for R2-TYPE-01/R2-DATE-01; grain keys + dedupe id for
R2-DEDUP-01). Nothing here invents schema — column lists come from Stage 0 (sources.md).
"""

from __future__ import annotations

from typing import Final

# R2-FMT-01 — tokens (compared case-insensitively after stripping) that mean "missing",
# mapped to null, NEVER zero. A whitespace-only / empty cell is also null (handled in fmt).
NULL_TOKENS: Final = frozenset({"NA", "-"})
