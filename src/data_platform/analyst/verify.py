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

from data_platform.analyst import derive, retrieve
from data_platform.analyst.models import (
    Cohort,
    Derivation,
    Figure,
    RetrievedSection,
    VerificationReport,
    canonical,
)
from data_platform.analyst.tools import AnalystTools, Payload

# A financial-year label: stripped from the prose before numbers are read, and validated separately.
FY_LABEL: Final = re.compile(r"\b[0-9]{4}-[0-9]{2}\b")

# A numeric token as prose renders one: 94,004 · 3,881,318,918 · 0.16 · 22.09. A trailing comma or
# period is PUNCTUATION, not part of the number — "300,000, and" must read as the figure 300,000.
NUMBER: Final = re.compile(r"(?<![\w.])[0-9](?:[0-9,]*[0-9])?(?:\.[0-9]+)?")


def verify(section: RetrievedSection, prose: str, tools: AnalystTools) -> VerificationReport:
    """Check every numeric claim in ``prose`` against the section's evidence and the served data."""
    problems: list[str] = []

    for figure in section.figures:
        problems.extend(lineage_problems(figure))
        problems.extend(replay_problems(figure, tools))

    for cohort in section.cohorts:
        problems.extend(cohort_problems(cohort, tools))

    known = {figure.id: figure.value for figure in section.figures}
    known.update({cohort.id: cohort.value for cohort in section.cohorts})
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

    periods = _allowed_periods(section)
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
                f"the number {token} in the prose is not a figure, a declared derivation, or a "
                "number the served data or this section's brief supplies — every number must come "
                "from the record"
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


def cohort_problems(cohort: Cohort, tools: AnalystTools) -> list[str]:
    """Re-execute a cohort's query, re-apply its named filter, and recount from the served data.

    Both the count AND the member set are checked: a count can be right while the facts behind it
    are wrong, and the member ids are what let a reader pull each trace for themselves.
    """
    spec = cohort.query
    try:
        recomputed = retrieve.fetch_cohort(
            tools,
            id=cohort.id,
            label=cohort.label,
            table=spec.table,
            filter=cohort.filter,
            metrics=None if spec.metrics is None else list(spec.metrics),
            states=None if spec.states is None else list(spec.states),
            fy_from=spec.fy_from,
            fy_to=spec.fy_to,
        )
    except (retrieve.RetrievalError, ValueError) as exc:
        return [f"{cohort.id}: cannot be recomputed from the served data ({exc})"]

    problems: list[str] = []
    if recomputed.value != cohort.value:
        problems.append(
            f"{cohort.id}: claims {canonical(cohort.value)} facts, but re-running its query with "
            f"the filter {cohort.filter!r} counts {canonical(recomputed.value)}"
        )
    if set(recomputed.member_fact_ids) != set(cohort.member_fact_ids):
        problems.append(
            f"{cohort.id}: its members are not the facts the served data selects "
            f"({len(cohort.member_fact_ids)} declared, {len(recomputed.member_fact_ids)} served)"
        )
    if cohort.member_fact_ids and not cohort.sources:
        problems.append(f"{cohort.id}: no lineage sources behind its members")
    for source in cohort.sources:
        if not source.get("resource_id"):
            problems.append(f"{cohort.id}: a lineage source names no resource_id")
    return problems


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
    """Every number the prose may legitimately contain, and there are exactly three sources.

    1. The section's evidence — figures, derivations, cohorts — spelled exactly as served.
    2. Numbers the SERVER itself returned inside a refusal (the call, the reason). Narrating a
       refusal is the point of several sections, and the model must be able to say what the server
       said. (Without this, the first full run deleted the dates out of the server's own quoted
       reason — "MGNREGA was repealed effective, so the canonical series ends at FY" — to comply.)
    3. Numbers the SECTION BRIEF or an evidence LABEL supplies: the repeal date, the era boundary,
       the Rs 1,000/day implausibility floor, the FY range a cohort covers. Both are authored text
       in this repo, reviewed like code and handed to the drafter as evidence — not model output —
       so restating them is not a claim about the data.

    Anything else is a number the model produced from nowhere, and it blocks the section.
    """
    allowed: set[str] = set()
    for figure in section.figures:
        allowed |= renderings(figure.value)
    for derivation in section.derivations:
        allowed |= renderings(derivation.value)
    for cohort in section.cohorts:
        allowed |= renderings(cohort.value)
    for text in _served_and_briefed_text(section):
        allowed |= set(number_tokens(text))
    return allowed


def _allowed_periods(section: RetrievedSection) -> set[str]:
    """The financial years the prose may name: retrieved, or named by the server or the brief."""
    periods = {figure.period for figure in section.figures}
    for cohort in section.cohorts:  # a cohort scoped to a year makes that year a retrieved period
        periods |= {fy for fy in (cohort.query.fy_from, cohort.query.fy_to) if fy is not None}
    for text in _served_and_briefed_text(section):
        periods |= set(FY_LABEL.findall(text))
    return periods


def _served_and_briefed_text(section: RetrievedSection) -> list[str]:
    """Text that is not the model's invention: the server's refusals, the brief, and the labels.

    The labels are authored here, in code, and shown to the drafter as part of the evidence ("wage
    rates above Rs 1,000/day", "facts the record serves (FY 2018-19 to 2025-26)"). A drafter that
    may read a label but not repeat what it says is being set up to fail.
    """
    texts = [section.plan.brief]
    texts.extend(figure.label for figure in section.figures)
    texts.extend(derivation.label for derivation in section.derivations)
    texts.extend(cohort.label for cohort in section.cohorts)
    for exhibit in section.refusals:
        texts.append(exhibit.call)
        texts.append(exhibit.label)
        texts.extend(v for v in exhibit.payload.values() if isinstance(v, str))
    return texts


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
