"""T2.5 — R2-DEDUP-01 intra-batch snapshot dedupe (tests first, red checkpoint).

Row-atomic (Q3): one winner per grain key, kept whole. Tie-break R2-DEDUP-TB-01 — latest
source_as_of, ties -> last-in-file. All-null grain key -> MISSING_GRAIN_KEY quarantine; partial
key passes through. Lineage = collapse count + collapsed indexes only. Every invariant guarded.
"""

from __future__ import annotations

from datetime import UTC, datetime

from data_platform.normalize.dedupe import DedupeCandidate, dedupe
from data_platform.normalize.models import NormalizationQuarantineReason

TB = "R2-DEDUP-TB-01"
T_EARLY = datetime(2026, 1, 1, tzinfo=UTC)
T_LATE = datetime(2026, 6, 1, tzinfo=UTC)


def _cand(
    row_index: int, key: tuple[str | None, ...], as_of: datetime | None = T_EARLY
) -> DedupeCandidate:
    return DedupeCandidate(row_index=row_index, raw={"k": key[0]}, key=key, source_as_of=as_of)


def test_distinct_keys_all_survive_in_order_no_collapse() -> None:
    cands = [_cand(0, ("10", "Jan")), _cand(1, ("10", "Feb"))]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [0, 1]
    assert result.quarantined == []
    assert result.lineage.duplicates_collapsed == 0
    assert result.lineage.collapsed_row_indexes == []
    assert result.lineage.tie_break_rule_id == TB


def test_equal_as_of_tie_breaks_to_last_in_file() -> None:
    # the golden snapshot case: same key + same batch source_as_of -> keep the later row.
    cands = [_cand(0, ("10", "Jan")), _cand(1, ("10", "Jan"))]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [1]
    assert result.lineage.duplicates_collapsed == 1
    assert result.lineage.collapsed_row_indexes == [0]


def test_latest_source_as_of_wins_regardless_of_file_order() -> None:
    # row 0 is later-as_of than row 1: latest as_of wins even though it is first in file.
    cands = [_cand(0, ("10", "Jan"), as_of=T_LATE), _cand(1, ("10", "Jan"), as_of=T_EARLY)]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [0]
    assert result.lineage.collapsed_row_indexes == [1]


def test_null_as_of_falls_back_to_last_in_file() -> None:
    cands = [_cand(0, ("10", "Jan"), as_of=None), _cand(1, ("10", "Jan"), as_of=None)]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [1]


def test_three_duplicates_collapse_to_one() -> None:
    cands = [_cand(0, ("10", "Jan")), _cand(1, ("10", "Jan")), _cand(2, ("10", "Jan"))]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [2]
    assert result.lineage.duplicates_collapsed == 2
    assert result.lineage.collapsed_row_indexes == [0, 1]


def test_all_null_grain_key_is_quarantined_not_deduped() -> None:
    cands = [_cand(0, (None, None)), _cand(1, ("10", "Jan"))]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [1]
    assert len(result.quarantined) == 1
    fail = result.quarantined[0]
    assert fail.row_index == 0
    assert fail.reason is NormalizationQuarantineReason.MISSING_GRAIN_KEY
    # a quarantined missing-key row is NOT counted as a collapsed duplicate
    assert result.lineage.duplicates_collapsed == 0


def test_partial_key_passes_through_un_quarantined() -> None:
    # some keys present -> has identity -> not Stage 2's quarantine (Stage 5's concern).
    cands = [_cand(0, (None, "Jan")), _cand(1, ("10", "Jan"))]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [0, 1]
    assert result.quarantined == []


def test_survivors_sorted_ascending_across_groups() -> None:
    cands = [
        _cand(0, ("10", "Jan")),
        _cand(1, ("10", "Feb")),
        _cand(2, ("10", "Jan")),  # dup of row 0's key -> row 2 wins (last-in-file)
    ]
    result = dedupe(cands, tie_break_rule_id=TB)
    assert result.surviving_row_indexes == [1, 2]
    assert result.lineage.collapsed_row_indexes == [0]
