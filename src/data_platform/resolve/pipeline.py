"""Stage 3 orchestrator — ``resolve_batch`` (stub; implemented next commit)."""

from __future__ import annotations

from data_platform.normalize.models import NormalizedBatch
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.models import ResolvedBatch


def resolve_batch(batch: NormalizedBatch, resolver: GeoResolver) -> ResolvedBatch:
    """Resolve a normalized batch to canonical scheme + geography identity."""
    return ResolvedBatch(
        source_id=batch.source_id,
        resource_id=batch.resource_id,
        ingested_at=batch.ingested_at,
        source_as_of=batch.source_as_of,
        schema_version=batch.schema_version,
        source_grain=batch.source_grain,
        pull_completeness=batch.pull_completeness,
        records=[],
        quarantined=[],
    )
