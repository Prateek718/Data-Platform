"""Extract canonical metric values from the PRE-2018 historical sources (already resolved).

Stage 3.5 lands each historical source as resolved state (or national) rows with melted cells
``{_metric: <column stem>, _fin_year, _value}``. This module maps those stems to canonical metrics
and normalizes their units — the per-source "metric mapping", config-carried as explicit rules.
It is NOT adjudication: it just produces per-(geo, FY, metric) :class:`SourceValue`s that the
Stage-4 reconciler then trusts/compares. Rules are pattern-based so one rule covers a source
family's stem spelling variants (e.g. "Expenditure on (In Lakhs) - Wages -" vs "...(` In lakhs)…").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from data_platform.harmonize.config import (
    ADMIN_EXPENDITURE,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    HOUSEHOLDS_EMPLOYED,
    MATERIAL_SKILLED_EXPENDITURE,
    PERSONDAYS_GENERATED,
    TOTAL_EXPENDITURE,
    WAGES_EXPENDITURE,
)
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.harmonize.units import CountScale, MoneyUnit, to_canonical_lakh, to_raw_count
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch

Cells = dict[int, dict[str, CleanCell]]


class UnitKind(StrEnum):
    """How a source column's value must be normalized to the metric's canonical unit."""

    MONEY_LAKH = "money_lakh"  # already INR lakh → canonical money unit, no scaling
    COUNT_RAW = "count_raw"  # already a raw count
    COUNT_LAKH = "count_lakh"  # a count "in lakh" → × 100,000


@dataclass(frozen=True)
class StemRule:
    """Map a source ``_metric`` stem (by regex) to a canonical metric + its unit normalization."""

    pattern: re.Pattern[str]
    metric: str
    unit_kind: UnitKind


# Stems to skip outright — percentages, releases/funds, and per-category or rate breakdowns that are
# NOT the canonical metric (never map these; they share keywords but mean something else).
STEM_EXCLUDE = re.compile(
    r"%|percentage|central release|funds available|- scs|- sts|- others|- women"
    r"|average|beneficiary|demanded|not paid|rejection|allotted|registered|wage rate|per personday",
    re.I,
)

# The MoSPI "Financial Outcomes" family: wages / material / administration / total expenditure,
# published in INR lakh. One rule set covers all three files' stem-spelling variants.
FINANCIAL_OUTCOMES_RULES: tuple[StemRule, ...] = (
    StemRule(re.compile(r"expenditure on.*wages", re.I), WAGES_EXPENDITURE, UnitKind.MONEY_LAKH),
    StemRule(
        re.compile(r"expenditure on.*material", re.I),
        MATERIAL_SKILLED_EXPENDITURE,
        UnitKind.MONEY_LAKH,
    ),
    StemRule(
        re.compile(r"expenditure on.*(administration|admin)", re.I),
        ADMIN_EXPENDITURE,
        UnitKind.MONEY_LAKH,
    ),
    StemRule(re.compile(r"expenditure on.*total", re.I), TOTAL_EXPENDITURE, UnitKind.MONEY_LAKH),
)

# MoSPI "Implementation Report" state family: households provided + 100-days as RAW counts,
# persondays as a lakh count. (Demanded / per-category / average stems are excluded above.)
MOSPI_IMPLEMENTATION_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"households provided employment", re.I), HOUSEHOLDS_EMPLOYED, UnitKind.COUNT_RAW
    ),
    StemRule(
        re.compile(r"availed 100 days|100 days of employment", re.I),
        HOUSEHOLDS_COMPLETED_100_DAYS,
        UnitKind.COUNT_RAW,
    ),
    StemRule(
        re.compile(r"persondays in lakhs - total", re.I),
        PERSONDAYS_GENERATED,
        UnitKind.COUNT_LAKH,
    ),
)

# RS "households provided employment" tables — provided-employment counts published in lakh.
RS_HOUSEHOLDS_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"provided.?employment|hh.*provided|household.*provided", re.I),
        HOUSEHOLDS_EMPLOYED,
        UnitKind.COUNT_LAKH,
    ),
)

# RS "households completed 100 days" table — a raw count ("... in nos ...").
RS_HUNDRED_DAYS_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"completed 100 days|100 days", re.I),
        HOUSEHOLDS_COMPLETED_100_DAYS,
        UnitKind.COUNT_RAW,
    ),
)

# National sources are WIDE (one row per FY, one column per metric) — not melted. Column names use
# underscores, so patterns use ``.`` between words. Provided-employment / availed-100-days are raw
# counts; persondays is a lakh count. (The subcategory persondays "___scs/sts/…" columns don't match
# the specific "…total" pattern; "demanded"/"average" are dropped by STEM_EXCLUDE.)
NATIONAL_IMPLEMENTATION_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"households.provided.employment", re.I),
        HOUSEHOLDS_EMPLOYED,
        UnitKind.COUNT_RAW,
    ),
    StemRule(
        re.compile(r"availed.100.days", re.I), HOUSEHOLDS_COMPLETED_100_DAYS, UnitKind.COUNT_RAW
    ),
    StemRule(
        re.compile(r"persondays.in.lakhs.+total", re.I), PERSONDAYS_GENERATED, UnitKind.COUNT_LAKH
    ),
)

# Wired historical NATIONAL sources: (resource-id prefix, rules). Financial-Outcomes national reuses
# the expenditure rules — the "% Age …" and "Central Release" columns are dropped by STEM_EXCLUDE.
HISTORICAL_NATIONAL_SOURCES: tuple[tuple[str, tuple[StemRule, ...]], ...] = (
    ("04476f1d", NATIONAL_IMPLEMENTATION_RULES),
    ("1878204d", NATIONAL_IMPLEMENTATION_RULES),
    ("54d1a5fa", NATIONAL_IMPLEMENTATION_RULES),
    ("d88e2cb6", NATIONAL_IMPLEMENTATION_RULES),
    ("7496d75d", FINANCIAL_OUTCOMES_RULES),
    ("8d734637", FINANCIAL_OUTCOMES_RULES),
    ("99a91845", FINANCIAL_OUTCOMES_RULES),
)

# Which GENUINE historical STATE sources are wired, and the rule set each uses (resource-id prefix →
# rules). Verified against the archive: MoSPI raw counts vs RS lakh counts agree on clean full-year
# cells (the residual differences are real — partial-year snapshots / revisions — and get flagged).
HISTORICAL_STATE_SOURCES: tuple[tuple[str, tuple[StemRule, ...]], ...] = (
    ("d64434e9", FINANCIAL_OUTCOMES_RULES),
    ("18527128", FINANCIAL_OUTCOMES_RULES),
    ("fd7c50d2", FINANCIAL_OUTCOMES_RULES),
    ("2d0a4136", MOSPI_IMPLEMENTATION_RULES),
    ("3ebbea46", MOSPI_IMPLEMENTATION_RULES),
    ("9aefcd0f", MOSPI_IMPLEMENTATION_RULES),
    ("c11b65d4", MOSPI_IMPLEMENTATION_RULES),
    ("34a83496", RS_HOUSEHOLDS_RULES),
    ("6c12385f", RS_HOUSEHOLDS_RULES),
    ("c5c8858c", RS_HOUSEHOLDS_RULES),
    ("e5491ee9", RS_HOUSEHOLDS_RULES),
    ("cb137c04", RS_HOUSEHOLDS_RULES),
    ("2611cc74", RS_HOUSEHOLDS_RULES),
    ("22f8cdb0", RS_HOUSEHOLDS_RULES),
    ("73d68992", RS_HUNDRED_DAYS_RULES),
)


def _normalize(value: Decimal, unit_kind: UnitKind) -> tuple[Decimal, str]:
    if unit_kind is UnitKind.MONEY_LAKH:
        out = to_canonical_lakh(value, MoneyUnit.LAKH)
        return out.value_lakh, out.original_unit  # type: ignore[return-value]  # value non-None here
    scale = CountScale.LAKH if unit_kind is UnitKind.COUNT_LAKH else CountScale.COUNT
    out2 = to_raw_count(value, scale)
    return out2.value, out2.original_unit  # type: ignore[return-value]


def extract_national_wide(
    resolved: ResolvedBatch,
    cells: Cells,
    rules: tuple[StemRule, ...],
    *,
    fy_column: str,
    source_as_of: datetime | None,
    authority_rank: int,
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Map a WIDE national source (one row per FY, one column per metric) to national SourceValues.

    ``fy_column`` names the financial-year column (the source's grain key). Each other column is
    matched against ``rules`` (after ``STEM_EXCLUDE``); the matching cell's value is normalized.
    """
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.geo_level is not GeoLevel.NATIONAL:
            continue
        row = cells[record.row_index]
        fin_year = row.get(fy_column)
        if not isinstance(fin_year, str):
            continue
        for column, raw in row.items():
            if column == fy_column or raw is None or STEM_EXCLUDE.search(column):
                continue
            rule = next((r for r in rules if r.pattern.search(column)), None)
            if rule is None:
                continue
            try:
                value = Decimal(str(raw))
            except InvalidOperation:
                continue
            canonical_value, original_unit = _normalize(value, rule.unit_kind)
            key = CanonicalKey(
                scheme="MGNREGA",
                geo_level=GeoLevel.NATIONAL,
                state_code=None,
                district_code=None,
                fin_year=fin_year,
                month=None,
                metric=rule.metric,
            )
            out.append(
                (
                    key,
                    SourceValue(
                        source_id=resolved.source_id,
                        value=canonical_value,
                        original_unit=original_unit,
                        source_as_of=source_as_of,
                        authority_rank=authority_rank,
                    ),
                )
            )
    return out


