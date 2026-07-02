"""Stage 2 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

Per the registry pattern: the tunable inputs Stage 2 rules consume live here as named
constants, never as magic values inside the transforms. Grows per task (NULL_TOKENS for
R2-FMT-01; the column-type spec for R2-TYPE-01/R2-DATE-01; grain keys + dedupe id for
R2-DEDUP-01). Nothing here invents schema — column lists come from Stage 0 (sources.md).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID
from data_platform.normalize.reshape import ReshapeSpec

# R2-FMT-01 — tokens (compared case-insensitively after stripping) that mean "missing",
# mapped to null, NEVER zero. A whitespace-only / empty cell is also null (handled in fmt).
NULL_TOKENS: Final = frozenset({"NA", "-"})


class ColumnType(StrEnum):
    """The real type a source column is coerced/normalized to (Q4 — config-carried, not inferred).

    ``STRING`` covers identifiers (``state_code``/``district_code``) and free text — kept as
    ``str`` even when they look numeric. ``INT``/``DECIMAL`` are R2-TYPE-01's domain (Q6: counts
    int, money/rate Decimal); ``FY``/``MONTH`` are R2-DATE-01's domain (canonical strings, Q2).
    """

    STRING = "string"
    INT = "int"
    DECIMAL = "decimal"
    FY = "fy"
    MONTH = "month"


# R2-DATE-01 — month name/abbreviation (lowercased) -> canonical zero-padded "01".."12" (Q2).
_MONTH_NAMES: Final = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
MONTH_TO_CANONICAL: Final[dict[str, str]] = {
    **{name: f"{i:02d}" for i, name in enumerate(_MONTH_NAMES, start=1)},
    **{name[:3]: f"{i:02d}" for i, name in enumerate(_MONTH_NAMES, start=1)},
}

# Default for any column not in a source's spec: FMT-cleaned, kept as a string (typing the
# remaining columns is mechanical repetition, deferred like the 6-metric build order, Q4).
DEFAULT_COLUMN_TYPE: Final = ColumnType.STRING

# R2-DEDUP-01 active tie-break strategy id, recorded in lineage dedupe.tie_break_rule_id.
DEDUPE_TIE_BREAK_RULE_ID: Final = "R2-DEDUP-TB-01"


class ResourceNormalizeConfig(BaseModel):
    """The Stage-2 config for ONE resource: reshape rule, per-column types, grain-key columns.

    Keyed by ``resource_id`` (not ``source_id``): one source publishes many resources with
    divergent shapes/columns, so config must vary per resource. Column-type keys are the columns
    present AFTER reshape (so a melted resource types the synthesized ``_value``/``_fin_year``).
    Any column absent from ``column_types`` defaults to :data:`DEFAULT_COLUMN_TYPE` (STRING).
    """

    model_config = ConfigDict(strict=True, frozen=True)

    reshape: ReshapeSpec = ReshapeSpec()
    column_types: dict[str, ColumnType]
    grain_key_columns: list[str]


# Flagship column real-types (Q4/Q6). Keys are source column names (Stage 0, verbatim); names that
# look numeric but are identifiers stay STRING. The starter 3 metrics cover one type per
# harmonization shape (count/rate/money); other columns default to STRING for now.
_FLAGSHIP: Final = ResourceNormalizeConfig(
    column_types={
        "state_code": ColumnType.STRING,
        "district_code": ColumnType.STRING,
        "state_name": ColumnType.STRING,
        "district_name": ColumnType.STRING,
        "fin_year": ColumnType.FY,
        "month": ColumnType.MONTH,
        "Persondays_of_Central_Liability_so_far": ColumnType.INT,
        "Average_Wage_rate_per_day_per_person": ColumnType.DECIMAL,
        "Total_Exp": ColumnType.DECIMAL,
        "Remarks": ColumnType.STRING,
    },
    grain_key_columns=["state_code", "district_code", "fin_year", "month"],
)

# Per-resource Stage-2 config, keyed by resource_id. Grows as sources are wired (Stage 3.5).
NORMALIZE_CONFIG: Final[dict[str, ResourceNormalizeConfig]] = {
    FLAGSHIP_RESOURCE_ID: _FLAGSHIP,
}
