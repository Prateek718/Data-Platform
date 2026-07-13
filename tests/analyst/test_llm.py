"""The LLM seam: prompt construction and the live HTTP path — both exercised without a network.

The live drafter talks to an OpenAI-compatible chat-completions endpoint (OpenRouter by default).
Here it talks to an httpx MockTransport instead: no socket is opened, so the suite's hermetic
network guard stays satisfied and CI never depends on a model being up.
"""

from __future__ import annotations

import httpx
import pytest

from data_platform.analyst import llm
from data_platform.analyst.llm import DraftRequest, OpenRouterDrafter
from data_platform.analyst.models import RetrievedSection
from data_platform.analyst.tools import DirectTools
from data_platform.mcp import loader
from tests.analyst.evidence import build_section
from tests.conftest import SyntheticDist


@pytest.fixture
def section(synthetic_dist: SyntheticDist) -> RetrievedSection:
    tools = DirectTools(
        loader.load_dataset(dist_dir=synthetic_dist.dir, manifest_path=synthetic_dist.manifest_path)
    )
    return build_section(tools)


def test_evidence_carries_every_figure_verbatim(section: RetrievedSection) -> None:
    evidence = llm.render_evidence(section)
    assert "1000000" in evidence
    assert "300000" in evidence
    assert "0.3" in evidence
    assert "monthly_wage_unavailable" in evidence  # the refusal object is evidence too


def test_messages_carry_the_rules_and_the_brief(section: RetrievedSection) -> None:
    messages = llm.build_messages(DraftRequest(section=section))
    assert messages[0]["role"] == "system"
    assert "MUST be one of the figures" in messages[0]["content"]
    assert section.plan.brief in messages[1]["content"]


def test_a_retry_hands_back_the_mismatch_report(section: RetrievedSection) -> None:
    request = DraftRequest(
        section=section,
        previous_prose="It generated 1,400,000 person-days.",
        mismatches=("1,400,000 is not a figure in this section",),
    )
    prompt = llm.build_messages(request)[-1]["content"]
    assert "1,400,000 is not a figure in this section" in prompt
    assert "1,400,000 person-days" in prompt  # the rejected draft, so the model can see its error


def test_the_live_drafter_needs_an_api_key(
    section: RetrievedSection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(llm.MissingApiKeyError):
        OpenRouterDrafter().draft(DraftRequest(section=section))


def test_the_live_drafter_posts_an_openai_compatible_request(section: RetrievedSection) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        import json

        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "The state generated 1,000,000."}}]}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    drafter = OpenRouterDrafter(
        api_key="test-key", base_url="https://example.invalid/api/v1", model="some/model:free"
    )
    prose = drafter.draft(DraftRequest(section=section), client=client)

    assert prose == "The state generated 1,000,000."
    assert seen["url"] == "https://example.invalid/api/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "some/model:free"
    assert body["messages"][0]["role"] == "system"


def test_an_unusable_response_is_an_error_not_empty_prose(section: RetrievedSection) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={"choices": []}))
    )
    drafter = OpenRouterDrafter(api_key="test-key")
    with pytest.raises(llm.DraftingError):
        drafter.draft(DraftRequest(section=section), client=client)


def test_an_http_error_is_reported(section: RetrievedSection) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _r: httpx.Response(429, text="rate limited"))
    )
    drafter = OpenRouterDrafter(api_key="test-key")
    with pytest.raises(llm.DraftingError, match="429"):
        drafter.draft(DraftRequest(section=section), client=client)


def test_the_api_key_is_never_in_the_repr() -> None:
    drafter = OpenRouterDrafter(api_key="super-secret")
    assert "super-secret" not in repr(drafter)
