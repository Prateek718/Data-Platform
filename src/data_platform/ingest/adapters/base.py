"""The source-agnostic ingestion seam: :class:`SourceAdapter` + :class:`SourcePayload`.

A NEW source is a NEW :class:`SourceAdapter` subclass with its own ``parse`` — never a
rewrite of an existing adapter (the scheme/source-agnostic claim, BUILD_SEQUENCE T1.2).

``parse`` is PURE: an already-fetched :class:`SourcePayload` in, a
:class:`~data_platform.ingest.landing.RawLandingBatch` out. No network, no disk. All
side effects live in ``transport.py`` (the only impure ingestion module); adapters never
import it. Decoupling parse from fetch is what makes ingestion unit-testable and hermetic.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from data_platform.ingest.landing import PullCompleteness, RawLandingBatch


@dataclass(frozen=True)
class SourcePayload:
    """One already-fetched payload handed to an adapter's ``parse``.

    ``raw`` is source-specific (the data.gov.in response envelope for flagship/RS, or
    whatever shape a future adapter defines). ``source_as_of`` is extracted from the
    response metadata by ``transport`` — for data.gov.in that is the envelope-level
    ``updated_date`` (a single value for the whole batch; Stage 0 confirmed it never
    appears per-record) — so ``parse`` receives provenance rather than discovering it.

    ``pull_completeness`` carries the batch's observed coverage (``full``/``partial``) set
    by ``transport`` (or declared on an offline read); ``parse`` copies it onto the batch.
    Defaults to the fail-safe ``partial`` so an un-tagged payload can never be mistaken for
    a comparable ``full`` pull in drift detection.
    """

    resource_id: str
    fetched_at: datetime
    source_as_of: datetime | None
    raw: Any
    pull_completeness: PullCompleteness = "partial"


class SourceAdapter(ABC):
    """Shared, source-agnostic interface. Implement ``parse`` (pure) and the three ClassVars."""

    source_id: ClassVar[str]
    resource_ids: ClassVar[Sequence[str]]
    source_grain: ClassVar[str]

    @abstractmethod
    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        """Pure transform: ``SourcePayload`` -> ``RawLandingBatch``. No I/O."""
        ...


def observed_columns(rows: Sequence[Any]) -> list[str]:
    """The observed schema: union of keys across mapping rows, in first-seen (source)
    order — verbatim, never sorted, never invented. Non-mapping rows are skipped here
    (``build_batch`` quarantines them as malformed); a column present in only some rows
    still appears, since landing fills its absence with null on the rows that lack it.
    """
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if isinstance(row, Mapping):
            for key in row:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
    return columns


def schema_fingerprint(column_names: Sequence[str]) -> str:
    """Deterministic, order-insensitive fingerprint of an observed column set, stamped on
    each batch as ``schema_version``. Order-insensitive so a reordered-but-identical schema
    hashes the same. Interim primitive: T1.3 builds schema-drift DETECTION on top of it.
    """
    digest = hashlib.sha256("\n".join(sorted(set(column_names))).encode()).hexdigest()
    return f"sha256:{digest}"
