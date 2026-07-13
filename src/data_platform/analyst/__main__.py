"""Generate the MGNREGA report — the ONLY path in this repo that calls a live LLM.

Nothing in the test suite runs this: tests drive the graph with scripted fakes and never touch a
network. This script is invoked by hand, with an OpenAI-compatible chat-completions endpoint
configured in the environment:

    OPENROUTER_API_KEY=sk-...  PYTHONPATH=src uv run python -m data_platform.analyst

    # optional, both env-configurable (free-tier model ids churn):
    OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
    OPENROUTER_BASE_URL=https://openrouter.ai/api/v1     # any OpenAI-compatible endpoint

The drafter writes prose only from figures the retriever fetched from the served dataset, and the
deterministic verifier re-checks every number in that prose against the served data. If a section
cannot survive verification within the retry budget, this script writes NOTHING and exits non-zero,
printing the verifier's complaints — a weak model yields no report, never a wrong one.

Backends: `--backend stdio` (default) spawns the real MCP server as a subprocess and speaks the
protocol to it; `--backend direct` calls the same query core in-process (faster, identical
payloads — asserted by the backend-parity golden tests).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from data_platform.analyst import assemble, graph, sections
from data_platform.analyst.llm import OpenRouterDrafter
from data_platform.analyst.tools import AnalystTools, DirectTools, McpStdioTools
from data_platform.mcp import loader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sections",
        nargs="+",
        default=sorted(sections.SECTIONS),
        choices=sorted(sections.SECTIONS),
        help="which sections to generate (default: all registered sections)",
    )
    parser.add_argument(
        "--backend",
        choices=("stdio", "direct"),
        default="stdio",
        help="stdio spawns the real MCP server (default); direct calls the query core in-process",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("report"),
        help="directory for report.json and report.md (default: report/)",
    )
    args = parser.parse_args(argv)

    drafter = OpenRouterDrafter()
    print(f"drafter: {drafter!r}")
    print(f"sections: {', '.join(args.sections)}")
    print(f"backend: {args.backend}")

    started = time.perf_counter()
    if args.backend == "direct":
        dataset = loader.load_dataset()
        try:
            report = _run(DirectTools(dataset), drafter, args.sections)
        finally:
            dataset.close()
    else:
        with McpStdioTools() as tools:
            report = _run(tools, drafter, args.sections)
    elapsed = time.perf_counter() - started

    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / "report.json"
    md_path = args.out / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(assemble.render_markdown(report), encoding="utf-8")

    written = report["sections"]
    assert isinstance(written, list)
    print(f"\nVERIFIED {len(written)} section(s) in {elapsed:.1f}s — every number checked.")
    for section in written:
        print(f"  {section['key']}: {section['attempts']} drafting attempt(s)")
    print(f"\nwrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"wrote {md_path} ({md_path.stat().st_size:,} bytes)")
    return 0


def _run(tools: AnalystTools, drafter: OpenRouterDrafter, keys: list[str]) -> dict[str, object]:
    return graph.run(
        tools=tools,
        drafter=drafter,
        section_keys=keys,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except graph.VerificationFailure as failure:
        # The loud failure: the report is not written, and the verifier's complaints are the output.
        print(f"\nVERIFICATION FAILED — no report written.\n\n{failure}", file=sys.stderr)
        sys.exit(1)
