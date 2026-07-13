"""The agent graph (LangGraph): plan → retrieve → draft → verify → assemble.

The loop that matters is drafter ↔ verifier. The drafter writes prose from evidence; the verifier
checks every number in it against the served data. A section that fails goes back to the drafter
with the mismatch report attached, up to :data:`MAX_DRAFT_ATTEMPTS` times — after which the run
FAILS LOUDLY, carrying the verifier's mismatch report in the error, so a failed run is diagnosable
rather than mysterious. A weak drafter therefore produces no report, never a wrong one.

Only the drafter node calls an LLM. Planner, retriever, verifier and assembler are deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, TypedDict

from langgraph.graph import END, StateGraph

from data_platform.analyst import assemble
from data_platform.analyst import sections as sections_mod
from data_platform.analyst import verify as verify_mod
from data_platform.analyst.llm import Drafter, DraftRequest
from data_platform.analyst.models import RetrievedSection, SectionPlan, VerifiedSection
from data_platform.analyst.tools import AnalystTools

MAX_DRAFT_ATTEMPTS: Final = 3


class VerificationFailure(RuntimeError):
    """A section could not be drafted so that every number in it survives verification."""


class AnalystState(TypedDict, total=False):
    """The graph's state: the plan, the section in flight, and the sections already verified."""

    section_keys: list[str]
    plans: list[SectionPlan]
    index: int
    current: RetrievedSection
    prose: str
    attempts: int
    problems: list[str]
    verified: list[VerifiedSection]
    report: dict[str, object]


def run(
    *,
    tools: AnalystTools,
    drafter: Drafter,
    section_keys: Sequence[str],
    generated_at: str,
) -> dict[str, object]:
    """Run the graph over the given sections and return the assembled report artifact."""
    graph = build_graph(tools=tools, drafter=drafter, generated_at=generated_at)
    final: AnalystState = graph.invoke({"section_keys": list(section_keys)})  # type: ignore[attr-defined]
    return final["report"]


def build_graph(*, tools: AnalystTools, drafter: Drafter, generated_at: str) -> object:
    """Wire the five nodes. The conditional edge out of the verifier is the whole design."""

    def planner(state: AnalystState) -> AnalystState:
        plans = [sections_mod.SECTIONS[key][0] for key in state["section_keys"]]
        return {"plans": plans, "index": 0, "verified": []}

    def retriever(state: AnalystState) -> AnalystState:
        plan = state["plans"][state["index"]]
        retrieve_section = sections_mod.SECTIONS[plan.key][1]
        return {"current": retrieve_section(tools), "attempts": 0, "problems": []}

    def drafter_node(state: AnalystState) -> AnalystState:
        section = state["current"]
        request = DraftRequest(
            section=section,
            previous_prose=state.get("prose"),
            mismatches=tuple(state.get("problems", [])),
        )
        return {"prose": drafter.draft(request), "attempts": state["attempts"] + 1}

    def verifier(state: AnalystState) -> AnalystState:
        section = state["current"]
        report = verify_mod.verify(section, state["prose"], tools)
        if not report.ok:
            return {"problems": list(report.problems)}

        verified = [
            *state["verified"],
            VerifiedSection(retrieved=section, prose=state["prose"], attempts=state["attempts"]),
        ]
        return {"verified": verified, "problems": [], "index": state["index"] + 1}

    def assembler(state: AnalystState) -> AnalystState:
        return {"report": assemble.build_report(state["verified"], generated_at=generated_at)}

    def after_verify(state: AnalystState) -> str:
        if state["problems"]:
            if state["attempts"] >= MAX_DRAFT_ATTEMPTS:
                plan = state["plans"][state["index"]]
                raise VerificationFailure(
                    f"section {plan.key!r} failed verification after {state['attempts']} drafting "
                    f"attempts; the report was NOT written. The verifier's last complaints:\n"
                    + "\n".join(f"- {problem}" for problem in state["problems"])
                    + "\n\nRejected draft:\n"
                    + state["prose"]
                )
            return "draft"
        return "retrieve" if state["index"] < len(state["plans"]) else "assemble"

    builder: StateGraph[AnalystState, None, AnalystState, AnalystState] = StateGraph(AnalystState)
    builder.add_node("plan", planner)
    builder.add_node("retrieve", retriever)
    builder.add_node("draft", drafter_node)
    builder.add_node("verify", verifier)
    builder.add_node("assemble", assembler)

    builder.set_entry_point("plan")
    builder.add_edge("plan", "retrieve")
    builder.add_edge("retrieve", "draft")
    builder.add_edge("draft", "verify")
    builder.add_conditional_edges(
        "verify",
        after_verify,
        {"draft": "draft", "retrieve": "retrieve", "assemble": "assemble"},
    )
    builder.add_edge("assemble", END)
    return builder.compile()
