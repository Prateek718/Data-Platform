"""The drafter's LLM seam — injectable, so the graph never depends on a live model.

:class:`Drafter` is the interface the graph calls. Tests inject scripted fakes (including one that
lies about a number, to prove the verifier blocks it); the live implementation talks to an
OpenAI-compatible chat-completions endpoint — OpenRouter by default, but any compatible endpoint
works, so regenerating the report does not tie the reader to one vendor.

Configuration is environment-only, never committed and never logged:

* ``OPENROUTER_API_KEY`` — required for the live path.
* ``OPENROUTER_BASE_URL`` — default ``https://openrouter.ai/api/v1``.
* ``OPENROUTER_MODEL``  — default :data:`DEFAULT_MODEL`. Free-tier model availability churns, so
  the id is config, not code: override it without touching this file.

The drafter is given the figures and nothing else. It cannot query, it cannot compute, and every
number it writes is checked by the verifier afterwards — the prompt asks for discipline, the
verifier enforces it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Final, Protocol

import httpx

from data_platform.analyst.models import RetrievedSection

DEFAULT_BASE_URL: Final = "https://openrouter.ai/api/v1"
DEFAULT_MODEL: Final = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_TIMEOUT_S: Final = 180.0
DEFAULT_MAX_TOKENS: Final = 1200

SYSTEM_PROMPT: Final = """\
You write one section of a public, researcher-grade report on India's MGNREGA rural employment \
guarantee scheme, a closed historical record (the scheme was repealed effective 30 June 2026).

You are given a section brief and the ONLY evidence you may use: figures retrieved from the \
governed dataset, derived figures computed from them, and — where relevant — the structured \
refusals the data server returned.

Hard rules, mechanically checked after you write:
1. Every number you write MUST be one of the figures or derived figures given to you, copied \
EXACTLY as provided (keep the digits; comma grouping is fine). Do not round, rescale, convert \
units, or compute anything new. A number that is not in the evidence blocks the section.
2. Do not invent facts, causes, or context that the evidence does not state. No outside knowledge.
3. Financial-year labels (e.g. 2022-23) may be used as written.
4. Write plain, precise prose for a researcher: 2-4 short paragraphs, no headings, no bullet \
lists, no markdown tables. Name the figures in words; do not print the figure ids.
5. State what the record shows, including where it refuses to answer or has no data. Do not \
editorialize or speculate about causes.
"""


@dataclass(frozen=True)
class DraftRequest:
    """Everything the drafter is allowed to see for one section."""

    section: RetrievedSection
    previous_prose: str | None = None
    mismatches: tuple[str, ...] = field(default_factory=tuple)


class Drafter(Protocol):
    """Writes a section's prose from its evidence. The only LLM call in the system."""

    def draft(self, request: DraftRequest) -> str: ...


def build_messages(request: DraftRequest) -> list[dict[str, str]]:
    """The chat messages for one draft: the system rules, the evidence, and any retry feedback."""
    raise NotImplementedError


def render_evidence(section: RetrievedSection) -> str:
    """The evidence block: every figure, derivation and refusal the drafter may narrate."""
    raise NotImplementedError


class MissingApiKeyError(RuntimeError):
    """The live drafter was used without ``OPENROUTER_API_KEY`` in the environment."""


class DraftingError(RuntimeError):
    """The chat-completions endpoint failed or returned an unusable response."""


class OpenRouterDrafter:
    """Live drafter over an OpenAI-compatible chat-completions endpoint (OpenRouter by default)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)
        self.model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens

    def draft(self, request: DraftRequest, *, client: httpx.Client | None = None) -> str:
        """Draft one section. ``client`` is injectable, so tests drive this path offline."""
        raise NotImplementedError