def extract_historical_state(
    resolved: ResolvedBatch,
    cells: Cells,
    rules: tuple[StemRule, ...],
    *,
    source_as_of: datetime | None,
    authority_rank: int,
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Map a resolved historical STATE batch to per-(state, FY, metric) SourceValues."""
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.state_canonical_id is None:
            continue
        row = cells[record.row_index]
        stem = row.get("_metric")
        fin_year = row.get("_fin_year")
        raw = row.get("_value")
        if not isinstance(stem, str) or not isinstance(fin_year, str) or raw is None:
            continue
        if STEM_EXCLUDE.search(stem):
            continue
        rule = next((r for r in rules if r.pattern.search(stem)), None)
        if rule is None:
            continue
        try:
            value = Decimal(str(raw))
        except InvalidOperation:
            continue
        canonical_value, original_unit = _normalize(value, rule.unit_kind)
        key = CanonicalKey(
            scheme="MGNREGA",
            geo_level=GeoLevel.STATE,
            state_code=record.state_canonical_id,
            district_code=None,
            fin_year=fin_year,
            month=None,
            metric=rule.metric,
        )
        out.append(
            (
                key,
                SourceValue(
                    source_id=resolved.source_id,
                    value=canonical_value,
                    original_unit=original_unit,
                    source_as_of=source_as_of,
                    authority_rank=authority_rank,
                ),
            )
        )
    return out
