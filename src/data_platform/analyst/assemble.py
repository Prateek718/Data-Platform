"""The assembler — emits the report as a structured artifact plus a rendered read.

``report.json`` is the contract: sections, prose, and every figure as a typed object (value, unit,
metric, geography, period, fact_id, lineage) with each derived figure carrying its operation and
its input fact ids. ``report.md`` is the human read of the same content.

Values are written as STRINGS, not JSON numbers: these are exact decimals, and a consumer that
parses 422.1806747 into a float and re-serializes it would not get the same figure back.

NOTE — the trace format is deliberately NOT final. How much of each figure's lineage the JSON
carries (the full payload embedded, or a reference a viewer resolves live) is the presentation
decision the human makes at the Stage 8 checkpoint. Until then this emits the full payload, which
is the superset: it is what the fork-facts measurement needs, and either shape can be produced from
it without re-running the graph.
"""

from __future__ import annotations

from collections.abc import Sequence

from data_platform.analyst.models import (
    Derivation,
    Figure,
    RefusalExhibit,
    RetrievedSection,
    VerifiedSection,
    canonical,
)

REPORT_TITLE = "MGNREGA, 2006-2026: what the record says"


def build_report(sections: Sequence[VerifiedSection], *, generated_at: str) -> dict[str, object]:
    """The structured report artifact — the contract a viewer consumes."""
    return {
        "title": REPORT_TITLE,
        "generated_at": generated_at,
        "dataset": {
            "name": "MGNREGA canonical series",
            "version": "v1.0.0",
            "doi": "10.5281/zenodo.21318431",
            "served_by": "data_platform.mcp (read-only MCP server over the sealed dist/v1.0)",
        },
        "verification": {
            "policy": (
                "Every number in the prose is a figure the dataset served or a derivation computed "
                "from such figures by code. Each was re-checked against the served data after "
                "drafting; a number that failed blocked its section."
            ),
            "figure_count": sum(len(s.retrieved.figures) for s in sections),
            "derivation_count": sum(len(s.retrieved.derivations) for s in sections),
        },
        "sections": [_section(s) for s in sections],
    }


def _section(section: VerifiedSection) -> dict[str, object]:
    retrieved = section.retrieved
    return {
        "key": retrieved.plan.key,
        "title": retrieved.plan.title,
        "prose": section.prose,
        "attempts": section.attempts,
        "figures": [_figure(f) for f in retrieved.figures],
        "derivations": [_derivation(d, retrieved) for d in retrieved.derivations],
        "refusals": [_refusal(r) for r in retrieved.refusals],
    }


def _figure(figure: Figure) -> dict[str, object]:
    return {
        "id": figure.id,
        "label": figure.label,
        "value": canonical(figure.value),
        "unit": figure.unit,
        "metric": figure.metric,
        "geography": figure.geography,
        "period": figure.period,
        "fact_id": figure.fact_id,
        "query": figure.query.to_dict(),
        "lineage": figure.lineage,
    }


def _derivation(derivation: Derivation, section: RetrievedSection) -> dict[str, object]:
    return {
        "id": derivation.id,
        "label": derivation.label,
        "operation": derivation.operation,
        "value": canonical(derivation.value),
        "unit": derivation.unit,
        "input_figure_ids": list(derivation.inputs),
        "input_fact_ids": section.fact_ids(derivation.id),
    }


def _refusal(refusal: RefusalExhibit) -> dict[str, object]:
    return {
        "id": refusal.id,
        "label": refusal.label,
        "call": refusal.call,
        "payload": refusal.payload,
    }


def render_markdown(report: dict[str, object]) -> str:
    """The human read of the same report."""
    sections = report["sections"]
    assert isinstance(sections, list)

    lines = [
        f"# {report['title']}",
        "",
        f"*Generated {report['generated_at']} from the MGNREGA canonical series v1.0.0 "
        f"(DOI 10.5281/zenodo.21318431), served read-only over MCP.*",
        "",
        "Every number below is a value the dataset served, or a figure derived from those values "
        "by deterministic code. Each was machine-checked against the served data after it was "
        "written; a number that failed to check blocked its section from the report.",
        "",
    ]

    for section in sections:
        lines += [f"## {section['title']}", "", str(section["prose"]).strip(), ""]

        figures = section["figures"]
        assert isinstance(figures, list)
        if figures:
            lines += [
                "| figure | value | unit | period | fact_id | sources |",
                "|---|---|---|---|---|---|",
            ]
            for figure in figures:
                sources = "; ".join(
                    f"{s.get('source_id')} ({s.get('resource_id')}, as of {s.get('as_of')})"
                    for s in _sources(figure)
                )
                lines.append(
                    f"| {figure['label']} | {figure['value']} | {figure['unit']} | "
                    f"{figure['period']} | `{figure['fact_id']}` | {sources} |"
                )
            lines.append("")

        derivations = section["derivations"]
        assert isinstance(derivations, list)
        if derivations:
            lines += ["| derived figure | operation | inputs | value |", "|---|---|---|---|"]
            for derivation in derivations:
                inputs = ", ".join(f"`{f}`" for f in derivation["input_fact_ids"])
                lines.append(
                    f"| {derivation['label']} | {derivation['operation']} | {inputs} | "
                    f"{derivation['value']} |"
                )
            lines.append("")

        refusals = section["refusals"]
        assert isinstance(refusals, list)
        for refusal in refusals:
            payload = refusal["payload"]
            assert isinstance(payload, dict)
            lines += [
                f"> **The record refuses:** `{refusal['call']}`",
                f"> → `{payload.get('code')}` — {payload.get('reason')}",
                "",
            ]

    return "\n".join(lines)


def _sources(figure: dict[str, object]) -> list[dict[str, object]]:
    lineage = figure.get("lineage")
    if not isinstance(lineage, dict):
        return []
    sources = lineage.get("sources")
    return [s for s in sources if isinstance(s, dict)] if isinstance(sources, list) else []
