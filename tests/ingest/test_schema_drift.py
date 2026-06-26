"""T1.3 — schema-version / drift DETECTION (tests written first, per strict TDD).

Locked spec (CLAUDE.md TIER 1 + plan):
  * schema identity = OBSERVED column union (row keys), order-insensitive;
  * drift is comparable ONLY between two FULL pulls — a ``partial`` pull yields
    ``comparable=False`` (visibly distinct from ``detected=False``) and NEVER updates baseline;
  * the ledger stores the column SET (so ``removed`` is enumerable) plus ``pull_completeness``.

CONSTRAINT honoured here: ``pull_completeness`` is set EXPLICITLY on every call — never
derived from a fixture ``count``/``total`` (hand-edited, unfaithful). These tests use
synthetic column lists, not fixtures, precisely so completeness is a deliberate input.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from data_platform.ingest.schema import (
    SchemaLedger,
    detect_drift,
    fingerprint_schema,
)

AS_OF = datetime(2025, 3, 7, tzinfo=UTC)
INGESTED = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


# ------------------------------------------------------------------------------------
# Fingerprint + full-vs-full diff  (#1–#5)
# ------------------------------------------------------------------------------------
def test_same_column_set_even_reordered_is_same_version_no_drift() -> None:
    base = ["a", "b", "c"]
    reordered = ["c", "a", "b"]  # identical SET, different order
    assert fingerprint_schema(base) == fingerprint_schema(reordered)

    flag = detect_drift(base, reordered, baseline_completeness="full", current_completeness="full")
    assert flag.detected is False
    assert flag.comparable is True
    assert flag.added == []
    assert flag.removed == []
    assert flag.previous_version == flag.new_version


def test_added_column_flags_drift() -> None:
    flag = detect_drift(
        ["a", "b"], ["a", "b", "c"], baseline_completeness="full", current_completeness="full"
    )
    assert flag.detected is True
    assert flag.comparable is True
    assert flag.added == ["c"]
    assert flag.removed == []


def test_renamed_column_flags_both_add_and_remove() -> None:
    flag = detect_drift(
        ["a", "b"], ["a", "b_v2"], baseline_completeness="full", current_completeness="full"
    )
    assert flag.detected is True
    assert flag.added == ["b_v2"]
    assert flag.removed == ["b"]


def test_removed_column_is_named_in_removed() -> None:
    flag = detect_drift(
        ["a", "b", "c"], ["a", "c"], baseline_completeness="full", current_completeness="full"
    )
    assert flag.detected is True
    assert flag.removed == ["b"]  # the dropped column is enumerated, not just "something changed"
    assert flag.added == []


def test_disappearance_detected_even_when_current_is_strict_subset() -> None:
    # current ⊂ baseline (a whole column gone from every row) — the "smaller batch, no
    # error" gap from the T1.2 review. MUST still be detected.
    flag = detect_drift(
        ["a", "b", "c"], ["a", "b"], baseline_completeness="full", current_completeness="full"
    )
    assert flag.detected is True
    assert flag.removed == ["c"]
    assert flag.added == []


# ------------------------------------------------------------------------------------
# Partial-vs-full guard  (#8) — flag, never a false diff
# ------------------------------------------------------------------------------------
def test_partial_current_pull_is_incomparable_not_a_false_removal() -> None:
    # A partial pull that LOOKS like a removal (fewer columns) must NOT be diffed.
    flag = detect_drift(
        ["a", "b", "c"], ["a", "b"], baseline_completeness="full", current_completeness="partial"
    )
    assert flag.comparable is False
    assert flag.added == []
    assert flag.removed == []
    assert flag.detected is False


def test_partial_baseline_is_also_incomparable() -> None:
    # Symmetric: an under-observed baseline can't be trusted either.
    flag = detect_drift(
        ["a", "b"], ["a", "b", "c"], baseline_completeness="partial", current_completeness="full"
    )
    assert flag.comparable is False
    assert flag.added == []
    assert flag.removed == []


def test_comparable_false_is_visibly_distinct_from_detected_false() -> None:
    # "couldn't compare" (incomparable) != "compared, found no drift". Both have
    # detected=False, but they are NOT the same flag — comparable tells them apart.
    no_drift = detect_drift(
        ["a", "b"], ["a", "b"], baseline_completeness="full", current_completeness="full"
    )
    incomparable = detect_drift(
        ["a", "b"], ["a"], baseline_completeness="full", current_completeness="partial"
    )
    assert (no_drift.detected, no_drift.comparable) == (False, True)
    assert (incomparable.detected, incomparable.comparable) == (False, False)
    assert no_drift != incomparable


# ------------------------------------------------------------------------------------
# Ledger  (#6 set round-trip, #7 first ingest, #9 completeness round-trip, #10 no overwrite)
# ------------------------------------------------------------------------------------
def test_first_ingest_records_baseline_and_reports_no_drift(tmp_path: Path) -> None:
    ledger = SchemaLedger(root=tmp_path)
    flag = ledger.assess(
        source_id="SRC_X",
        columns=["a", "b"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert flag.detected is False
    assert flag.previous_version is None  # nothing came before

    base = ledger.baseline("SRC_X")
    assert base is not None
    assert set(base.columns) == {"a", "b"}


def test_ledger_round_trips_column_set_so_removed_is_enumerable(tmp_path: Path) -> None:
    SchemaLedger(root=tmp_path).assess(
        source_id="SRC_X",
        columns=["a", "b", "c"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    # A FRESH ledger reads the baseline back from disk — proving the SET (not just the
    # one-way hash) was persisted, which is the only way the next ``removed`` is nameable.
    reloaded = SchemaLedger(root=tmp_path)
    flag = reloaded.assess(
        source_id="SRC_X",
        columns=["a", "c"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert flag.removed == ["b"]


def test_ledger_records_and_round_trips_pull_completeness(tmp_path: Path) -> None:
    SchemaLedger(root=tmp_path).assess(
        source_id="SRC_X",
        columns=["a", "b"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    base = SchemaLedger(root=tmp_path).baseline("SRC_X")
    assert base is not None
    assert base.pull_completeness == "full"


def test_partial_pull_never_overwrites_the_full_baseline(tmp_path: Path) -> None:
    ledger = SchemaLedger(root=tmp_path)
    ledger.assess(  # full baseline: a, b, c
        source_id="SRC_X",
        columns=["a", "b", "c"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    ledger.assess(  # a PARTIAL slice (a, b) — must NOT replace the full baseline
        source_id="SRC_X",
        columns=["a", "b"],
        pull_completeness="partial",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    # The next FULL pull must diff against the ORIGINAL full baseline (a, b, c), not the
    # under-observed slice (a, b). If the partial had overwritten it, the drop of ``c``
    # would be invisible here.
    flag = ledger.assess(
        source_id="SRC_X",
        columns=["a", "b", "d"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert flag.detected is True
    assert flag.removed == ["c"]
    assert flag.added == ["d"]


def test_partial_first_baseline_is_upgraded_by_a_later_full_pull(tmp_path: Path) -> None:
    # Invariant: a partial FIRST pull must not lock the source out forever. It records a
    # baseline (so there is something on record), but the first full pull upgrades it.
    ledger = SchemaLedger(root=tmp_path)

    # 1) First-ever pull is PARTIAL -> baseline recorded, nothing to compare, no drift.
    first = ledger.assess(
        source_id="SRC_Y",
        columns=["a", "b"],
        pull_completeness="partial",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert first.detected is False
    assert first.comparable is True
    assert first.previous_version is None
    base1 = ledger.baseline("SRC_Y")
    assert base1 is not None
    assert base1.pull_completeness == "partial"
    assert set(base1.columns) == {"a", "b"}

    # 2) First FULL pull. (a) Diffing against a PARTIAL baseline can't be trusted ->
    # comparable=False, no diff emitted. (b) But the full pull UPGRADES the baseline.
    second = ledger.assess(
        source_id="SRC_Y",
        columns=["a", "b", "c"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert second.comparable is False
    assert second.added == []
    assert second.removed == []
    base2 = ledger.baseline("SRC_Y")
    assert base2 is not None
    assert base2.pull_completeness == "full"  # upgraded from partial to full
    assert set(base2.columns) == {"a", "b", "c"}

    # 3) Next FULL pull now diffs CLEANLY against the upgraded full baseline {a,b,c}.
    # added == ["d"] proves it compared against {a,b,c}; it would be ["c","d"] if it had
    # wrongly compared against the original partial baseline {a,b}.
    third = ledger.assess(
        source_id="SRC_Y",
        columns=["a", "b", "c", "d"],
        pull_completeness="full",
        source_as_of=AS_OF,
        ingested_at=INGESTED,
    )
    assert third.comparable is True
    assert third.detected is True
    assert third.added == ["d"]
    assert third.removed == []
