"""SRC_FLAGSHIP adapter — ``District-wise MGNREGA Data at a Glance`` (district + monthly).

Pure parse: the data.gov.in response envelope in, a :class:`RawLandingBatch` out. Every
source column is kept verbatim (Stage 0 observed 36), cells are stored exactly as emitted
(flagship publishes everything as strings — ``"NA"`` and numerics alike — so nothing is
coerced here), and duplicate snapshot rows are preserved un-deduped (dedupe is Stage 2).
"""

from __future__ import annotations

from typing import ClassVar

from data_platform.ingest import registry
from data_platform.ingest.adapters.base import (
    SourceAdapter,
    SourcePayload,
    observed_columns,
    schema_fingerprint,
)
from data_platform.ingest.landing import RawLandingBatch, build_batch


class FlagshipAdapter(SourceAdapter):
    source_id: ClassVar[str] = registry.SRC_FLAGSHIP
    resource_ids: ClassVar[list[str]] = [registry.FLAGSHIP_RESOURCE_ID]
    source_grain: ClassVar[str] = registry.FLAGSHIP_GRAIN

    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        rows = payload.raw[registry.DATAGOVIN_RECORDS_FIELD]
        column_names = observed_columns(rows)
        return build_batch(
            source_id=self.source_id,
            resource_id=payload.resource_id,
            ingested_at=payload.fetched_at,
            source_as_of=payload.source_as_of,
            schema_version=schema_fingerprint(column_names),
            source_grain=self.source_grain,
            pull_completeness=payload.pull_completeness,
            column_names=column_names,
            rows=rows,
        )
