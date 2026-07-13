"""The retriever — gathers a section's evidence from the served surface, before any prose exists.

Every figure is fetched by an explicit ``query`` call, keeps the ``fact_id`` the server returned,
and immediately pulls its full ``get_lineage`` payload: a figure and its provenance are retrieved
together, so a figure without lineage cannot reach the drafter in the first place.

Derived figures (ratios, sums, differences) are computed here, by :mod:`derive`, over input facts
listed by id — never by the LLM.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from data_platform.analyst import cohort as cohort_mod
from data_platform.analyst import derive
from data_platform.analyst.models import (
    Cohort,
    CohortSpec,
    Derivation,
    Figure,
    QuerySpec,
    RefusalExhibit,
)
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
    payload = tools.query(
        spec.table,
        metrics=[spec.metric],
        states=None if spec.state is None else [spec.state],
        districts=None if spec.district is None else [spec.district],
        fy_from=spec.fy,
        fy_to=spec.fy,
    )
    if payload.get("refused"):
        raise RetrievalError(f"{id}: the record refused this query — {payload.get('reason')}")

    rows = _rows(payload)
    if len(rows) != 1:
        raise RetrievalError(f"{id}: expected exactly 1 row for {spec}, got {len(rows)}")
    row = rows[0]

    value = row.get("value")
    if value is None:
        raise RetrievalError(
            f"{id}: the fact is null — a null cell is data, but it is not a figure"
        )

    fact_id = row.get("fact_id")
    if not isinstance(fact_id, str):
        raise RetrievalError(f"{id}: the served row carries no fact_id")

    records = tools.get_lineage(fact_id).get("records")
    if not isinstance(records, list) or not records:
        raise RetrievalError(f"{id}: no lineage record for fact {fact_id}")
    lineage = records[0]
    if not isinstance(lineage, dict):
        raise RetrievalError(f"{id}: malformed lineage record for fact {fact_id}")

    return Figure(
        id=id,
        label=label,
        metric=spec.metric,
        geography=geography,
        period=spec.fy,
        value=_decimal(value),
        unit=str(row.get("unit")),
        fact_id=fact_id,
        query=spec,
        lineage=lineage,
    )


def fetch_cohort(
    tools: AnalystTools,
    *,
    id: str,
    label: str,
    table: str,
    filter: str,
    metrics: Sequence[str] | None = None,
    states: Sequence[str] | None = None,
    fy_from: str | None = None,
    fy_to: str | None = None,
) -> Cohort:
    """Count the facts a named filter selects from one query, and record what proves the count.

    The cohort keeps the query, the filter's name, every member ``fact_id``, and the distinct
    sources behind those members — so the verifier can re-execute, re-filter, and recount, and a
    reader can pull any member's full trace with one ``get_lineage`` call.
    """
    if filter not in cohort_mod.FILTERS:  # fail before querying, so a typo is not an empty count
        raise ValueError(f"unknown filter {filter!r}; known: {sorted(cohort_mod.FILTERS)}")

    spec = CohortSpec(
        table=table,
        metrics=None if metrics is None else tuple(metrics),
        states=None if states is None else tuple(states),
        fy_from=fy_from,
        fy_to=fy_to,
    )
    members = _select(tools, spec, filter)
    fact_ids = tuple(str(row["fact_id"]) for row in members)
    return Cohort(
        id=id,
        label=label,
        operation="count",
        query=spec,
        filter=filter,
        value=Decimal(len(fact_ids)),
        unit="facts",
        member_fact_ids=fact_ids,
        sources=_distinct_sources(tools, fact_ids),
    )


def _select(tools: AnalystTools, spec: CohortSpec, filter: str) -> list[Payload]:
    payload = tools.query(
        spec.table,
        metrics=None if spec.metrics is None else list(spec.metrics),
        states=None if spec.states is None else list(spec.states),
        fy_from=spec.fy_from,
        fy_to=spec.fy_to,
    )
    if payload.get("refused"):
        raise RetrievalError(f"the record refused a cohort query — {payload.get('reason')}")
    return cohort_mod.select(_rows(payload), filter)


def _distinct_sources(tools: AnalystTools, fact_ids: Sequence[str]) -> tuple[Payload, ...]:
    """The distinct (source, resource, as-of) triples behind a cohort's members.

    An empty cohort rests on no facts, so it has no sources — zero is a finding about the record
    ("no wage rate exists for the repeal-truncated year"), and demanding provenance for facts that
    do not exist would make the honest answer unprovable.
    """
    if not fact_ids:
        return ()

    records = tools.get_lineage(list(fact_ids)).get("records")
    if not isinstance(records, list):
        raise RetrievalError("get_lineage returned no records for a cohort's members")

    seen: dict[tuple[str, str, str], Payload] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        sources = record.get("sources")
        if not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict):
                continue
            key = (
                str(source.get("source_id")),
                str(source.get("resource_id")),
                str(source.get("as_of")),
            )
            seen.setdefault(
                key,
                {
                    "source_id": source.get("source_id"),
                    "resource_id": source.get("resource_id"),
                    "as_of": source.get("as_of"),
                },
            )
    return tuple(seen.values())


def derived(
    *,
    id: str,
    label: str,
    operation: str,
    inputs: Sequence[Figure | Derivation | Cohort],
    unit: str,
) -> Derivation:
    """Compute a derivation over retrieved figures, recording the operation and its inputs.

    An input may itself be a derivation or a cohort — the spine residual is a difference against a
    sum; the record's null count is a sum of two counts — so the inputs form a small DAG whose
    leaves are all served facts.
    """
    value = derive.compute(operation, [node.value for node in inputs])
    return Derivation(
        id=id,
        label=label,
        operation=operation,
        inputs=tuple(node.id for node in inputs),
        value=value,
        unit=unit,
    )


def refusal(
    tools: AnalystTools, *, id: str, label: str, call: str, **kwargs: object
) -> RefusalExhibit:
    """Execute a call the record cannot honestly answer and keep the refusal object it returned.

    A section that claims the record refuses something must prove it: if the call is answered, that
    is a retrieval error, not a section with a missing exhibit.
    """
    table = kwargs.pop("table")
    payload = tools.query(str(table), **kwargs)  # type: ignore[arg-type]
    if not payload.get("refused"):
        raise RetrievalError(f"{id}: expected a refusal from {call}, but the record answered it")
    return RefusalExhibit(id=id, label=label, call=call, payload=payload)


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise RetrievalError(f"served value {value!r} is not a number") from exc


def _rows(payload: Payload) -> list[Payload]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise RetrievalError("the query returned no result envelope")
    return [row for row in rows if isinstance(row, dict)]
