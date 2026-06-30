"""R3-GEO-03 — curated geography alias tables (config-carried, not inferred).

The maintained variant→canonical lookups the resolver consults when conservative normalization
(R3-GEO-01/02) does not produce an exact LGD match. Keys are the NORMALIZED flagship name
(:func:`normalize_geo_name` applied), values are the target LGD English name (also normalized at
load). Every entry is a HAND-VERIFIED fact: each target was confirmed present in the archived LGD
reference before being added (a guarding test re-checks this). Putting these in an explicit,
auditable table — rather than in cleverer normalization code — is deliberate: it keeps R3-GEO-01
conservative so it can never silently merge two distinct places (R3-GEO-05).

DISTRICT_ALIASES land with district resolution (T3.4).
"""

from __future__ import annotations

from typing import Final

# Flagship state-name variants that R3-GEO-02 misses. Two observed:
#   "DN HAVELI AND DD"     — heavy abbreviation (R3-GEO-01 docstring example)
#   "ANDAMAN AND NICOBAR"  — flagship drops the "Islands" suffix LGD carries
STATE_ALIASES: Final[dict[str, str]] = {
    "dn haveli and dd": "the dadra and nagar haveli and daman and diu",
    "andaman and nicobar": "andaman and nicobar islands",
}
