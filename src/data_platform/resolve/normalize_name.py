"""R3-GEO-01 — geo name normalization.

The conservative match key shared by state and district resolution. Deliberately minimal:
NFKD unicode fold, lowercase, expand ``&`` to the word ``and`` (the only token substitution —
``&`` and ``and`` are the SAME conjunction, so "Jammu & Kashmir" and "Jammu and Kashmir" are the
same name; without this ``&`` is stripped to nothing and the two forms diverge), strip everything
else that is not a letter or digit to a single space, and collapse runs of whitespace. That is ALL
— directional reorders ("24 Parganas North" vs "North 24 Parganas"), suffix stripping
("… District"), and spelling/transliteration fixes ("Bhatinda"→"Bathinda") are handled ONLY by the
explicit alias table (R3-GEO-03). Generic cleverness here would risk silently merging two distinct
places, the one thing R3-GEO-05 forbids; expanding ``&``→``and`` cannot — it only unifies two
spellings of one conjunction, never two different place names.

``None`` (a Stage-2 nulled cell) passes through as ``None`` — null is never coerced to "".
"""

from __future__ import annotations

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_geo_name(name: str | None) -> str | None:
    """Return the conservative normalized match key for a geography name, or ``None``."""
    if name is None:
        return None
    folded = unicodedata.normalize("NFKD", name).lower().replace("&", " and ")
    return _NON_ALNUM.sub(" ", folded).strip()
