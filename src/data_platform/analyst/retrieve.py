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

from data_platform.analyst import derive
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


def derived(
    *,
    id: str,
    label: str,
    operation: str,
    inputs: Sequence[Figure | Derivation],
    unit: str,
) -> Derivation:
    """Compute a derivation over retrieved figures, recording the operation and its inputs.

    An input may itself be a derivation — the spine residual is a difference against a sum — so the
    inputs form a small DAG whose leaves are all served facts.
    """
    value = derive.compute(operation, [figure.value for figure in inputs])
    return Derivation(
        id=id,
        label=label,
        operation=operation,
        inputs=tuple(figure.id for figure in inputs),
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
