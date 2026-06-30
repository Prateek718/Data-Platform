"""R3-SCHEME-01 — scheme identity resolution.

Normalize a scheme label (uppercase, strip spaces/punctuation) and match against the closed
alias set of MGNREGA names → canonical ``"MGNREGA"``. No match → ``None`` (the caller quarantines
``unknown_scheme``). Lockable with no live data: the variant set is a known, closed list.
"""

from __future__ import annotations

import pytest

from data_platform.resolve.scheme import CANONICAL_SCHEME, resolve_scheme


@pytest.mark.parametrize(
    "label",
    [
        "MGNREGA",
        "NREGA",
        "MNREGA",
        "MGNREGS",
        "mgnrega",  # case-insensitive
        "Mahatma Gandhi NREGA",  # spaces stripped
        "Mahatma Gandhi National Rural Employment Guarantee Act",  # full act name
        "M.G.N.R.E.G.A.",  # punctuation stripped
        "  MGNREGA  ",  # trimmed
    ],
)
def test_known_aliases_resolve_to_mgnrega(label: str) -> None:
    assert resolve_scheme(label) == CANONICAL_SCHEME == "MGNREGA"


@pytest.mark.parametrize("label", ["PM-KISAN", "PMAY", "UNKNOWN SCHEME", "", "NREGAX"])
def test_unknown_scheme_returns_none(label: str) -> None:
    # No-match → None → caller quarantines unknown_scheme. Never a false positive.
    assert resolve_scheme(label) is None


def test_none_label_returns_none() -> None:
    assert resolve_scheme(None) is None
