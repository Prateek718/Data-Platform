"""Checksum gate + in-memory DuckDB loader for the sealed v1.0 release artifacts.

At startup the server verifies every file in the committed :data:`SHA256SUMS.txt` manifest against
the bytes in ``dist/v1.0`` and refuses to start on any mismatch or missing file (naming the file and
the expected/actual digest). Only then are the three data Parquet files and ``lineage.jsonl`` loaded
into an in-memory DuckDB (four tables; ``lineage`` carries the raw provenance JSON keyed by
``fact_id``). No persistent DB file, no network — the released bytes are the sole source of truth.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

_MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _MODULE_DIR.parents[2]
DEFAULT_DIST_DIR = REPO_ROOT / "dist" / "v1.0"
DEFAULT_MANIFEST = _MODULE_DIR / "SHA256SUMS.txt"

# Logical table name -> the Parquet artifact it loads from.
_PARQUET_TABLES = {
    "state_annual_series": "state_annual_series.parquet",
    "national_annual_series": "national_annual_series.parquet",
    "district_flagship": "district_flagship.parquet",
}
_LINEAGE_TABLE = "lineage"
_LINEAGE_FILE = "lineage.jsonl"

_READ_CHUNK = 1 << 20


class ArtifactError(RuntimeError):
    """A release artifact failed the startup integrity gate."""


class MissingArtifactError(ArtifactError):
    """A file named in the manifest is absent from the dist directory."""


class ChecksumMismatchError(ArtifactError):
    """A file's SHA-256 does not match its manifest digest."""


@dataclass(frozen=True)
class Dataset:
    """A loaded, checksum-verified dataset: the DuckDB connection and per-table row counts."""

    con: duckdb.DuckDBPyConnection
    row_counts: dict[str, int]

    def close(self) -> None:
        self.con.close()


def parse_manifest(path: Path) -> dict[str, str]:
    """Parse a ``<sha256>  <filename>`` manifest into ``{filename: digest}``.

    Blank lines and lines beginning with ``#`` (the provenance header) are ignored.
    """
    manifest: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, name = line.partition("  ")
        manifest[name.strip()] = digest.strip()
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifacts(dist_dir: Path, manifest_path: Path) -> None:
    """Verify every manifest entry against ``dist_dir``; raise on the first missing/mismatched file.

    Files are checked in sorted name order so the failure reported is deterministic.
    """
    manifest = parse_manifest(manifest_path)
    for name in sorted(manifest):
        expected = manifest[name]
        path = dist_dir / name
        if not path.is_file():
            raise MissingArtifactError(
                f"release artifact missing: {name} (expected under {dist_dir})"
            )
        actual = _sha256(path)
        if actual != expected:
            raise ChecksumMismatchError(
                f"checksum mismatch for {name}: expected {expected}, actual {actual}"
            )


def load_dataset(
    *, dist_dir: Path = DEFAULT_DIST_DIR, manifest_path: Path = DEFAULT_MANIFEST
) -> Dataset:
    """Verify the artifacts, then load them into a fresh in-memory DuckDB and return the dataset."""
    verify_artifacts(dist_dir, manifest_path)

    con = duckdb.connect(":memory:")
    row_counts: dict[str, int] = {}
    for table, filename in _PARQUET_TABLES.items():
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_parquet(?)",
            [str(dist_dir / filename)],
        )
        row_counts[table] = _count(con, table)

    con.execute(
        f"CREATE TABLE {_LINEAGE_TABLE} AS "
        "SELECT json->>'fact_id' AS fact_id, json AS record FROM read_ndjson_objects(?)",
        [str(dist_dir / _LINEAGE_FILE)],
    )
    row_counts[_LINEAGE_TABLE] = _count(con, _LINEAGE_TABLE)

    return Dataset(con=con, row_counts=row_counts)


def _count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    result = con.execute(f"SELECT count(*) FROM {table}").fetchone()
    assert result is not None
    return int(result[0])
