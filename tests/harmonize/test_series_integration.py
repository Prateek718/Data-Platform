"""Series assembly end-to-end over the real archive — continuous expenditure series across the 2018
seam. Pre-2018: the three MoSPI Financial Outcomes state files (corroborating); 2018+: the flagship
rolled up to state-annual. Skips when the gitignored archive snapshot is absent.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from data_platform.harmonize.config import WAGES_EXPENDITURE
from data_platform.harmonize.extract import flagship_state_annual_cumulative
from data_platform.harmonize.historical import FINANCIAL_OUTCOMES_RULES, extract_historical_state
from data_platform.harmonize.series import Basis, Confidence, SeriesFact, assemble_series
from data_platform.ingest.archive import read_archive_batch
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.config import NORMALIZE_CONFIG
from data_platform.normalize.models import CleanCell, NormalizedBatch
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.config import RESOLVE_CONFIG
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import load_lgd_reference
from data_platform.resolve.pipeline import resolve_batch
from data_platform.wiring.specs import WIRED

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
_FIN_OUTCOMES = [  # MoSPI Financial Outcomes state family (wages/material/admin, INR lakh)
    "d64434e9",
    "18527128",
    "fd7c50d2",
]
_HISTORICAL_RANK = 10

pytestmark = pytest.mark.skipif(
    not (ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json").exists(),
    reason="local archive snapshot not present",
)


def _full(prefix: str) -> str:
    return next(r for r in WIRED if r.startswith(prefix))


def _resolver() -> GeoResolver:
    states, districts = load_lgd_reference(
        ARCHIVE / "lgd" / "lgd_states.json", ARCHIVE / "lgd" / "lgd_districts.json"
    )
    return GeoResolver.from_reference(states=states, districts=districts)


def _cells(batch: NormalizedBatch) -> dict[int, dict[str, CleanCell]]:
    return {r.row_index: dict(r.cells) for r in batch.records}


def _lgd_counts() -> dict[str, int]:
    records = json.loads((ARCHIVE / "lgd" / "lgd_districts.json").read_text())["records"]
    return dict(Counter(str(r["state_code"]) for r in records))


@pytest.fixture(scope="module")
def series() -> list[SeriesFact]:
    resolver = _resolver()
    lgd = _lgd_counts()
    keyed = []

    # 2018+ : flagship rolled up to state-annual (rank 0), for the three expenditure metrics.
    fb = read_archive_batch(
        resource_id=FLAGSHIP_RESOURCE_ID,
        source_id=SRC_FLAGSHIP,
        source_grain="district+monthly",
        path=ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json",
    )
    fn = normalize_batch(fb, config=NORMALIZE_CONFIG[FLAGSHIP_RESOURCE_ID])
    fr = resolve_batch(fn, resolver, config=RESOLVE_CONFIG[FLAGSHIP_RESOURCE_ID])
    for metric in ("wages_expenditure", "material_skilled_expenditure", "admin_expenditure"):
        keyed += flagship_state_annual_cumulative(
            fr, _cells(fn), metric=metric, source_as_of=fb.source_as_of, lgd_district_counts=lgd
        )

    # pre-2018 : the three Financial Outcomes state files (rank 10, corroborating).
    for prefix in _FIN_OUTCOMES:
        rid = _full(prefix)
        spec = WIRED[rid]
        rb = read_archive_batch(
            resource_id=rid,
            source_id=spec.source_id,
            source_grain=spec.source_grain,
            path=ARCHIVE / spec.file,
        )
        rn = normalize_batch(rb, config=spec.normalize_config)
        rr = resolve_batch(rn, resolver, config=spec.resolve_config)
        keyed += extract_historical_state(
            rr,
            _cells(rn),
            FINANCIAL_OUTCOMES_RULES,
            source_as_of=rb.source_as_of,
            authority_rank=_HISTORICAL_RANK,
        )

    return assemble_series(keyed, flagship_source_id=SRC_FLAGSHIP)


def _wages(series: list[SeriesFact]) -> list[SeriesFact]:
    return [f for f in series if f.key.metric == WAGES_EXPENDITURE]


def test_series_is_continuous_across_the_2018_seam(series: list[SeriesFact]) -> None:
    # Pick a state present in both eras and confirm wages_expenditure spans pre- and post-2018.
    wages = _wages(series)
    by_state: dict[str, set[str]] = {}
    for f in wages:
        by_state.setdefault(f.key.state_code or "", set()).add(f.key.fin_year)
    spanning = [
        s
        for s, yrs in by_state.items()
        if any(y < "2018" for y in yrs) and any(y >= "2018" for y in yrs)
    ]
    assert spanning, "expected at least one state with wages both pre- and post-2018 (continuous)"


def test_2018plus_basis_is_flagship_pre2018_is_historical(series: list[SeriesFact]) -> None:
    for f in _wages(series):
        if f.key.fin_year >= "2018-19":
            assert f.basis is Basis.FLAGSHIP_ROLLUP
        else:
            assert f.basis in (Basis.HISTORICAL_MULTI, Basis.HISTORICAL_SINGLE)


def test_pre2018_expenditure_has_corroborated_cells(series: list[SeriesFact]) -> None:
    # The three Financial Outcomes files overlap ~2010-2014, so some pre-2018 wages corroborate.
    corroborated = [
        f
        for f in _wages(series)
        if f.key.fin_year < "2018" and f.confidence is Confidence.CORROBORATED
    ]
    assert corroborated, "expected corroborated (>=2 source) pre-2018 wages cells"


def test_all_three_expenditure_metrics_present(series: list[SeriesFact]) -> None:
    metrics = {f.key.metric for f in series}
    assert {"wages_expenditure", "material_skilled_expenditure", "admin_expenditure"} <= metrics
