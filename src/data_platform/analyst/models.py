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


def canonical(value: Decimal) -> str:
    """The one plain spelling of a value: no exponent, no trailing zeros. 1000000.0 -> "1000000".

    Shared by the verifier (which decides what the prose may say) and the assembler (which writes
    report.json), so a figure is spelled identically wherever it appears.
    """
    return format(value.normalize(), "f")


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
class CohortSpec:
    """The query a cohort counts over — replayed verbatim by the verifier."""

    table: str
    metrics: tuple[str, ...] | None = None
    states: tuple[str, ...] | None = None
    fy_from: str | None = None
    fy_to: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "table": self.table,
            "metrics": None if self.metrics is None else list(self.metrics),
            "states": None if self.states is None else list(self.states),
            "fy_from": self.fy_from,
            "fy_to": self.fy_to,
        }


@dataclass(frozen=True)
class Cohort:
    """A count over many facts: the query, the named filter, every member, and their sources.

    A single fact proves itself with one ``fact_id`` and one lineage payload. A count cannot — so it
    carries the query and the named deterministic filter that selected its members (both replayable
    by the verifier), the ``fact_id`` of EVERY member (each one's full trace is a ``get_lineage``
    call away), and the distinct sources behind those members. An empty cohort — zero facts, which
    is itself a finding — has no members and therefore no sources.
    """

    id: str
    label: str
    operation: str
    query: CohortSpec
    filter: str
    value: Decimal
    unit: str
    member_fact_ids: tuple[str, ...]
    sources: tuple[Payload, ...]


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
    cohorts: tuple[Cohort, ...] = ()

    def figure(self, figure_id: str) -> Figure:
        for fig in self.figures:
            if fig.id == figure_id:
                return fig
        raise KeyError(f"no figure {figure_id!r} in section {self.plan.key!r}")

    def derivation(self, derivation_id: str) -> Derivation:
        for der in self.derivations:
            if der.id == derivation_id:
                return der
        raise KeyError(f"no derivation {derivation_id!r} in section {self.plan.key!r}")

    def cohort(self, cohort_id: str) -> Cohort:
        for coh in self.cohorts:
            if coh.id == cohort_id:
                return coh
        raise KeyError(f"no cohort {cohort_id!r} in section {self.plan.key!r}")

    def fact_ids(self, node_id: str) -> list[str]:
        """The served facts a figure, cohort or derivation ultimately rests on, in input order.

        A derivation may take another derivation or a cohort as an input (the spine residual is a
        difference against a sum; the record's null count is a sum of two cohorts), so the facts
        behind it are the transitive closure — and every one of them carries its own lineage.
        """
        for fig in self.figures:
            if fig.id == node_id:
                return [fig.fact_id]
        for coh in self.cohorts:
            if coh.id == node_id:
                return list(coh.member_fact_ids)
        facts: list[str] = []
        for input_id in self.derivation(node_id).inputs:
            facts.extend(self.fact_ids(input_id))
        return facts


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
