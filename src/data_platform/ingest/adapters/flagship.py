"""SRC_FLAGSHIP adapter — ``District-wise MGNREGA Data at a Glance`` (district + monthly).

STUB (T1.2): the seam is wired so tests import cleanly; ``parse`` is intentionally
unimplemented (behaviorally red) until the failing tests are reviewed. When built it
must keep all source columns verbatim (Stage 0 observed 36) and preserve duplicate
snapshot rows un-deduped (dedupe is Stage 2).
"""

from __future__ import annotations

from typing import ClassVar

from data_platform.ingest import registry
from data_platform.ingest.adapters.base import SourceAdapter, SourcePayload
from data_platform.ingest.landing import RawLandingBatch


class FlagshipAdapter(SourceAdapter):
    source_id: ClassVar[str] = registry.SRC_FLAGSHIP
    resource_ids: ClassVar[list[str]] = [registry.FLAGSHIP_RESOURCE_ID]
    source_grain: ClassVar[str] = registry.FLAGSHIP_GRAIN

    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        raise NotImplementedError("T1.2: FlagshipAdapter.parse not yet implemented")
