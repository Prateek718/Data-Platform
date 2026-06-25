"""The source-agnostic ingestion seam: :class:`SourceAdapter` + :class:`SourcePayload`.

A NEW source is a NEW :class:`SourceAdapter` subclass with its own ``parse`` — never a
rewrite of an existing adapter (the scheme/source-agnostic claim, BUILD_SEQUENCE T1.2).

``parse`` is PURE: an already-fetched :class:`SourcePayload` in, a
:class:`~data_platform.ingest.landing.RawLandingBatch` out. No network, no disk. All
side effects live in ``transport.py`` (the only impure ingestion module); adapters never
import it. Decoupling parse from fetch is what makes ingestion unit-testable and hermetic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from data_platform.ingest.landing import RawLandingBatch


@dataclass(frozen=True)
class SourcePayload:
    """One already-fetched payload handed to an adapter's ``parse``.

    ``raw`` is source-specific (the data.gov.in response envelope for flagship/RS, or
    whatever shape a future adapter defines). ``source_as_of`` is extracted from the
    response metadata by ``transport`` — for data.gov.in that is the envelope-level
    ``updated_date`` (a single value for the whole batch; Stage 0 confirmed it never
    appears per-record) — so ``parse`` receives provenance rather than discovering it.
    """

    resource_id: str
    fetched_at: datetime
    source_as_of: datetime | None
    raw: Any


class SourceAdapter(ABC):
    """Shared, source-agnostic interface. Implement ``parse`` (pure) and the three ClassVars."""

    source_id: ClassVar[str]
    resource_ids: ClassVar[Sequence[str]]
    source_grain: ClassVar[str]

    @abstractmethod
    def parse(self, payload: SourcePayload) -> RawLandingBatch:
        """Pure transform: ``SourcePayload`` -> ``RawLandingBatch``. No I/O."""
        ...
