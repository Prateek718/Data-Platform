"""Pure export transforms: SeriesFact → flat row + deep lineage record, and deterministic bytes.

No archive access, no I/O — every function here is a pure mapping so the whole export is unit-tested
without the (slow) archive assembly, and repeated runs are byte-identical. A ``fact_id`` (a stable
hash of the canonical key) is the join key between the flat CSVs and ``lineage.jsonl``.

``resource_map`` (``id(SourceValue) → resource_id``) supplies the ``contributing_resource_ids`` the
reconciliation lineage itself does not carry (it records publisher-level ``source_id`` only); the
build layer populates it during its own extraction. Values stay ``None`` when absent — never 0
(TIER-1 rule 4).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal

from data_platform.harmonize.models import (
    AggregateCoverage,
    CanonicalKey,
    DefinitionDiscrepancy,
    Disagreement,
    SourceValue,
)
from data_platform.harmonize.series import Basis, SeriesFact

STATE_COLUMNS = [
    "state_lgd_code",
    "state_name",
    "financial_year",
    "metric",
    "value",
    "unit",
    "era_basis",
    "confidence",
    "sources_seen_count",
    "contributing_resource_ids",
    "fact_id",
]
NATIONAL_COLUMNS = [c for c in STATE_COLUMNS if c not in ("state_lgd_code", "state_name")]
DISTRICT_COLUMNS = [
    "state_lgd_code",
    "state_name",
    "district_lgd_code",
    "district_name",
    "financial_year",
    "metric",
    "value",
    "unit",
    "grain",
    "confidence",
    "sources_seen_count",
    "contributing_resource_ids",
    "fact_id",
]


def fact_id(key: CanonicalKey) -> str:
    """A stable 16-hex-char id for a canonical key — the CSV↔lineage join key.

    Deterministic and collision-resistant over the key's identifying fields; equal keys always map
    to the same id, and a change in any field changes the id.
    """
    raw = "|".join(
        (
            key.scheme,
            key.geo_level.value,
            key.state_code or "",
            key.district_code or "",
            key.fin_year,
            key.month or "",
            key.metric,
        )
    )
    return hashlib.blake2b(raw.encode("utf-8"), digest_size=8).hexdigest()


def _era_basis(basis: Basis) -> str:
    """Two-valued era descriptor: the flagship rollup (2018+) vs historical sources (pre-2018)."""
    return "flagship-rollup" if basis is Basis.FLAGSHIP_ROLLUP else "historical"


def _contributing_resource_ids(fact: SeriesFact, resource_map: Mapping[int, str]) -> str:
    """Distinct resource ids that carried a value for this fact, deduped + sorted, ';'-joined."""
    seen = fact.reconciliation.sources_seen
    ids = {resource_map[id(sv)] for sv in seen if id(sv) in resource_map}
    return ";".join(sorted(ids))


def _base_row(fact: SeriesFact, resource_map: Mapping[int, str]) -> dict[str, object]:
    """The columns shared by every flat row (metric-level fact fields, no geography)."""
    return {
        "financial_year": fact.key.fin_year,
        "metric": fact.key.metric,
        "value": fact.value,  # Decimal | None — serialized later; None stays None (never 0)
        "unit": fact.unit,
        "confidence": fact.confidence.value,
        "sources_seen_count": len(fact.reconciliation.sources_seen),
        "contributing_resource_ids": _contributing_resource_ids(fact, resource_map),
        "fact_id": fact_id(fact.key),
    }


def state_row(
    fact: SeriesFact, *, state_names: Mapping[str, str], resource_map: Mapping[int, str]
) -> dict[str, object]:
    """A flat state-spine row (state LGD code + name, then the shared fact columns + era basis)."""
    base = _base_row(fact, resource_map)
    code = fact.key.state_code or ""
    row: dict[str, object] = {
        "state_lgd_code": code,
        "state_name": state_names.get(code, ""),
        "financial_year": base["financial_year"],
        "metric": base["metric"],
        "value": base["value"],
        "unit": base["unit"],
        "era_basis": _era_basis(fact.basis),
        "confidence": base["confidence"],
        "sources_seen_count": base["sources_seen_count"],
        "contributing_resource_ids": base["contributing_resource_ids"],
        "fact_id": base["fact_id"],
    }
    return row


def national_row(fact: SeriesFact, *, resource_map: Mapping[int, str]) -> dict[str, object]:
    """A flat national-spine row — the state row without geography (national has no LGD code)."""
    base = _base_row(fact, resource_map)
    return {
        "financial_year": base["financial_year"],
        "metric": base["metric"],
        "value": base["value"],
        "unit": base["unit"],
        "era_basis": _era_basis(fact.basis),
        "confidence": base["confidence"],
        "sources_seen_count": base["sources_seen_count"],
        "contributing_resource_ids": base["contributing_resource_ids"],
        "fact_id": base["fact_id"],
    }


def district_row(
    fact: SeriesFact,
    *,
    state_names: Mapping[str, str],
    district_names: Mapping[tuple[str, str], str],
    resource_map: Mapping[int, str],
) -> dict[str, object]:
    """A flat district drill-down row. The file is single-grain: every fact is ``district-annual``
    (the additive FY-finals and the FY-final wage rate alike), so there is no ``month`` column."""
    base = _base_row(fact, resource_map)
    state = fact.key.state_code or ""
    district = fact.key.district_code or ""
    return {
        "state_lgd_code": state,
        "state_name": state_names.get(state, ""),
        "district_lgd_code": district,
        "district_name": district_names.get((state, district), ""),
        "financial_year": base["financial_year"],
        "metric": base["metric"],
        "value": base["value"],
        "unit": base["unit"],
        "grain": "district-annual",
        "confidence": base["confidence"],
        "sources_seen_count": base["sources_seen_count"],
        "contributing_resource_ids": base["contributing_resource_ids"],
        "fact_id": base["fact_id"],
    }


def _coverage(coverage: AggregateCoverage | None) -> dict[str, object] | None:
    if coverage is None:
        return None
    return {
        "units_summed": coverage.units_summed,
        "units_in_source_universe": coverage.units_in_source_universe,
        "units_in_lgd": coverage.units_in_lgd,
        "status": coverage.status.value,
    }


def _discrepancy(discrepancy: DefinitionDiscrepancy | None) -> dict[str, object] | None:
    if discrepancy is None:
        return None
    return {
        "derived": str(discrepancy.derived),
        "source_provided": str(discrepancy.source_provided),
        "pct": str(discrepancy.pct),
        "rule_id": discrepancy.rule_id,
    }


def _source_ref(sv: SourceValue, resource_map: Mapping[int, str]) -> dict[str, object]:
    """One source's full lineage row: publisher + resource id, value, unit, as-of, editions."""
    return {
        "source_id": sv.source_id,
        "resource_id": resource_map.get(id(sv)),
        "value": str(sv.value),
        "original_unit": sv.original_unit,
        "source_as_of": sv.source_as_of.isoformat() if sv.source_as_of is not None else None,
        "authority_rank": sv.authority_rank,
        "rounding_epsilon": str(sv.rounding_epsilon),
        "edition_span_end": sv.edition_span_end,
        "is_edition_terminal": sv.is_edition_terminal,
        "aggregate_coverage": _coverage(sv.aggregate_coverage),
        "definition_discrepancy": _discrepancy(sv.definition_discrepancy),
    }


