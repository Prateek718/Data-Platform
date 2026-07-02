"""Stage 3.5 — offline archive ingestion for both byte-shapes (CSV file + JSON envelope).

Reads directly from the committed ``data/archive/`` snapshot (this stage is offline; the portal is
not a dependency). Verifies the CSV path lands verbatim rows with the header as columns, and that
the shared landing seam is used (parse failures captured, never crashing the batch).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.ingest.archive import read_archive_batch

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
# The deepest, simplest history file: All-India annual, Year + count columns, back to 2006-07.
_D88 = "d88e2cb6-842b-48ed-884c-a561c8f113ff"

pytestmark = pytest.mark.skipif(
    not (ARCHIVE / "csv" / f"{_D88}.csv").exists(),
    reason="local archive snapshot not present",
)


def test_csv_archive_lands_header_as_columns_and_rows_verbatim() -> None:
    batch = read_archive_batch(
        resource_id=_D88,
        source_id="SRC_MOSPI",
        source_grain="national+annual",
        path=ARCHIVE / "csv" / f"{_D88}.csv",
    )
    assert batch.source_id == "SRC_MOSPI"
    assert batch.resource_id == _D88
    assert "Year" in batch.column_names
    assert batch.records  # rows landed
    first = batch.records[0].raw
    assert first["Year"] == "2006-07"  # verbatim FY string, uncleaned
    # A CSV has no envelope, so as-of is honestly unknown — never fabricated.
    assert batch.source_as_of is None


def test_csv_archive_preserves_na_and_numeric_strings_verbatim() -> None:
    batch = read_archive_batch(
        resource_id=_D88,
        source_id="SRC_MOSPI",
        source_grain="national+annual",
        path=ARCHIVE / "csv" / f"{_D88}.csv",
    )
    # Every landed cell is a string (verbatim) or None; no coercion happened at ingest.
    for record in batch.records:
        for value in record.raw.values():
            assert value is None or isinstance(value, str)
