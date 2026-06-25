"""SRC_RS adapter — Rajya Sabha person-days tables (state + annual), two resources.

STUB (T1.2): the seam is wired so tests import cleanly; ``parse`` is intentionally
unimplemented (behaviorally red) until the failing tests are reviewed. One instance is
bound to ONE resource_id: the two RS resources have different schemas and different
as-of dates, so each yields its OWN batch — they are never merged. When built, ``parse``
must quarantine the synthetic ``Total`` row via the ``build_batch`` quarantine predicate
as ``ParseFailureReason.SYNTHETIC_TOTAL_ROW`` (kept, not dropped, not passed through).
"""

from __future__ import annotations

from typing import ClassVar

from data_platform.ingest import registry
from data_platform.ingest.adapters.base import SourceAdapter, SourcePayload
from data_platform.ingest.landing import RawLandingBatch


class RajyaSabhaAdapter(SourceAdapter):
    source_id: ClassVar[str] = registry.SRC_RS
    resource_ids: ClassVar[list[str]] = registry.RS_RESOURCE_IDS
    source_grain: ClassVar[str] = registry.RS_GRAIN

    def __init__(self, resource_id: str) -> None:
        if resource_id not in self.resource_ids:
            raise ValueError(f"unknown SRC_RS resource_id: {resource_id!r}")
        self.resource_id = resource_id

    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        raise NotImplementedError("T1.2: RajyaSabhaAdapter.parse not yet implemented")