def _disagreement(disagreement: Disagreement | None) -> dict[str, object] | None:
    if disagreement is None:
        return None
    return {
        "pct": str(disagreement.pct),
        "rejected_sources": list(disagreement.rejected_sources),
        "rule_id": disagreement.rule_id,
        "material": disagreement.material,
    }


def lineage_record(fact: SeriesFact, *, resource_map: Mapping[int, str]) -> dict[str, object]:
    """The deep per-fact lineage object (one JSONL line), keyed by ``fact_id``.

    Carries every source seen (with resource id, as-of, edition markers, coverage), the recorded
    disagreement, and the removed-before-adjudication buckets (coverage-absent, scale-quarantined,
    edition-superseded, partial-period) — nothing the reconciliation held is dropped.
    """
    key, rec = fact.key, fact.reconciliation
    return {
        "fact_id": fact_id(key),
        "key": {
            "scheme": key.scheme,
            "geo_level": key.geo_level.value,
            "state_code": key.state_code,
            "district_code": key.district_code,
            "fin_year": key.fin_year,
            "month": key.month,
            "metric": key.metric,
        },
        "value": None if fact.value is None else str(fact.value),
        "unit": fact.unit,
        "basis": fact.basis.value,
        "confidence": fact.confidence.value,
        "resolution_rule_id": rec.resolution_rule_id,
        "adjudicated": rec.adjudicated,
        "quarantined": fact.quarantined,
        "quarantine_reason": fact.quarantine_reason,
        "sources_seen": [_source_ref(sv, resource_map) for sv in rec.sources_seen],
        "disagreement": _disagreement(rec.disagreement),
        "coverage_absent": [_source_ref(sv, resource_map) for sv in rec.coverage_absent],
        "scale_quarantined": [_source_ref(sv, resource_map) for sv in rec.scale_quarantined],
        "edition_superseded": [_source_ref(sv, resource_map) for sv in rec.edition_superseded],
        "partial_period": [_source_ref(sv, resource_map) for sv in rec.partial_period],
    }


def _cell(value: object) -> str:
    """Format one CSV cell: Decimal as a plain string, None as empty (never 0), else ``str``."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")  # plain decimal, never scientific notation
    return str(value)


def sort_rows(
    rows: Sequence[Mapping[str, object]], sort_by: Sequence[str]
) -> list[Mapping[str, object]]:
    """Deterministically order rows by the string form of the ``sort_by`` columns (shared by all
    serializers so CSV and Parquet emit identical row order)."""
    return sorted(rows, key=lambda r: tuple(_cell(r.get(k)) for k in sort_by))


def csv_bytes(
    rows: Sequence[Mapping[str, object]], *, columns: Sequence[str], sort_by: Sequence[str]
) -> bytes:
    """Serialize rows to deterministic CSV bytes: sorted by ``sort_by``, fixed column order, LF."""
    ordered = sort_rows(rows, sort_by)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in ordered:
        writer.writerow([_cell(row.get(column)) for column in columns])
    return buffer.getvalue().encode("utf-8")


def jsonl_bytes(records: Sequence[Mapping[str, object]], *, sort_by: str) -> bytes:
    """Serialize records to deterministic JSONL bytes: one object per line, ``sort_by`` order."""
    ordered = sorted(records, key=lambda r: str(r[sort_by]))
    lines = [json.dumps(record, ensure_ascii=False) for record in ordered]
    return ("\n".join(lines) + "\n").encode("utf-8")
