"""Carry one wired resource from the offline archive to a resolved state (or an honest defer).

Ties the pieces together per resource: read the archived file → Stage-2 normalize (with reshape)
→ Stage-3 resolve, all with the resource's own config injected. If the general machinery raises on
a resource (a spec that does not fit it cleanly), the failure is caught and returned as a runtime
deferral WITH the reason — a dataset that cannot be wired is preserved and flagged, never dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from data_platform.ingest.archive import read_archive_batch
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.models import ResolvedBatch
from data_platform.resolve.pipeline import resolve_batch
from data_platform.wiring.specs import WiredResource

ARCHIVE_ROOT = Path("data/archive")


@dataclass(frozen=True)
class WiringOutcome:
    """The result of wiring one resource: either a resolved batch, or a runtime deferral reason.

    ``resolved`` and ``normalized_rows`` are set on success; ``deferred_reason`` on failure.
    Exactly one side is populated, so a resource is always accounted for (zero data loss).
    """

    resource_id: str
    resolved: ResolvedBatch | None
    normalized_rows: int
    deferred_reason: str | None

    @property
    def is_resolved(self) -> bool:
        return self.resolved is not None


def wire_resource(
    resource: WiredResource, resolver: GeoResolver, *, archive_root: Path = ARCHIVE_ROOT
) -> WiringOutcome:
    """Run one wired resource through ingest → normalize → resolve; defer on any failure."""
    try:
        batch = read_archive_batch(
            resource_id=resource.resource_id,
            source_id=resource.source_id,
            source_grain=resource.source_grain,
            path=archive_root / resource.file,
        )
        normalized = normalize_batch(batch, config=resource.normalize_config)
        resolved = resolve_batch(normalized, resolver, config=resource.resolve_config)
    except Exception as exc:  # noqa: BLE001 - any failure becomes an honest deferral, never a drop
        return WiringOutcome(
            resource_id=resource.resource_id,
            resolved=None,
            normalized_rows=0,
            deferred_reason=f"runtime wiring error: {type(exc).__name__}: {exc}",
        )
    return WiringOutcome(
        resource_id=resource.resource_id,
        resolved=resolved,
        normalized_rows=len(normalized.records),
        deferred_reason=None,
    )
