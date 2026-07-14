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
* ``OPENROUTER_MAX_TOKENS`` / ``OPENROUTER_TIMEOUT_S`` — headroom for a slow reasoning model, whose
  private reasoning is charged against the same completion budget and can take minutes per section.

The drafter is given the figures and nothing else. It cannot query, it cannot compute, and every
number it writes is checked by the verifier afterwards — the prompt asks for discipline, the
verifier enforces it.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Final, Protocol

import httpx

from data_platform.analyst.models import RetrievedSection, canonical

DEFAULT_BASE_URL: Final = "https://openrouter.ai/api/v1"
DEFAULT_MODEL: Final = "meta-llama/llama-3.3-70b-instruct:free"
# A free-tier reasoning model can spend minutes on one section before the first byte of the answer
# arrives (measured: the national-series prompt read-timed out at 180s). Config-carried
# (OPENROUTER_TIMEOUT_S) — a slower endpoint is a setting, not a code change.
DEFAULT_TIMEOUT_S: Final = 600.0

# A section's prose is ~400 tokens, but this budget is not just for prose: on a REASONING model the
# private reasoning is charged against the same completion budget, and a model that thinks past the
# limit returns finish_reason "length" with no content at all. Measured: tencent/hy3 spends ~1,900
# reasoning tokens on one section before writing a word. Config-carried (OPENROUTER_MAX_TOKENS), so
# a model that thinks harder is a setting, not a code change.
DEFAULT_MAX_TOKENS: Final = 4000

# A free endpoint throttles: mid-run it answers 429 ("not now"), and one throttled section would
# otherwise cost the whole report. Transient statuses are retried with a linear backoff; a 4xx that
# means the REQUEST is wrong is not retried, because repeating it would only fail again.
RETRY_STATUSES: Final = frozenset({408, 409, 429, 500, 502, 503, 504})
MAX_ATTEMPTS: Final = 4
RETRY_BACKOFF_S: Final = 20.0

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
4. PREFER the presentation forms where they are given ("3.88 billion person-days", "Rs 1.10 lakh \
crore") over the raw served value: they are the same fact, restated by code in a unit a reader can \
hold. The exact value appears in the table beneath your prose, so you do not need to print it.
5. State what the record shows, including where it refuses to answer or has no data. Do not \
editorialize or speculate about causes.

REGISTER. This is a chapter of a research report that a stranger will read cover to cover.
- Measured academic prose. Full sentences, 3-5 paragraphs, no headings, no bullet lists, no tables.
- Never narrate the machinery. Do not write "indicating that", "the record shows that the count \
is", "the derived figure is", "a structured refusal was returned with code X". Say what is true \
about MGNREGA, and where the record declines to answer, say so in plain words and quote the \
server's reason once.
- Never state the same figure twice in a paragraph, and do not restate a number you have already \
given in the section.
- Group thousands with commas: write 94,004 and not 94004.
- NO SUPERLATIVES unless the evidence itself says so. Do not call anything the largest, the \
highest, the worst or the most unless the label of the figure you are citing uses that word. A \
ranking nobody computed is a claim you cannot support.
- A figure attached to a disagreement is the CANONICAL VALUE the record settled on — it is not the \
size of the gap between the publishers. Never describe it as a magnitude of disagreement.
- Do not print figure ids, fact ids, table names, or column names.
- QUOTATION MARKS ARE A CLAIM. If you put the server's reason in quotes, reproduce it WORD FOR \
WORD, exactly as given. If you want to shorten or reword it, do so WITHOUT quotation marks. A \
reworded "quotation" is checked and will block the section.
- No throat-clearing ("This section will..."), no summarising your own instructions.
- Every sentence must carry a fact. Delete any sentence that only restates what the previous ones \
already said ("This joint foundation supports the counts that make up the scheme's lifespan").
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


def render_evidence(section: RetrievedSection) -> str:
    """The evidence block: every figure, derivation and refusal the drafter may narrate."""
    lines = ["FIGURES (each is a value the dataset served, with the fact it came from):"]
    for figure in section.figures:
        # "count" is a unit-class, not a word to put in a sentence: "75,500,579 count" reads badly
        # and the drafter copies what it is shown.
        unit = "" if figure.unit == "count" else f" {figure.unit}"
        lines.append(
            f"- {figure.label}: {canonical(figure.value)}{unit} "
            f"[metric={figure.metric}, geography={figure.geography}, period={figure.period}, "
            f"fact_id={figure.fact_id}]"
        )

    if section.cohorts:
        lines += ["", "COUNTS (each counted by code over the dataset — use the number as given):"]
        for cohort in section.cohorts:
            lines.append(
                f"- {cohort.label}: {canonical(cohort.value)} "
                f"[counted over the facts where {cohort.predicate}]"
            )

    if section.schema_facts:
        lines += [
            "",
            "SCHEMA FACTS (what the dataset's contract declares — use the number as given):",
        ]
        for fact in section.schema_facts:
            lines.append(
                f"- {fact.label}: {canonical(fact.value)} {fact.unit} "
                f"[{fact.call} declares: {', '.join(fact.metrics)}]"
            )

    if section.derivations:
        lines += ["", "DERIVED FIGURES (computed by code from the figures above — use as given):"]
        for derivation in section.derivations:
            inputs = " and ".join(derivation.inputs)
            lines.append(
                f"- {derivation.label}: {canonical(derivation.value)} {derivation.unit} "
                f"[{derivation.operation} of {inputs}]"
            )

    if section.refusals:
        lines += ["", "REFUSALS (what the server returned when asked — narrate the reason):"]
        for refusal in section.refusals:
            lines.append(f"- {refusal.label} — call: {refusal.call}")
            lines.append(f"  code: {refusal.payload.get('code')}")
            lines.append(f"  reason: {refusal.payload.get('reason')}")

    return "\n".join(lines)


