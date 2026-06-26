"""Schema-version fingerprinting and drift DETECTION (Stage 1 T1.3) — detect + tag only.

Schema identity is the OBSERVED column union (row keys), NOT the envelope's declared
``field[]`` — Stage 0 found data.gov.in's declared metadata unreliable (it declares long
types for decimal-string values), so drift is verified against the DATA. The fingerprint is
order-insensitive (a reordered-but-identical schema is the same version) and is the very
string stamped on each batch as ``schema_version`` — so we reuse the one implementation
(:func:`fingerprint_schema`) rather than maintaining a second, divergence-prone hash.

HARD PRECONDITION — compare FULL pulls only. A ``partial`` pull (a filtered/truncated slice)
under-observes sparse columns and would false-flag added/removed against a fuller baseline.
So :func:`detect_drift` diffs ONLY when both sides are ``full``; otherwise it returns a flag
with ``comparable=False`` and an empty diff — flagging "couldn't compare" rather than emitting
a fiction. The :class:`SchemaLedger` enforces the partner rule: only a ``full`` pull may
UPDATE the baseline; a ``partial`` pull is recorded for audit but never overwrites it (which
would corrupt the next full comparison into a false ``added``).

Detect + tag only — nothing here rejects an ingest. Full drift HANDLING is Stage 2.
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
_LEDGER_FILENAME = "_schema_history.json"


class LedgerEntry(BaseModel):
    """One recorded schema observation — the persisted unit of the interim ledger.

    Stores the column **SET** (the list — not just the fingerprint) so a later ``removed``
    is enumerable: a sha256 proves *that* the schema changed but, being one-way, cannot say
    *which* column vanished. Also stores ``pull_completeness`` so the compare-full-pulls-only
    rule is checkable on the next ingest. Not ``strict`` (unlike the landing models): this is
    metadata we own and must round-trip through JSON, so datetime<->ISO coercion on load is wanted.
    """

    model_config = ConfigDict(frozen=True)

    columns: list[str]
    fingerprint: str
    pull_completeness: PullCompleteness
    source_as_of: datetime | None
    ingested_at: datetime


class _LedgerState(BaseModel):
    """On-disk shape: the current baseline plus an append-only audit trail of every pull."""

    model_config = ConfigDict(frozen=True)

    baseline: LedgerEntry | None = None
    history: list[LedgerEntry] = []


def detect_drift(
    baseline_columns: Sequence[str],
    current_columns: Sequence[str],
    *,
    baseline_completeness: PullCompleteness,
    current_completeness: PullCompleteness,
) -> DriftFlag:
    """Compare two observed column sets → :class:`DriftFlag`.

    When BOTH pulls are ``full``: ``added = current − baseline``, ``removed = baseline −
    current`` (both sorted for determinism); ``detected`` is true iff either is non-empty —
    so a disappearance (current a strict subset of baseline) is detected, with the dropped
    column named. When either side is not ``full`` the scopes are incomparable: the diff is
    suppressed (``added``/``removed`` empty, ``detected=False``) and ``comparable=False``.
    """
    previous_version = fingerprint_schema(baseline_columns)
    new_version = fingerprint_schema(current_columns)

    if baseline_completeness != "full" or current_completeness != "full":
        return DriftFlag(
            detected=False,
            previous_version=previous_version,
            new_version=new_version,
            added=[],
            removed=[],
            comparable=False,
        )

    baseline_set = set(baseline_columns)
    current_set = set(current_columns)
    added = sorted(current_set - baseline_set)
    removed = sorted(baseline_set - current_set)
    return DriftFlag(
        detected=bool(added or removed),
        previous_version=previous_version,
        new_version=new_version,
        added=added,
        removed=removed,
        comparable=True,
    )


class SchemaLedger:
    """Per-source schema baseline with interim on-disk JSON persistence.

    One ``data/raw/<source_id>/_schema_history.json`` per source (``root`` is injectable so
    tests stay hermetic and never touch the live zone), superseded by the governed store
    later. The baseline is the last **FULL** pull's column set; ``assess`` compares a new
    pull against it and updates it only when the new pull is itself ``full``.
    """

    def __init__(self, root: Path = _DEFAULT_LEDGER_ROOT) -> None:
        self._root = root

    def _path(self, source_id: str) -> Path:
        return self._root / source_id / _LEDGER_FILENAME

    def _load(self, source_id: str) -> _LedgerState:
        path = self._path(source_id)
        if not path.exists():
            return _LedgerState()
        return _LedgerState.model_validate_json(path.read_text())

    def _save(self, source_id: str, state: _LedgerState) -> None:
        path = self._path(source_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(indent=2))

    def baseline(self, source_id: str) -> LedgerEntry | None:
        """The current baseline entry for a source, or ``None`` if never ingested."""
        return self._load(source_id).baseline

    def assess(
        self,
        *,
        source_id: str,
        columns: Sequence[str],
        pull_completeness: PullCompleteness,
        source_as_of: datetime | None,
        ingested_at: datetime,
    ) -> DriftFlag:
        """Compare a new pull against the baseline, update it (full pulls only), persist.

        First ingest for a source establishes the baseline (regardless of completeness) and
        reports no drift. Thereafter the new pull is diffed against the baseline; the
        baseline is replaced only when the new pull is ``full`` — a ``partial`` pull is kept
        in ``history`` for audit but never overwrites the baseline.
        """
        state = self._load(source_id)
        current = LedgerEntry(
            columns=list(columns),
            fingerprint=fingerprint_schema(columns),
            pull_completeness=pull_completeness,
            source_as_of=source_as_of,
            ingested_at=ingested_at,
        )

        if state.baseline is None:
            flag = DriftFlag(
                detected=False,
                previous_version=None,
                new_version=current.fingerprint,
                added=[],
                removed=[],
                comparable=True,
            )
            new_baseline: LedgerEntry | None = current
        else:
            flag = detect_drift(
                state.baseline.columns,
                columns,
                baseline_completeness=state.baseline.pull_completeness,
                current_completeness=pull_completeness,
            )
            # Only a full pull may refresh the baseline; a partial slice never overwrites it.
            new_baseline = current if pull_completeness == "full" else state.baseline

        self._save(
            source_id,
            _LedgerState(baseline=new_baseline, history=[*state.history, current]),
        )
        return flag
