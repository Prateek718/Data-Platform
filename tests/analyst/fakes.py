"""Scripted fake drafters — the LLM seam under test control.

The graph's guarantee is that a drafter it cannot trust produces no report. These fakes are how
that is proven: one writes honest prose, one lies about a number, one invents a derivation the
retriever never declared, and one lies once and then corrects itself when handed the mismatch
report. No test in the suite ever calls a live model.
"""

from __future__ import annotations

from data_platform.analyst.llm import DraftRequest


class ScriptedDrafter:
    """Returns pre-written prose, one per attempt; records every request it was handed."""

    def __init__(self, *drafts: str) -> None:
        self._drafts = list(drafts)
        self.requests: list[DraftRequest] = []

    def draft(self, request: DraftRequest) -> str:
        self.requests.append(request)
        index = min(len(self.requests) - 1, len(self._drafts) - 1)
        return self._drafts[index]

    @property
    def calls(self) -> int:
        return len(self.requests)
