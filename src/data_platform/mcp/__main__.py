"""Entry point: ``uv run python -m data_platform.mcp``.

Loads the sealed v1.0 release artifacts through the checksum gate — which refuses to start on any
mismatch or missing file — then serves the five read-only tools over MCP stdio.
"""

from __future__ import annotations

from data_platform.mcp.loader import load_dataset
from data_platform.mcp.server import build_server


def main() -> None:
    # load_dataset is checksum-gated: it raises and refuses to start on any tampered/missing file.
    dataset = load_dataset()
    build_server(dataset).run()


if __name__ == "__main__":
    main()
