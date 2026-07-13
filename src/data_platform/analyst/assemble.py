"""The assembler — emits the report as a structured artifact plus a rendered read.

``report.json`` is the contract: sections, prose, and every figure as a typed object (value, unit,
metric, geography, period, fact_id, lineage) with each derived figure carrying its operation and
its input fact ids. ``report.md`` is the human read of the same content.

NOTE — the trace format is deliberately NOT final. How much of each figure's lineage the JSON
carries (the full payload embedded, or a reference the reader resolves live) is the presentation
decision the human makes at the Stage 8 checkpoint. Until then this emits the full payload, which
is the superset: it is what the fork-facts measurement needs, and either shape can be produced from
it without re-running the graph.
"""

from __future__ import annotations

from collections.abc import Sequence

from data_platform.analyst.models import VerifiedSection

REPORT_TITLE = "MGNREGA, 2006-2026: what the record says"


def build_report(sections: Sequence[VerifiedSection], *, generated_at: str) -> dict[str, object]:
    """The structured report artifact — the contract a viewer consumes."""
    raise NotImplementedError


def render_markdown(report: dict[str, object]) -> str:
    """The human read of the same report."""
    raise NotImplementedError
