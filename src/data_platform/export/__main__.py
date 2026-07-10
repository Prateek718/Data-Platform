"""CLI: assemble the canonical series over the local archive and write the v1 deliverables.

    python -m data_platform.export                 # data/archive → dist/v1.0
    python -m data_platform.export <archive> <out>  # explicit paths

Deterministic: re-running over the same archive produces byte-identical CSV + JSONL.
"""

from __future__ import annotations

import sys
from pathlib import Path

from data_platform.export.build import build_export
from data_platform.export.write import write_all

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ARCHIVE = _REPO_ROOT / "data" / "archive"
_DEFAULT_OUT = _REPO_ROOT / "dist" / "v1.0"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    archive = Path(args[0]) if len(args) >= 1 else _DEFAULT_ARCHIVE
    out_dir = Path(args[1]) if len(args) >= 2 else _DEFAULT_OUT

    if not archive.exists():
        print(f"archive not found: {archive}", file=sys.stderr)
        return 1

    print(f"assembling canonical series from {archive} …")
    bundle = build_export(archive)
    counts = write_all(out_dir, bundle)
    print(f"wrote deliverables to {out_dir}:")
    for name, count in counts.items():
        print(f"  {name}: {count:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
