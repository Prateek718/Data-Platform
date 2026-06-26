"""Source registry — declared config observed in Stage 0 (NOT invented schema).

Ids, grain, and the per-resource quirks adapters need, kept here so nothing is a
hardcoded magic value inline (CLAUDE.md CONVENTIONS). Every value below is a fact
recorded in ``docs/notes/sources.md`` / ``docs/notes/divergence-findings.md``.
"""

from __future__ import annotations

from typing import Final

# --- source identities -------------------------------------------------------------
SRC_FLAGSHIP: Final = "SRC_FLAGSHIP"
SRC_RS: Final = "SRC_RS"

# --- SRC_FLAGSHIP (data.gov.in, district + monthly) --------------------------------
FLAGSHIP_RESOURCE_ID: Final = "ee03643a-ee4c-48c2-ac30-9f2ff26ab722"
FLAGSHIP_GRAIN: Final = "district+monthly"

# --- SRC_RS (Rajya Sabha, two resources, state + annual) ---------------------------
RS_RESOURCE_IDS: Final = [
    "cea6ee41-2b18-4266-b42b-0af54c13b18c",  # FY 2019-20 -> 2023-24, as-of 2025-03-07
    "e289a8fe-3fd4-4964-9579-5bddb88e36b8",  # FY 2021-22 -> 2023-24, as-of 2024-11-02
]
RS_GRAIN: Final = "state+annual"

# The two RS resources publish the state label under DIFFERENT column names (verbatim
# from Stage 0); the synthetic 'Total' pseudo-row is detected on this column. Because
# the name differs per resource, the Total-quarantine predicate cannot hardcode one.
RS_LABEL_COLUMN: Final = {
    "cea6ee41-2b18-4266-b42b-0af54c13b18c": "state_ut_wise",
    "e289a8fe-3fd4-4964-9579-5bddb88e36b8": "state_uts",
}
RS_TOTAL_LABEL: Final = "Total"  # the synthetic roll-up row's label, verbatim

# --- data.gov.in response envelope (shared by flagship + RS) ------------------------
# `updated_date` is envelope-level (one value per response, identical for the whole
# batch — Stage 0 confirmed it is absent from every record); `source_as_of` derives
# from it. Records live under `records`.
DATAGOVIN_AS_OF_FIELD: Final = "updated_date"
DATAGOVIN_RECORDS_FIELD: Final = "records"