def build_messages(request: DraftRequest) -> list[dict[str, str]]:
    """The chat messages for one draft: the system rules, the evidence, and any retry feedback."""
    section = request.section
    parts = [
        f"SECTION TITLE: {section.plan.title}",
        "",
        f"BRIEF: {section.plan.brief}",
        "",
        render_evidence(section),
    ]

    if request.mismatches:
        parts += [
            "",
            "YOUR PREVIOUS DRAFT WAS REJECTED by the verifier, which checks every number in the "
            "prose against the dataset. Its complaints:",
            *[f"- {problem}" for problem in request.mismatches],
            "",
            "REJECTED DRAFT:",
            request.previous_prose or "",
            "",
            "Rewrite the section using ONLY the figures above, copied exactly. Remove or replace "
            "every number the verifier rejected.",
        ]

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(parts)},
    ]


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
        timeout_s: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        base = base_url or os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)
        self.base_url = base.rstrip("/")
        self.model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.timeout_s = timeout_s or float(
            os.environ.get("OPENROUTER_TIMEOUT_S", DEFAULT_TIMEOUT_S)
        )
        self.max_tokens = max_tokens or int(
            os.environ.get("OPENROUTER_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        )

    def __repr__(self) -> str:  # never let the key reach a log line or a traceback
        return f"OpenRouterDrafter(base_url={self.base_url!r}, model={self.model!r})"

    def draft(self, request: DraftRequest, *, client: httpx.Client | None = None) -> str:
        """Draft one section. ``client`` is injectable, so tests drive this path offline."""
        if not self._api_key:
            raise MissingApiKeyError(
                "OPENROUTER_API_KEY is not set. The live drafter needs a key for an "
                "OpenAI-compatible chat-completions endpoint; tests use scripted fakes instead."
            )

        body: dict[str, object] = {
            "model": self.model,
            "messages": build_messages(request),
            "max_tokens": self.max_tokens,
            "temperature": 0,  # a report, not a brainstorm
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        http = client or httpx.Client(timeout=self.timeout_s)
        try:
            return self._post_with_retries(http, body, headers)
        finally:
            if client is None:
                http.close()

    def _post_with_retries(
        self, http: httpx.Client, body: dict[str, object], headers: dict[str, str]
    ) -> str:
        last: str = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = http.post(
                    f"{self.base_url}/chat/completions", json=body, headers=headers
                )
            except httpx.HTTPError as exc:
                last = f"the chat-completions endpoint failed: {exc}"
            else:
                if response.status_code == httpx.codes.OK:
                    return self._content(response.json())
                last = (
                    f"the chat-completions endpoint returned {response.status_code}: "
                    f"{response.text[:300]}"
                )
                if response.status_code not in RETRY_STATUSES:
                    raise DraftingError(last)  # the request is wrong; retrying changes nothing

            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_S * attempt)

        raise DraftingError(f"{last} (gave up after {MAX_ATTEMPTS} attempts)")

    def _content(self, payload: object) -> str:
        """Pull the assistant message out of an OpenAI-compatible response, or fail loudly."""
        if not isinstance(payload, dict):
            raise DraftingError("the endpoint returned a non-object response")
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DraftingError("the endpoint returned no choices")

        first: dict[str, object] = choices[0] if isinstance(choices[0], dict) else {}
        raw_message = first.get("message")
        message: dict[str, object] = raw_message if isinstance(raw_message, dict) else {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        if first.get("finish_reason") == "length":
            raise DraftingError(
                f"the model hit its {self.max_tokens}-token completion budget before writing any "
                f"prose ({_reasoning_tokens(payload)} reasoning tokens spent). On a reasoning "
                "model the private reasoning is charged against the same budget — raise "
                "OPENROUTER_MAX_TOKENS, or use a non-reasoning model."
            )
        raise DraftingError("the endpoint returned an empty message")


def _reasoning_tokens(payload: dict[str, object]) -> int:
    usage = payload.get("usage")
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    tokens = details.get("reasoning_tokens") if isinstance(details, dict) else None
    return tokens if isinstance(tokens, int) else 0
