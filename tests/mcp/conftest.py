"""Fixtures for the MCP server tests.

``synthetic_dist`` materializes the tiny fixture dist (see ``tests/fixtures/synthetic_dist.py``)
into a tmp dir with its own real ``SHA256SUMS.txt`` — every unit test runs against it. Tests marked
``golden`` run against the real (gitignored) ``dist/v1.0`` and are skipped when it is absent, so the
default suite (and CI) stays green without the released artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from data_platform.mcp import loader
from tests.fixtures.synthetic_dist import build_synthetic_dist

_REAL_DIST_FILES = (
    "state_annual_series.parquet",
    "national_annual_series.parquet",
    "district_flagship.parquet",
    "lineage.jsonl",
)


def _real_dist_present() -> bool:
    return all((loader.DEFAULT_DIST_DIR / name).is_file() for name in _REAL_DIST_FILES)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker("golden") is not None and not _real_dist_present():
        pytest.skip("real dist/v1.0 not present; skipping golden test")


@dataclass(frozen=True)
class SyntheticDist:
    dir: Path
    manifest_path: Path
    counts: dict[str, int]


@pytest.fixture
def synthetic_dist(tmp_path: Path) -> SyntheticDist:
    dist_dir = tmp_path / "dist" / "v1.0"
    counts = build_synthetic_dist(dist_dir)
    return SyntheticDist(dir=dist_dir, manifest_path=dist_dir / "SHA256SUMS.txt", counts=counts)
