"""Transport — the ONLY impure ingestion module (network + disk live HERE, by design).

Adapters stay pure and never import this module; they receive an already-fetched
:class:`SourcePayload` and parse it. ``fetch_live`` does the bounded keyed pull (always
with an explicit ``limit`` — never ``limit=all``) and persists raw bytes to the
gitignored ``data/raw/`` landing zone; ``read_offline`` reconstructs a payload from disk
for hermetic/test runs. ``httpx`` is imported here — and nowhere under ``adapters/``.

STUB (T1.2): both functions are intentionally unimplemented until review.
"""

from __future__ import annotations

from pathlib import Path

import httpx  # noqa: F401  -- network impurity is centralized in THIS module, on purpose

from data_platform.ingest.adapters.base import SourceAdapter, SourcePayload


def fetch_live(adapter: SourceAdapter, resource_id: str, *, limit: int) -> SourcePayload:
    """Bounded keyed pull -> persist raw to ``data/raw/`` -> :class:`SourcePayload`."""
    raise NotImplementedError("T1.2/T1.4: transport.fetch_live not yet implemented")


def read_offline(adapter: SourceAdapter, path: Path) -> SourcePayload:
    """Read a previously-saved raw payload from disk -> :class:`SourcePayload`."""
    raise NotImplementedError("T1.2/T1.4: transport.read_offline not yet implemented")
