"""Stage 3 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

Per-source inputs the resolution pipeline consumes: which source columns hold the geography
fields, and the scheme each source publishes. Kept here as named constants (mirrors
``normalize/config.py``) so the transform never embeds a magic source-column name or a magic
scheme literal. Nothing here invents schema — flagship column names are Stage-0 observed facts.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from data_platform.ingest.registry import SRC_FLAGSHIP


class GeoColumns(BaseModel):
    """Which source columns carry the geography fields the resolver reads."""

    model_config = ConfigDict(strict=True, frozen=True)

    state_code: str
    state_name: str
    district_code: str
    district_name: str


# Flagship geography columns (Stage-0 verbatim). Codes are source-internal (MIS) and used only
# for lineage (source_code → lgd_code); identity is resolved from the names.
SOURCE_GEO_COLUMNS: Final[dict[str, GeoColumns]] = {
    SRC_FLAGSHIP: GeoColumns(
        state_code="state_code",
        state_name="state_name",
        district_code="district_code",
        district_name="district_name",
    ),
}

# The scheme each source publishes. The flagship carries no scheme column — the dataset IS
# MGNREGA — so its scheme label is declared here and run through R3-SCHEME-01 like any other,
# keeping the rule (and its lineage) on the uniform path rather than special-casing the constant.
SOURCE_SCHEME: Final[dict[str, str]] = {SRC_FLAGSHIP: "MGNREGA"}
