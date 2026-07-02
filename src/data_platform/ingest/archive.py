"""Offline archive ingestion — read a captured dataset (JSON envelope or file-only CSV) → batch.

Stage 3.5 builds against the local ``data/archive/`` snapshot, not the live portal. The archive
holds two byte-shapes: the data.gov.in JSON response envelope (``field`` + ``records``) and
file-only CSVs (header row + data rows). Both land through the ONE shared seam
(:func:`~data_platform.ingest.landing.build_batch`), so this module is the impure disk entry point
(analogous to ``transport.read_offline``) and the parsing stays verbatim: every cell is kept as the
source emitted it — ``"NA"`` stays ``"NA"``, numeric strings stay strings — with cleaning deferred
to Stage 2 (``null != 0``; no coercion at ingest).

Identity (``source_id``, ``source_grain``) is per-RESOURCE here, supplied by the caller from the
manifest/config, so ingestion needs no per-class adapter — a new dataset is a new config row, not
new code.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_platform.ingest.adapters.base import observed_columns, schema_fingerprint
from data_platform.ingest.landing import PullCompleteness, RawLandingBatch, build_batch

_RECORDS_FIELD = "records"
_AS_OF_FIELD = "updated_date"


def read_archive_batch(
    *,
    resource_id: str,
    source_id: str,
    source_grain: str,
    path: Path,
    pull_completeness: PullCompleteness = "full",
) -> RawLandingBatch:
    """Read one archived dataset file (``.json`` envelope or ``.csv``) into a landing batch."""
    if path.suffix == ".csv":
        columns, rows, source_as_of = _read_csv(path)
    elif path.suffix == ".json":
        columns, rows, source_as_of = _read_json_envelope(path)
    else:  # pragma: no cover - guarded so an unexpected extension fails loudly, never silently
        raise ValueError(f"unsupported archive file type: {path.name}")

    return build_batch(
        source_id=source_id,
        resource_id=resource_id,
        ingested_at=datetime.now(UTC),
        source_as_of=source_as_of,
        schema_version=schema_fingerprint(columns),
        source_grain=source_grain,
        pull_completeness=pull_completeness,
        column_names=columns,
        rows=rows,
    )


def _read_json_envelope(path: Path) -> tuple[list[str], list[Any], datetime | None]:
    envelope = json.loads(path.read_text())
    rows = envelope.get(_RECORDS_FIELD, [])
    as_of_raw = envelope.get(_AS_OF_FIELD)
    as_of = datetime.fromisoformat(as_of_raw) if isinstance(as_of_raw, str) and as_of_raw else None
    return observed_columns(rows), rows, as_of


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], None]:
    """Read a CSV to (header, row-dicts). Cells stay verbatim strings — Stage 2 does the cleaning.

    A file-only CSV carries no envelope, so it has no ``updated_date``; ``source_as_of`` is ``None``
    (honestly unknown), never fabricated.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return [], [], None
        columns = [cell.strip() for cell in header]
        rows = [dict(zip(columns, cells, strict=False)) for cells in reader]
    return columns, rows, None
