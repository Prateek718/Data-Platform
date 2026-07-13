"""The verifier — deterministic, no LLM, and the reason the report can be trusted.

It takes drafted prose plus the evidence the retriever gathered, and it blocks the section unless
EVERY numeric claim in the prose is backed:

* every number in the prose must be one of the section's declared figures or derivations, rendered
  exactly as the figure was given (no silent rounding, no unit conversion, no invention);
* every declared figure must carry a lineage reference — sources with resource ids, at least one of
  them dated. A figure without lineage is a failure, not a warning;
* every derivation is recomputed from its declared input facts, and must match;
* defense in depth: each figure's backing ``query`` is re-executed against the served data, and the
  value and ``fact_id`` must still match what the drafter was given.

Financial-year labels ("2022-23") are not figures: they are periods, and they are checked against
the periods the section actually retrieved (R7-SRV-01 — such a label is compared as a string, so it
is validated rather than trusted).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Final

from data_platform.analyst import derive
from data_platform.analyst.models import (
    Derivation,
    Figure,
    RetrievedSection,
    VerificationReport,
    canonical,
)
from data_platform.analyst.tools import AnalystTools, Payload

# A financial-year label: stripped from the prose before numbers are read, and validated separately.
FY_LABEL: Final = re.compile(r"\b[0-9]{4}-[0-9]{2}\b")

# A numeric token as prose renders one: 94,004 · 3,881,318,918 · 0.16 · 22.09
NUMBER: Final = re.compile(r"(?<![\w.])[0-9][0-9,]*(?:\.[0-9]+)?")


def verify(section: RetrievedSection, prose: str, tools: AnalystTools) -> VerificationReport:
    """Check every numeric claim in ``prose`` against the section's evidence and the served data."""
    problems: list[str] = []

    for figure in section.figures:
        problems.extend(lineage_problems(figure))
        problems.extend(replay_problems(figure, tools))

    known = {figure.id: figure.value for figure in section.figures}
    for derivation in section.derivations:
        found = derivation_problems(section, derivation, known)
        problems.extend(found)
        if not found:  # only a derivation that checked out may feed a later one
            known[derivation.id] = derivation.value

    # Text the server itself returned — a refusal's call and its reason — is served content. Quoting
    # it VERBATIM is verified by string equality with the payload, so it is not a numeric claim and
    # is removed before the prose is read for claims. Alter one digit and the quote stops matching,
    # so the altered number reappears as an invented one. (Found by the first live run: the drafter
    # quoted a refusal whose month argument, "2022-04", read as a financial-year claim.)
    claims = _strip_quoted_exhibits(prose, section)

    periods = {figure.period for figure in section.figures}
    for label in FY_LABEL.findall(claims):
        if label not in periods:
            problems.append(
                f"the prose cites financial year {label}, which this section never retrieved "
                f"(retrieved: {', '.join(sorted(periods))})"
            )

    allowed = _allowed_renderings(section)
    for token in number_tokens(claims):
        if token not in allowed:
            problems.append(
                f"the number {token} in the prose is not a figure or a declared derivation in "
                "this section — every number must come from the served data"
            )

    return VerificationReport(problems=tuple(problems))


def number_tokens(prose: str) -> list[str]:
    """Every numeric token in the prose, with financial-year labels removed first."""
    return NUMBER.findall(FY_LABEL.sub(" ", prose))


def renderings(value: Decimal) -> set[str]:
    """The spellings of a value the prose may legitimately use: plain and comma-grouped.

    Deliberately narrow. Anything else — a rounded value, a rescaled one ("1.0 million"), a
    converted unit — is a number the served data did not produce, and is blocked.
    """
    plain = canonical(value)
    grouped = f"{value.normalize():,f}"
    return {plain, grouped}


def lineage_problems(figure: Figure) -> list[str]:
    """Complaints about a figure's provenance — empty when it carries a usable lineage reference.

    Every source must name the resource it came from, and at least one must be dated. (Not every
    source can be: several archived MOSPI vintages carry no publication date at all, and demanding
    one from each would reject facts whose provenance is otherwise complete.)
    """
    sources = figure.sources
    if not sources:
        problems = [f"{figure.id}: no lineage reference — a figure without provenance cannot ship"]
        return problems

    problems = []
    undated = [s for s in sources if not s.get("as_of")]
    if len(undated) == len(sources):
        problems.append(f"{figure.id}: no lineage source carries an as-of date")
    for source in sources:
        if not source.get("resource_id"):
            problems.append(
                f"{figure.id}: lineage source {source.get('source_id')!r} names no resource_id"
            )
    return problems


def derivation_problems(
    section: RetrievedSection, derivation: Derivation, known: Mapping[str, Decimal]
) -> list[str]:
    """Recompute a derivation from its declared inputs; complain on mismatch.

    ``known`` holds the values already established for this section — its figures, plus the
    derivations verified before this one. An input that is not in it was never retrieved (or is a
    forward reference), and the derivation is blocked rather than resolved.
    """
    values: list[Decimal] = []
    for input_id in derivation.inputs:
        if input_id not in known:
            return [
                f"{derivation.id}: declares input {input_id!r}, which this section never "
                "retrieved — a derivation may only combine facts the record served"
            ]
        values.append(known[input_id])

    try:
        recomputed = derive.compute(derivation.operation, values)
    except ValueError as exc:
        return [f"{derivation.id}: cannot be recomputed ({exc})"]

    if recomputed != derivation.value:
        return [
            f"{derivation.id}: declared value {canonical(derivation.value)} does not match "
            f"{derivation.operation} over its inputs, which gives {canonical(recomputed)}"
        ]
    return []


def replay_problems(figure: Figure, tools: AnalystTools) -> list[str]:
    """Re-execute a figure's backing query; complain if the served data no longer agrees."""
    spec = figure.query
    payload = tools.query(
        spec.table,
        metrics=[spec.metric],
        states=None if spec.state is None else [spec.state],
        districts=None if spec.district is None else [spec.district],
        fy_from=spec.fy,
        fy_to=spec.fy,
    )
    if payload.get("refused"):
        return [f"{figure.id}: re-running its query is refused — {payload.get('reason')}"]

    rows = _rows(payload)
    match = [row for row in rows if row.get("fact_id") == figure.fact_id]
    if not match:
        return [f"{figure.id}: fact {figure.fact_id} is not returned by its own query any more"]

    served = _decimal(match[0].get("value"))
    if served is None or served != figure.value:
        return [
            f"{figure.id}: the served data says {served}, but the figure carries "
            f"{canonical(figure.value)}"
        ]
    return []


def _strip_quoted_exhibits(prose: str, section: RetrievedSection) -> str:
    """Remove verbatim quotations of the section's refusal exhibits, longest first.

    Only exact matches are removed: the exhibit text is what the server returned, so an exact quote
    of it is already verified. A paraphrase, or a quote with a digit changed, does not match and
    stays in the prose to be checked as an ordinary claim.
    """
    quotable: list[str] = []
    for exhibit in section.refusals:
        quotable.append(exhibit.call)
        reason = exhibit.payload.get("reason")
        if isinstance(reason, str):
            quotable.append(reason)

    stripped = prose
    for text in sorted(quotable, key=len, reverse=True):
        stripped = stripped.replace(text, " ")
    return stripped


def _allowed_renderings(section: RetrievedSection) -> set[str]:
    allowed: set[str] = set()
    for figure in section.figures:
        allowed |= renderings(figure.value)
    for derivation in section.derivations:
        allowed |= renderings(derivation.value)
    return allowed


def _rows(payload: Payload) -> list[Payload]:
    rows = payload.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None
