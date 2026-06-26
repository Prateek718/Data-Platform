"""Transport — the ONLY impure ingestion module (network + disk live HERE, by design).

Adapters stay pure and never import this module; they receive an already-fetched
:class:`SourcePayload` and parse it. ``fetch_live`` does the bounded keyed pull (always
with an explicit positive ``limit`` — never ``limit=all``) and persists raw bytes to the
gitignored ``data/raw/`` landing zone; ``read_offline`` reconstructs a payload from disk
for hermetic/test runs. Both extract ``source_as_of`` from the envelope-level
``updated_date`` (the single batch-wide value Stage 0 confirmed). ``httpx`` is imported
here — and nowhere under ``adapters/``.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from data_platform.ingest import registry
from data_platform.ingest.adapters.base import SourceAdapter, SourcePayload
from data_platform.ingest.landing import PullCompleteness

_BASE_URL = "https://api.data.gov.in/resource"
_RAW_ROOT = Path("data/raw")
_API_KEY_ENV = "DATA_GOV_API_KEY"
_TIMEOUT_SECONDS = 60.0


def _source_as_of(envelope: dict[str, Any]) -> datetime | None:
    """Extract the envelope-level ``updated_date`` as the batch's source as-of date."""
    value = envelope.get(registry.DATAGOVIN_AS_OF_FIELD)
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def _resource_id_of(envelope: dict[str, Any], fallback: str) -> str:
    """data.gov.in echoes the resource id in ``index_name``; fall back if absent."""
    index_name = envelope.get("index_name")
    return index_name if isinstance(index_name, str) and index_name else fallback


def read_offline(
    adapter: SourceAdapter,
    path: Path,
    *,
    pull_completeness: PullCompleteness = "partial",
) -> SourcePayload:
    """Read a previously-saved raw payload from disk -> :class:`SourcePayload`.

    ``pull_completeness`` is DECLARED by the caller (default the fail-safe ``partial``):
    offline fixtures are trimmed slices, and the envelope's ``count`` is hand-edited and
    unfaithful, so completeness is never derived from it here — it is stated explicitly.
    """
    envelope = json.loads(path.read_text())
    return SourcePayload(
        resource_id=_resource_id_of(envelope, fallback=path.stem),
        fetched_at=datetime.now(UTC),
        source_as_of=_source_as_of(envelope),
        raw=envelope,
        pull_completeness=pull_completeness,
    )


def fetch_live(adapter: SourceAdapter, *, limit: int) -> list[SourcePayload]:
    """Bounded keyed pull of every resource the adapter owns -> persist -> payloads.

    One :class:`SourcePayload` per ``resource_id`` (so RS's two resources stay separate).
    ``limit`` must be a positive int — this is a bounded pull, never ``limit=all``.
    """
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"limit must be a positive int (bounded pull, never 'all'); got {limit!r}")

    key = _require_api_key()
    payloads: list[SourcePayload] = []
    with httpx.Client(timeout=_TIMEOUT_SECONDS, follow_redirects=True) as client:
        for resource_id in adapter.resource_ids:
            params = {"api-key": key, "format": "json", "limit": str(limit)}
            response = client.get(f"{_BASE_URL}/{resource_id}", params=params)
            response.raise_for_status()
            envelope = response.json()
            _persist_raw(adapter.source_id, resource_id, envelope)
            payloads.append(
                SourcePayload(
                    resource_id=resource_id,
                    fetched_at=datetime.now(UTC),
                    source_as_of=_source_as_of(envelope),
                    raw=envelope,
                )
            )
    return payloads


def _require_api_key() -> str:
    key = os.environ.get(_API_KEY_ENV)
    if not key:
        raise RuntimeError(f"{_API_KEY_ENV} is not set; live fetch needs a data.gov.in API key")
    return key


def _persist_raw(source_id: str, resource_id: str, envelope: dict[str, Any]) -> Path:
    """Land raw bytes verbatim under data/raw/<source_id>/<resource_id>/<utc-stamp>.json."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = _RAW_ROOT / source_id / resource_id / f"{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, indent=2))
    return out
