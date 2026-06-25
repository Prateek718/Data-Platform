"""SRC_RS adapter — Rajya Sabha person-days tables (state + annual), two resources.

Pure parse, one instance bound to ONE resource_id: the two RS resources have different
schemas and different as-of dates, so each yields its OWN batch — they are never merged.
The synthetic ``Total`` roll-up row is quarantined (kept, not dropped, not passed through)
via the ``build_batch`` quarantine predicate as ``SYNTHETIC_TOTAL_ROW``; the label column it
lives under differs per resource, so it is read from ``registry.RS_LABEL_COLUMN`` — never
hardcoded. Metric cells (JSON floats, declared "in lakh") are kept verbatim-typed; unit
normalization is Stage 4.
"""

from __future__ import annotations

from typing import Any, ClassVar

from data_platform.ingest import registry
from data_platform.ingest.adapters.base import (
    SourceAdapter,
    SourcePayload,
    observed_columns,
    schema_fingerprint,
)
from data_platform.ingest.landing import ParseFailureReason, RawLandingBatch, build_batch


class RajyaSabhaAdapter(SourceAdapter):
    source_id: ClassVar[str] = registry.SRC_RS
    resource_ids: ClassVar[list[str]] = registry.RS_RESOURCE_IDS
    source_grain: ClassVar[str] = registry.RS_GRAIN

    def __init__(self, resource_id: str) -> None:
        if resource_id not in self.resource_ids:
            raise ValueError(f"unknown SRC_RS resource_id: {resource_id!r}")
        self.resource_id = resource_id

    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        rows = payload.raw[registry.DATAGOVIN_RECORDS_FIELD]
        column_names = observed_columns(rows)
        label_column = registry.RS_LABEL_COLUMN[self.resource_id]

        def quarantine_total(row: dict[str, Any]) -> ParseFailureReason | None:
            if row.get(label_column) == registry.RS_TOTAL_LABEL:
                return ParseFailureReason.SYNTHETIC_TOTAL_ROW
            return None

        return build_batch(
            source_id=self.source_id,
            resource_id=payload.resource_id,
            ingested_at=payload.fetched_at,
            source_as_of=payload.source_as_of,
            schema_version=schema_fingerprint(column_names),
            source_grain=self.source_grain,
            column_names=column_names,
            rows=rows,
            quarantine=quarantine_total,
        )
