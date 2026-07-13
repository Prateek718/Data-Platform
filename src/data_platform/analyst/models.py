"""The analyst's typed objects — what a claim is made of.

Every number the report can print is one of exactly two things: a :class:`Figure` (a value a single
``query`` call returned, carrying its ``fact_id`` and its lineage payload) or a :class:`Derivation`
(a named deterministic operation over figures the retriever already fetched — a ratio, a sum, a
difference). There is no third kind, and the LLM produces neither: it is handed these objects and
may only narrate them. The verifier re-checks both against the served data.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from data_platform.analyst.tools import Payload


@dataclass(frozen=True)
class QuerySpec:
    """The exact ``query`` call that produced a figure — replayed verbatim by the verifier."""

    table: str
    metric: str
    fy: str
    state: str | None = None
    district: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "table": self.table,
            "metrics": [self.metric],
            "states": None if self.state is None else [self.state],
            "districts": None if self.district is None else [self.district],
            "fy_from": self.fy,
            "fy_to": self.fy,
        }


@dataclass(frozen=True)
class Figure:
    """One served value: what it is, where it came from, and the provenance behind it."""

    id: str
    label: str
    metric: str
    geography: str
    period: str
    value: Decimal
    unit: str
    fact_id: str
    query: QuerySpec
    lineage: Payload

    @property
    def sources(self) -> list[Payload]:
        raw = self.lineage.get("sources")
        return [s for s in raw if isinstance(s, dict)] if isinstance(raw, list) else []


@dataclass(frozen=True)
class Derivation:
    """A named deterministic operation over figures — computed by code, never by the LLM."""

    id: str
    label: str
    operation: str
    inputs: tuple[str, ...]
    value: Decimal
    unit: str


@dataclass(frozen=True)
class RefusalExhibit:
    """A refusal the report shows as evidence: the call, and the object the server returned."""

    id: str
    label: str
    call: str
    payload: Payload


@dataclass(frozen=True)
class SectionPlan:
    """A section the report will contain: key, title, and the brief handed to the drafter."""

    key: str
    title: str
    brief: str


@dataclass(frozen=True)
class RetrievedSection:
    """A section's evidence, gathered before a word of prose exists."""

    plan: SectionPlan
    figures: tuple[Figure, ...]
    derivations: tuple[Derivation, ...]
    refusals: tuple[RefusalExhibit, ...] = ()

    def figure(self, figure_id: str) -> Figure:
        for fig in self.figures:
            if fig.id == figure_id:
                return fig
        raise KeyError(f"no figure {figure_id!r} in section {self.plan.key!r}")


@dataclass(frozen=True)
class VerificationReport:
    """The verifier's verdict. ``problems`` is empty if and only if the section passed."""

    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems

    def render(self) -> str:
        return "\n".join(f"- {p}" for p in self.problems)


@dataclass(frozen=True)
class VerifiedSection:
    """A section whose every number has been checked against the served data."""

    retrieved: RetrievedSection
    prose: str
    attempts: int
