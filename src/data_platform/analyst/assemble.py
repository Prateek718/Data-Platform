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
from typing import Final

from data_platform.analyst import derive
from data_platform.analyst.models import (
    Cohort,
    Derivation,
    Figure,
    RefusalExhibit,
    RetrievedSection,
    VerifiedSection,
    canonical,
)

REPORT_TITLE = "MGNREGA, 2006-2026: what the record says"

# From CITATION.cff: the author of the dataset and of this report, and the two DOIs Zenodo mints —
# the VERSION doi points at this immutable v1.0.0 release (what a citation must pin), the CONCEPT
# doi at the record across all its versions.
AUTHOR = "Prateek"
VERSION_DOI = "10.5281/zenodo.21318927"
CONCEPT_DOI = "10.5281/zenodo.21318431"


def build_report(sections: Sequence[VerifiedSection], *, generated_at: str) -> dict[str, object]:
    """The structured report artifact — the contract a viewer consumes."""
    return {
        "title": REPORT_TITLE,
        "generated_at": generated_at,
        "dataset": {
            "name": "MGNREGA Canonical Series",
            "author": AUTHOR,
            "version": "v1.0.0",
            "doi": VERSION_DOI,
            "concept_doi": CONCEPT_DOI,
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
            "cohort_count": sum(len(s.retrieved.cohorts) for s in sections),
            "traces": (
                "Every figure embeds the full lineage payload captured at generation time from the "
                "checksum-verified dist/v1.0. A cohort (a count) embeds every member fact_id and "
                "the distinct sources behind them. Any trace can be independently re-derived by "
                "running this repo's MCP server and calling get_lineage(fact_id): the record is "
                "sealed, so a live lookup cannot return anything different from the embedded copy."
            ),
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
        "cohorts": [_cohort(c) for c in retrieved.cohorts],
        "schema_facts": [
            {
                "id": f.id,
                "label": f.label,
                "value": canonical(f.value),
                "unit": f.unit,
                "call": f.call,
                "declares": list(f.metrics),
            }
            for f in retrieved.schema_facts
        ],
        "derivations": [_derivation(d, retrieved) for d in retrieved.derivations],
        "refusals": [_refusal(r) for r in retrieved.refusals],
        # Verified exactly like the figures above, but never shown to the drafter: the charts are
        # drawn from these by code.
        "series": [_figure(f) for f in retrieved.series],
        "series_cohorts": [_cohort(c) for c in retrieved.series_cohorts],
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


def _cohort(cohort: Cohort) -> dict[str, object]:
    return {
        "id": cohort.id,
        "label": cohort.label,
        "value": canonical(cohort.value),
        "unit": cohort.unit,
        "operation": cohort.operation,
        "query": cohort.query.to_dict(),
        "filter": cohort.filter,
        "predicate": cohort.predicate,
        "member_fact_ids": list(cohort.member_fact_ids),
        "sources": [dict(s) for s in cohort.sources],
    }


def _derivation(derivation: Derivation, section: RetrievedSection) -> dict[str, object]:
    return {
        "id": derivation.id,
        "label": derivation.label,
        "operation": derivation.operation,
        # A presentation operation restates a served value in a readable unit ("3.88 billion");
        # an analytical one asserts a relationship (a sum, a ratio). A reader should be able to
        # tell them apart without knowing the operation names.
        "kind": (
            "presentation"
            if derivation.operation in derive.PRESENTATION_OPERATIONS
            else "analytical"
        ),
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


# The narrative sections, in reading order, that frame the findings rather than report them. The
# findings sections come between them (in the order the graph generated them).
FRONT_MATTER_KEYS: Final[tuple[str, ...]] = ("abstract", "introduction", "methodology")
BACK_MATTER_KEYS: Final[tuple[str, ...]] = ("limitations",)


def render_markdown(report: dict[str, object]) -> str:
    """The human read: a document a third party can read cover to cover."""
    sections = report["sections"]
    assert isinstance(sections, list)
    by_key = {str(s["key"]): s for s in sections}

    lines = [
        f"# {report['title']}",
        "",
        f"*Generated {report['generated_at']} from the MGNREGA Canonical Series v1.0.0 "
        f"(DOI [{VERSION_DOI}](https://doi.org/{VERSION_DOI})) by {AUTHOR}, served read-only over "
        "MCP.*",
        "",
        "> **Every number in this document was machine-verified against the served dataset.** The "
        "prose was written by a language model that could see the record only through the query "
        "server, and that never chose a number: each figure it was given was re-checked against "
        "the data after drafting, each derived figure was recomputed from its inputs, and a "
        "section whose numbers failed to check was blocked from the report. The tables beneath "
        "each section are the evidence — every figure with its `fact_id` and its sources.",
        "",
    ]

    ordered = [by_key[k] for k in FRONT_MATTER_KEYS if k in by_key]
    ordered += [s for s in sections if str(s["key"]) not in (*FRONT_MATTER_KEYS, *BACK_MATTER_KEYS)]
    ordered += [by_key[k] for k in BACK_MATTER_KEYS if k in by_key]

    charts = report.get("charts")
    charts_by_section: dict[str, list[dict[str, object]]] = {}
    if isinstance(charts, list):
        for chart in charts:
            if isinstance(chart, dict):
                charts_by_section.setdefault(str(chart.get("section")), []).append(chart)

    for section in ordered:
        lines += [f"## {section['title']}", "", str(section["prose"]).strip(), ""]

        for chart in charts_by_section.get(str(section["key"]), []):
            lines += [
                f"![{chart['title']}]({chart['file']})",
                "",
                f"*{chart['caption']} Plotted from {len(_plots(chart))} verified figures; the "
                f"figure ids are listed in `report.json` under `charts`.*",
                "",
            ]

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

        cohorts = section["cohorts"]
        assert isinstance(cohorts, list)
        if cohorts:
            lines += [
                "| count | value | selected by (the complete predicate) | members |",
                "|---|---|---|---|",
            ]
            for cohort in cohorts:
                members = cohort["member_fact_ids"]
                assert isinstance(members, list)
                lines.append(
                    f"| {cohort['label']} | {cohort['value']} | `{cohort['predicate']}` | "
                    f"{len(members)} fact ids in report.json |"
                )
            lines.append("")

        derivations = section["derivations"]
        assert isinstance(derivations, list)
        if derivations:
            lines += ["| derived figure | operation | inputs | value |", "|---|---|---|---|"]
            for derivation in derivations:
                lines.append(
                    f"| {derivation['label']} | {derivation['operation']} | "
                    f"{_inputs(derivation)} | {derivation['value']} |"
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

    lines += _how_to_cite(report)
    return "\n".join(lines)


def _how_to_cite(report: dict[str, object]) -> list[str]:
    """Back matter, written by code: citation, reproduction, and how to re-derive any trace."""
    dataset = report.get("dataset")
    dataset = dataset if isinstance(dataset, dict) else {}
    return [
        "## How to cite, and how to check this",
        "",
        "The dataset this report reads is a sealed, DOI-versioned release: "
        f"**{dataset.get('name')} {dataset.get('version')}**, "
        f"DOI [{dataset.get('doi')}](https://doi.org/{dataset.get('doi')}). MGNREGA was repealed "
        "effective 30 June 2026, so the record is closed — it will not change, and neither will "
        "the figures below.",
        "",
        "**To reproduce this report**, from a checkout of the repository with the release "
        "artifacts in `dist/v1.0/` (the server checksum-verifies them at startup and refuses to "
        "run if a byte differs):",
        "",
        "```bash",
        "OPENROUTER_API_KEY=...  PYTHONPATH=src uv run python -m data_platform.analyst",
        "```",
        "",
        "Any OpenAI-compatible endpoint works; the model writes the prose and nothing else.",
        "",
        "**To cite this report:**",
        "",
        f"> {AUTHOR} (2026). *{REPORT_TITLE}.* Generated from the MGNREGA Canonical Series v1.0.0 "
        f"[dataset], DOI [{VERSION_DOI}](https://doi.org/{VERSION_DOI}).",
        "",
        f"**To cite the dataset itself:** {AUTHOR} (2026). *MGNREGA Canonical Series* (v1.0.0) "
        f"[dataset]. Zenodo. DOI [{VERSION_DOI}](https://doi.org/{VERSION_DOI}). That is the "
        f"**version** DOI — it pins this immutable release, which is what a citation needs. The "
        f"**concept** DOI [{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI}) resolves to the record "
        "across all its versions. Cite the dataset for the figures and this report for the reading "
        "of them.",
        "",
        "**To check any single number**, take its `fact_id` from the table beneath the section, "
        "start the query server (`PYTHONPATH=src uv run python -m data_platform.mcp`) and call "
        "`get_lineage(fact_id)`. You will get back every source that carried the fact, its "
        "resource id on the open-data portal, its as-of date, the value it reported, and — where "
        "publishers disagreed — the value that was rejected and the rule that decided it. The "
        "full payload is also embedded in `report.json`, so the answer is already in your hands; "
        "the record is sealed, so the live lookup cannot return anything different.",
        "",
    ]


# Above this many input facts, an inline list is noise, not evidence: the derivation names the
# aggregate it was computed from, and report.json carries the full enumeration.
_MAX_INLINE_INPUTS: Final = 10


def _inputs(derivation: dict[str, object]) -> str:
    """A derivation's inputs, readable: fact ids when few, the aggregate's id when many."""
    facts = derivation.get("input_fact_ids")
    facts = facts if isinstance(facts, list) else []
    if len(facts) <= _MAX_INLINE_INPUTS:
        return ", ".join(f"`{f}`" for f in facts)
    ids = derivation.get("input_figure_ids")
    ids = ids if isinstance(ids, list) else []
    named = ", ".join(f"`{i}`" for i in ids)
    return f"{named} ({len(facts)} facts; enumerated in report.json)"


def _plots(chart: dict[str, object]) -> list[object]:
    plots = chart.get("plots")
    return plots if isinstance(plots, list) else []


def _sources(figure: dict[str, object]) -> list[dict[str, object]]:
    lineage = figure.get("lineage")
    if not isinstance(lineage, dict):
        return []
    sources = lineage.get("sources")
    return [s for s in sources if isinstance(s, dict)] if isinstance(sources, list) else []
