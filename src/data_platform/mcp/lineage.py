"""get_lineage — full provenance for a fact, served from a typed core model.

The DuckDB ``lineage`` table stores each record as raw JSON keyed by ``fact_id`` (a pure store).
This module reads the requested records, parses each into a typed :class:`LineageRecord`, and shapes
the API response from that model — so the storage shape does not dictate the API shape and the
provenance logic (reconciliation status, rejected value, materiality, null reason) is plain,
testable Python. A null cell is DATA here: it is returned with its reason, not refused.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from data_platform.mcp import schema
from data_platform.mcp.loader import Dataset

# Coarse reconciliation status per confidence state (the precise state is also returned).
_STATUS_BY_CONFIDENCE: dict[str, str] = {
    "cross-publisher": "corroborated",
    "single-publisher multi-vintage": "corroborated",
    "immaterial divergence": "corroborated",
    "flagged-disagreement": "flagged conflict",
    "edition-superseded": "edition-superseded",
    "unadjudicated": "unadjudicated",
    "single-publisher divergence": "unadjudicated",
    "partial-period-only": "partial-period-only",
    "single-source": "single-source",
}


@dataclass(frozen=True)
class SourceRef:
    source_id: str | None
    resource_id: str | None
    value: str | None
    source_as_of: str | None
    authority_rank: int | None

    @classmethod
    def parse(cls, raw: dict[str, object]) -> SourceRef:
        rank = raw.get("authority_rank")
        return cls(
            source_id=_opt_str(raw.get("source_id")),
            resource_id=_opt_str(raw.get("resource_id")),
            value=_opt_str(raw.get("value")),
            source_as_of=_opt_str(raw.get("source_as_of")),
            authority_rank=int(rank) if isinstance(rank, int) else None,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "resource_id": self.resource_id,
            "value": self.value,
            "as_of": self.source_as_of,
            "authority_rank": self.authority_rank,
        }


@dataclass(frozen=True)
class Disagreement:
    pct: str | None
    rejected_sources: tuple[str, ...]
    rule_id: str | None
    material: bool

    @classmethod
    def parse(cls, raw: dict[str, object]) -> Disagreement:
        rejected = raw.get("rejected_sources")
        return cls(
            pct=_opt_str(raw.get("pct")),
            rejected_sources=tuple(str(s) for s in rejected) if isinstance(rejected, list) else (),
            rule_id=_opt_str(raw.get("rule_id")),
            material=bool(raw.get("material")),
        )


@dataclass(frozen=True)
class LineageRecord:
    fact_id: str
    metric: str
    geo_level: str | None
    state_code: str | None
    district_code: str | None
    fin_year: str | None
    value: str | None
    unit: str | None
    confidence: str
    resolution_rule_id: str | None
    adjudicated: bool
    quarantined: bool
    quarantine_reason: str | None
    sources_seen: tuple[SourceRef, ...]
    disagreement: Disagreement | None

    @classmethod
    def parse(cls, raw: dict[str, object]) -> LineageRecord:
        key = raw.get("key")
        key = key if isinstance(key, dict) else {}
        sources = raw.get("sources_seen")
        disagreement = raw.get("disagreement")
        return cls(
            fact_id=str(raw["fact_id"]),
            metric=str(key.get("metric")),
            geo_level=_opt_str(key.get("geo_level")),
            state_code=_opt_str(key.get("state_code")),
            district_code=_opt_str(key.get("district_code")),
            fin_year=_opt_str(key.get("fin_year")),
            value=_opt_str(raw.get("value")),
            unit=_opt_str(raw.get("unit")),
            confidence=str(raw.get("confidence")),
            resolution_rule_id=_opt_str(raw.get("resolution_rule_id")),
            adjudicated=bool(raw.get("adjudicated")),
            quarantined=bool(raw.get("quarantined")),
            quarantine_reason=_opt_str(raw.get("quarantine_reason")),
            sources_seen=tuple(SourceRef.parse(s) for s in sources if isinstance(s, dict))
            if isinstance(sources, list)
            else (),
            disagreement=Disagreement.parse(disagreement)
            if isinstance(disagreement, dict)
            else None,
        )


def get_lineage(ds: Dataset, fact_ids: str | Sequence[str]) -> dict[str, object]:
    """Return full provenance for one or more ``fact_id``s as ``{requested, records}``.

    Each record carries its source references, reconciliation status, rejected value (where one
    exists), materiality reading, and — for a null cell — its null reason. An unknown ``fact_id``
    yields a ``{"found": false}`` record rather than a refusal, so batch requests stay well-formed.
    """
    requested = [fact_ids] if isinstance(fact_ids, str) else list(fact_ids)
    parsed = _load_records(ds, requested)
    records = [
        _provenance(parsed[fid]) if fid in parsed else {"fact_id": fid, "found": False}
        for fid in requested
    ]
    return {"requested": requested, "records": records}


def _load_records(ds: Dataset, fact_ids: Sequence[str]) -> dict[str, LineageRecord]:
    if not fact_ids:
        return {}
    placeholders = ", ".join("?" for _ in fact_ids)
    rows = ds.con.execute(
        f"SELECT fact_id, record FROM lineage WHERE fact_id IN ({placeholders})", list(fact_ids)
    ).fetchall()
    return {str(fid): LineageRecord.parse(json.loads(record)) for fid, record in rows}


def _provenance(record: LineageRecord) -> dict[str, object]:
    return {
        "fact_id": record.fact_id,
        "found": True,
        "metric": record.metric,
        "unit": record.unit,
        "financial_year": record.fin_year,
        "geo": {
            "level": record.geo_level,
            "state_code": record.state_code,
            "district_code": record.district_code,
        },
        "value": record.value,
        "confidence": record.confidence,
        "reconciliation_status": _STATUS_BY_CONFIDENCE.get(record.confidence, record.confidence),
        "resolution_rule_id": record.resolution_rule_id,
        "adjudicated": record.adjudicated,
        "quarantined": record.quarantined,
        "sources": [s.to_dict() for s in record.sources_seen],
        "rejected": _rejected(record),
        "materiality": _materiality(record),
        "null_reason": _null_reason(record),
    }


def _rejected(record: LineageRecord) -> list[dict[str, object]]:
    """The source values rejected by the recorded disagreement (empty when none)."""
    if record.disagreement is None:
        return []
    rejected_ids = set(record.disagreement.rejected_sources)
    return [
        {"source_id": s.source_id, "resource_id": s.resource_id, "value": s.value}
        for s in record.sources_seen
        if s.source_id in rejected_ids
    ]


def _materiality(record: LineageRecord) -> dict[str, object] | None:
    """The materiality reading of a disagreement: absolute spread (in unit-class) and relative %."""
    if record.disagreement is None:
        return None
    metric = schema.METRICS.get(record.metric)
    values = [_decimal(s.value) for s in record.sources_seen]
    numeric = [v for v in values if v is not None]
    absolute = format(max(numeric) - min(numeric), "f") if len(numeric) >= 2 else None
    return {
        "absolute": absolute,
        "unit": metric.unit if metric is not None else record.unit,
        "unit_class": metric.unit_class.value if metric is not None else None,
        "relative_pct": record.disagreement.pct,
        "material": record.disagreement.material,
    }


def _null_reason(record: LineageRecord) -> dict[str, object] | None:
    """For a null cell, its reason (partial-period-only / unadjudicated / divergence); else None."""
    if record.value is not None:
        return None
    reason = schema.NULL_REASON_BY_CONFIDENCE.get(record.confidence)
    if reason is None:
        return None
    reasons = schema.NULL_SEMANTICS["null_reasons"]
    assert isinstance(reasons, dict)
    return {"reason": reason, "explanation": reasons.get(reason)}


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (ArithmeticError, ValueError):
        return None
