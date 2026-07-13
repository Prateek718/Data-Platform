"""The retriever — gathers a section's evidence from the served surface, before any prose exists.

Every figure is fetched by an explicit ``query`` call, keeps the ``fact_id`` the server returned,
and immediately pulls its full ``get_lineage`` payload: a figure and its provenance are retrieved
together, so a figure without lineage cannot reach the drafter in the first place.

Derived figures (ratios, sums, differences) are computed here, by :mod:`derive`, over input facts
listed by id — never by the LLM.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from data_platform.analyst.models import Derivation, Figure, QuerySpec, RefusalExhibit
from data_platform.analyst.tools import AnalystTools, Payload


class RetrievalError(RuntimeError):
    """The served surface did not return the fact a section declared it needed."""


def fetch_figure(
    tools: AnalystTools,
    *,
    id: str,
    label: str,
    geography: str,
    spec: QuerySpec,
) -> Figure:
    """Run one query, take its single row, and attach the fact's full lineage payload."""
    raise NotImplementedError


def derived(
    *,
    id: str,
    label: str,
    operation: str,
    inputs: Sequence[Figure],
    unit: str,
) -> Derivation:
    """Compute a derivation over retrieved figures, recording the operation and its inputs."""
    raise NotImplementedError


def refusal(
    tools: AnalystTools, *, id: str, label: str, call: str, **kwargs: object
) -> RefusalExhibit:
    """Execute a call the record cannot honestly answer and keep the refusal object it returned."""
    raise NotImplementedError


def _decimal(value: object) -> Decimal:
    raise NotImplementedError


def _rows(payload: Payload) -> list[Payload]:
    raise NotImplementedError
