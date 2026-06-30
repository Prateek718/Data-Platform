"""R3-SCHEME-01 — scheme identity resolution.

Normalize a scheme label by uppercasing and stripping every non-alphanumeric character
(spaces and punctuation), then match against a closed set of known MGNREGA aliases. A match
resolves to canonical ``"MGNREGA"``; anything else returns ``None`` so the caller can quarantine
``unknown_scheme`` (R3-SCHEME-01) rather than guess. The scheme variant set is a known, closed
list, so this rule is deterministic with no live data.

Scheme normalization is intentionally MORE aggressive than geo normalization
(:func:`normalize_geo_name`): a scheme label has no internal identity carried by spacing, so
"Mahatma Gandhi NREGA" and "MGNREGA" must collapse to the same token — whereas geography spacing
("North 24 Parganas") IS identity and is preserved.
"""

from __future__ import annotations

import re
from typing import Final

CANONICAL_SCHEME: Final = "MGNREGA"

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")

# Closed alias set, pre-normalized (uppercase, no spaces/punctuation). DATA_CONTRACT §2.1 /
# R3-SCHEME-01: the short forms plus the expanded Act/Scheme names.
_SCHEME_ALIASES: Final[frozenset[str]] = frozenset(
    {
        "NREGA",
        "MNREGA",
        "MGNREGA",
        "MGNREGS",
        "MAHATMAGANDHINREGA",
        "MAHATMAGANDHINREGS",
        "MAHATMAGANDHINATIONALRURALEMPLOYMENTGUARANTEEACT",
        "MAHATMAGANDHINATIONALRURALEMPLOYMENTGUARANTEESCHEME",
        "NATIONALRURALEMPLOYMENTGUARANTEEACT",
    }
)


def _normalize_scheme(label: str) -> str:
    return _NON_ALNUM.sub("", label.upper())


def resolve_scheme(label: str | None) -> str | None:
    """Resolve a scheme label to canonical ``MGNREGA``, or ``None`` if unknown."""
    if label is None:
        return None
    return CANONICAL_SCHEME if _normalize_scheme(label) in _SCHEME_ALIASES else None
