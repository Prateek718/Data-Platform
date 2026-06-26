"""Schema-version fingerprinting and drift DETECTION (Stage 1 T1.3) — detect + tag only.

STUB — behaviour lands in the T1.3 green commit. The public surface (signatures, the
:class:`SchemaLedger`, the persisted :class:`LedgerEntry`) is defined so the test module
and the type checker are happy; the drift logic raises ``NotImplementedError`` until
implemented, so the T1.3 tests are RED.

Schema identity is the OBSERVED column union (row keys), NOT the envelope's declared
``field[]`` — Stage 0 found data.gov.in's declared metadata unreliable, so drift is verified
against the data. Drift is comparable ONLY between two ``full`` pulls; a ``partial`` pull
under-observes sparse columns and is flagged ``comparable=False`` rather than diffed.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# The fingerprint IS the batch ``schema_version``; reuse the single implementation that
# already stamps batches rather than defining a second (divergence-prone) hash.
from data_platform.ingest.adapters.base import schema_fingerprint as fingerprint_schema
from data_platform.ingest.landing import DriftFlag, PullCompleteness

__all__ = ["LedgerEntry", "SchemaLedger", "detect_drift", "fingerprint_schema"]

_DEFAULT_LEDGER_ROOT = Path("data/raw")


class LedgerEntry(BaseModel):
    """One recorded schema observation — the persisted unit of the interim ledger.

    Stores the column **SET** (not just the fingerprint) so a later ``removed`` is
    enumerable, plus ``pull_completeness`` so the compare-full-pulls-only rule is checkable.
    Not ``strict`` (unlike the landing models): this is metadata we own and must round-trip
    through JSON, so datetime<->ISO coercion on load is wanted.
    """

    model_config = ConfigDict(frozen=True)

    columns: list[str]
    fingerprint: str
    pull_completeness: PullCompleteness
    source_as_of: datetime | None
    ingested_at: datetime


def detect_drift(
    baseline_columns: Sequence[str],
    current_columns: Sequence[str],
    *,
    baseline_completeness: PullCompleteness,
    current_completeness: PullCompleteness,
) -> DriftFlag:
    """Compare two observed column sets → :class:`DriftFlag`. STUB until T1.3 green."""
    raise NotImplementedError


class SchemaLedger:
    """Per-source schema baseline with interim on-disk JSON persistence. STUB until green."""

    def __init__(self, root: Path = _DEFAULT_LEDGER_ROOT) -> None:
        self._root = root

    def baseline(self, source_id: str) -> LedgerEntry | None:
        """The current baseline entry for a source, or ``None`` if never ingested."""
        raise NotImplementedError

    def assess(
        self,
        *,
        source_id: str,
        columns: Sequence[str],
        pull_completeness: PullCompleteness,
        source_as_of: datetime | None,
        ingested_at: datetime,
    ) -> DriftFlag:
        """Compare a new pull against the baseline, update it (full pulls only), persist."""
        raise NotImplementedError
