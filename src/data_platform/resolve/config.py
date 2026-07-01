"""Stage 3 config — carried, not hardcoded inline (CLAUDE.md CONVENTIONS).

Per-RESOURCE inputs the resolution pipeline consumes: the geographic grain of the resource, which
source columns hold the geography fields (when any), and the scheme it publishes. Keyed by
``resource_id`` — NOT ``source_id`` — because one source (e.g. Rajya Sabha, ~96 resources) publishes
many resources with divergent shapes and grains; config that varies per resource cannot key on the
coarse source. ``source_id`` remains coarse provenance only. Nothing here invents schema —
column names are Stage-0 observed facts.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID
from data_platform.resolve.models import GeoLevel


class GeoColumns(BaseModel):
    """Which source columns carry the geography fields the resolver reads.

    ``state_name`` is always required for a geo-anchored (state/district) resource — identity is a
    NAME join (source codes are source-internal, not LGD; DATA_CONTRACT §2.2). ``state_code`` and
    the district columns are optional: a state-grain resource has no district columns, and some
    resources carry no source code to record in lineage. A national-grain resource has no
    :class:`GeoColumns` at all (``geo_columns=None`` on its config).
    """

    model_config = ConfigDict(strict=True, frozen=True)

    state_name: str
    state_code: str | None = None
    district_name: str | None = None
    district_code: str | None = None


class ResourceResolveConfig(BaseModel):
    """The Stage-3 config for ONE resource: its grain, scheme, and geography columns.

    ``geo_columns`` is required for ``STATE``/``DISTRICT`` grain and MUST be ``None`` for
    ``NATIONAL`` (a national row has no geography to resolve — R3-GEO-04). This invariant is
    enforced at construction so a misconfigured resource fails loudly, never silently mis-resolves.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    geo_level: GeoLevel
    scheme_label: str
    geo_columns: GeoColumns | None = None

    def model_post_init(self, _context: object) -> None:
        national = self.geo_level is GeoLevel.NATIONAL
        if national and self.geo_columns is not None:
            raise ValueError("national-grain resource must not declare geo_columns")
        if not national and self.geo_columns is None:
            raise ValueError(f"{self.geo_level} resource must declare geo_columns")
        if (
            self.geo_level is GeoLevel.DISTRICT
            and self.geo_columns is not None
            and self.geo_columns.district_name is None
        ):
            raise ValueError("district-grain resource must declare a district_name column")


# Flagship geography columns (Stage-0 verbatim). Codes are source-internal (MIS) and used only for
# lineage (source_code → lgd_code); identity is resolved from the names.
_FLAGSHIP: Final = ResourceResolveConfig(
    geo_level=GeoLevel.DISTRICT,
    scheme_label="MGNREGA",  # the flagship carries no scheme column — the dataset IS MGNREGA
    geo_columns=GeoColumns(
        state_name="state_name",
        state_code="state_code",
        district_name="district_name",
        district_code="district_code",
    ),
)

# Per-resource Stage-3 config, keyed by resource_id. Grows as sources are wired (Stage 3.5).
RESOLVE_CONFIG: Final[dict[str, ResourceResolveConfig]] = {
    FLAGSHIP_RESOURCE_ID: _FLAGSHIP,
}
