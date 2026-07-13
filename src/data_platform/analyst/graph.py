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
from typing import Annotated, Final, TypedDict

from data_platform.analyst.llm import Drafter
from data_platform.analyst.models import RetrievedSection, VerifiedSection
from data_platform.analyst.tools import AnalystTools

MAX_DRAFT_ATTEMPTS: Final = 3


class VerificationFailure(RuntimeError):
    """A section could not be drafted so that every number in it survives verification."""


class AnalystState(TypedDict, total=False):
    """The graph's state: the plan, the section in flight, and the sections already verified."""

    section_keys: list[str]
    index: int
    current: RetrievedSection | None
    prose: str
    attempts: int
    problems: list[str]
    verified: Annotated[list[VerifiedSection], "accumulated"]
    generated_at: str
    report: dict[str, object]


def run(
    *,
    tools: AnalystTools,
    drafter: Drafter,
    section_keys: Sequence[str],
    generated_at: str,
) -> dict[str, object]:
    """Run the graph over the given sections and return the assembled report artifact."""
    raise NotImplementedError
