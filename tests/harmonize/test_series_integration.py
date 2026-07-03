"""Series assembly end-to-end over the real archive — continuous expenditure series across the 2018
seam. Pre-2018: the three MoSPI Financial Outcomes state files (corroborating); 2018+: the flagship
rolled up to state-annual. Skips when the gitignored archive snapshot is absent.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from data_platform.harmonize.config import (
    ACTIVE_WORKERS,
    ADMIN_EXPENDITURE,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    HOUSEHOLDS_EMPLOYED,
    MATERIAL_SKILLED_EXPENDITURE,
    PERSONDAYS_GENERATED,
    TOTAL_EXPENDITURE,
    WAGES_EXPENDITURE,
)
from data_platform.harmonize.extract import (
    flagship_state_annual_cumulative,
    flagship_state_annual_persondays,
    flagship_state_annual_total_expenditure,
    roll_to_national,
)
from data_platform.harmonize.historical import (
    FINANCIAL_OUTCOMES_RULES,
    HISTORICAL_NATIONAL_SOURCES,
    HISTORICAL_STATE_SOURCES,
    extract_historical_state,
    extract_national_wide,
)
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.harmonize.series import (
    Basis,
    Confidence,
    SeriesFact,
    assemble_series,
    series_coverage_summary,
)
from data_platform.ingest.archive import read_archive_batch
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.config import NORMALIZE_CONFIG
from data_platform.normalize.models import CleanCell, NormalizedBatch
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.config import RESOLVE_CONFIG
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import load_lgd_reference
from data_platform.resolve.models import GeoLevel, ResolvedBatch
from data_platform.resolve.pipeline import resolve_batch
from data_platform.wiring.specs import WIRED

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
Cells = dict[int, dict[str, CleanCell]]
_KeyedValue = tuple[CanonicalKey, SourceValue]
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


def test_pre2018_expenditure_has_single_publisher_corroborated_cells(
    series: list[SeriesFact],
) -> None:
    # The three Financial Outcomes files overlap ~2010-2014, so some pre-2018 wages cells have >=2
    # agreeing sources — but all three are MoSPI, so this is single-publisher multi-vintage (NOT
    # independent cross-publisher corroboration; wages has no non-MoSPI pre-2018 source).
    corroborated = [
        f
        for f in _wages(series)
        if f.key.fin_year < "2018" and f.confidence is Confidence.SINGLE_PUBLISHER
    ]
    assert corroborated, "expected single-publisher (>=2 MoSPI vintage) pre-2018 wages cells"
    assert not any(
        f.confidence is Confidence.CROSS_PUBLISHER
        for f in _wages(series)
        if f.key.fin_year < "2018"
    ), "pre-2018 wages is MoSPI-only — must never be labelled cross-publisher"


def test_all_three_expenditure_metrics_present(series: list[SeriesFact]) -> None:
    metrics = {f.key.metric for f in series}
    assert {"wages_expenditure", "material_skilled_expenditure", "admin_expenditure"} <= metrics


_STATE_ANNUAL_METRICS = (
    HOUSEHOLDS_EMPLOYED,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    ACTIVE_WORKERS,
    WAGES_EXPENDITURE,
    MATERIAL_SKILLED_EXPENDITURE,
    ADMIN_EXPENDITURE,
)


def _flagship_state_annual(resolver: GeoResolver, lgd: dict[str, int]) -> list[_KeyedValue]:
    """All flagship state-annual metric values (2018+ era), across all canonical metrics."""
    fb = read_archive_batch(
        resource_id=FLAGSHIP_RESOURCE_ID,
        source_id=SRC_FLAGSHIP,
        source_grain="district+monthly",
        path=ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json",
    )
    fn = normalize_batch(fb, config=NORMALIZE_CONFIG[FLAGSHIP_RESOURCE_ID])
    fr = resolve_batch(fn, resolver, config=RESOLVE_CONFIG[FLAGSHIP_RESOURCE_ID])
    fc = _cells(fn)
    keyed: list[_KeyedValue] = []
    for metric in _STATE_ANNUAL_METRICS:
        keyed += flagship_state_annual_cumulative(
            fr, fc, metric=metric, source_as_of=fb.source_as_of, lgd_district_counts=lgd
        )
    keyed += flagship_state_annual_persondays(
        fr, fc, source_as_of=fb.source_as_of, lgd_district_counts=lgd
    )
    keyed += flagship_state_annual_total_expenditure(
        fr, fc, source_as_of=fb.source_as_of, lgd_district_counts=lgd
    )
    return keyed


def _load_wired(prefix: str) -> tuple[ResolvedBatch, Cells, datetime | None, str]:
    """Load a wired source to (resolved batch, cells, source_as_of, its FY/grain-key column)."""
    rid = _full(prefix)
    spec = WIRED[rid]
    rb = read_archive_batch(
        resource_id=rid,
        source_id=spec.source_id,
        source_grain=spec.source_grain,
        path=ARCHIVE / spec.file,
    )
    rn = normalize_batch(rb, config=spec.normalize_config)
    rr = resolve_batch(rn, _resolver(), config=spec.resolve_config)
    return rr, _cells(rn), rb.source_as_of, spec.normalize_config.grain_key_columns[0]


@pytest.fixture(scope="module")
def full_state_series() -> list[SeriesFact]:
    """Whole STATE-annual series: flagship 2018+ (all metrics) + every wired historical source."""
    resolver = _resolver()
    lgd = _lgd_counts()
    keyed = _flagship_state_annual(resolver, lgd)
    for prefix, rules in HISTORICAL_STATE_SOURCES:
        rr, cells, as_of, _fy = _load_wired(prefix)
        keyed += extract_historical_state(rr, cells, rules, source_as_of=as_of, authority_rank=10)
    return assemble_series(keyed, flagship_source_id=SRC_FLAGSHIP)


@pytest.fixture(scope="module")
def national_series() -> list[SeriesFact]:
    """The NATIONAL parallel spine: historical national sources (pre-2018) + flagship rolled up."""
    resolver = _resolver()
    lgd = _lgd_counts()
    keyed = roll_to_national(
        _flagship_state_annual(resolver, lgd), source_id=SRC_FLAGSHIP, authority_rank=0
    )
    for prefix, rules in HISTORICAL_NATIONAL_SOURCES:
        rr, cells, as_of, fy = _load_wired(prefix)
        keyed += extract_national_wide(
            rr,
            cells,
            rules,
            fy_column=fy,
            source_as_of=as_of,
            authority_rank=10,
        )
    return assemble_series(keyed, flagship_source_id=SRC_FLAGSHIP)


def test_full_state_series_covers_all_eight_metrics(full_state_series: list[SeriesFact]) -> None:
    summary = series_coverage_summary(full_state_series)
    assert set(summary) == {
        HOUSEHOLDS_EMPLOYED,
        HOUSEHOLDS_COMPLETED_100_DAYS,
        ACTIVE_WORKERS,
        PERSONDAYS_GENERATED,
        WAGES_EXPENDITURE,
        MATERIAL_SKILLED_EXPENDITURE,
        ADMIN_EXPENDITURE,
        TOTAL_EXPENDITURE,
    }


def test_state_count_metrics_span_both_eras(full_state_series: list[SeriesFact]) -> None:
    summary = series_coverage_summary(full_state_series)
    for metric in (HOUSEHOLDS_EMPLOYED, HOUSEHOLDS_COMPLETED_100_DAYS, PERSONDAYS_GENERATED):
        assert summary[metric]["pre_2018"] > 0 and summary[metric]["y2018_plus"] > 0


def test_state_household_flagged_are_real_not_scale_bugs(
    full_state_series: list[SeriesFact],
) -> None:
    # A lakh/raw scale error would make almost every cell disagree by ~100,000x. The median pre-2018
    # household disagreement must be small (partial-year/revision divergence), proving units align.
    pcts = sorted(
        float(f.reconciliation.disagreement.pct)
        for f in full_state_series
        if f.key.metric == HOUSEHOLDS_EMPLOYED
        and f.key.fin_year < "2018"
        and f.reconciliation.disagreement is not None
    )
    assert pcts, "expected some pre-2018 household disagreements"
    assert pcts[len(pcts) // 2] < 100, "median household disagreement should be small (units align)"


def test_partial_year_household_columns_excluded_from_full_year_cells(
    full_state_series: list[SeriesFact],
) -> None:
    # The two RS partial-year columns (34a83496 FY2015-16 "upto 30.09.2015"; 6c12385f FY2016-17
    # "till 16.11.2016") previously injected a ~half-year value into EVERY state, flagging ~all 32
    # states in each year at 10-66%. After exclusion they cannot enter the full-year cell: the
    # ~half value is gone from every cell's lineage, so no source deviates by anywhere near 50%.
    cells = [
        f
        for f in full_state_series
        if f.key.metric == HOUSEHOLDS_EMPLOYED and f.key.fin_year in {"2015-16", "2016-17"}
    ]
    assert cells, "expected FY2015-16 / FY2016-17 household cells"
    flagged = [f for f in cells if f.reconciliation.disagreement is not None]
    assert len(flagged) < len(cells), "no longer almost-all flagged once the partial is excluded"
    for f in cells:
        if f.value is None or f.value < Decimal(100_000):  # skip near-zero UTs (own noise)
            continue
        worst = max(abs(f.value - s.value) / f.value for s in f.reconciliation.sources_seen)
        assert worst < Decimal("0.40"), (  # a retained partial would be ~0.45-0.66 off
            f"partial-year value still present in {f.key.state_code} {f.key.fin_year}: {worst}"
        )


def test_precision_aware_count_agreement_surfaces_cross_publisher(
    full_state_series: list[SeriesFact],
) -> None:
    # R4-REC-01a on the count metrics: an RS lakh-rounded count agrees with a MoSPI raw count within
    # the RS rounding granularity instead of being flagged by exact match. This reveals genuine
    # MoSPI+RS agreement as cross-publisher corroboration (which exact-match hid). households is the
    # only pre-2018 state metric with two independent publishers, so it is where this shows.
    xpub = [
        f
        for f in full_state_series
        if f.key.metric == HOUSEHOLDS_EMPLOYED
        and f.key.fin_year < "2018"
        and f.confidence is Confidence.CROSS_PUBLISHER
    ]
    assert len(xpub) >= 40, "precision-aware agreement should surface many cross-publisher cells"
    for f in xpub:
        publishers = {s.source_id for s in f.reconciliation.sources_seen}
        assert len(publishers) >= 2, "a cross-publisher cell must carry >=2 distinct publishers"

    # at least one cross-publisher cell agrees by rounding-precision, not exact equality: two of its
    # sources differ yet fall within the coarser source's rounding band (reconcile's max-epsilon).
    def agrees_within_rounding(fact: SeriesFact) -> bool:
        seen = fact.reconciliation.sources_seen
        return any(
            (eps := max(a.rounding_epsilon, b.rounding_epsilon)) > 0
            and 0 < abs(a.value - b.value) <= eps
            for a in seen
            for b in seen
        )

    assert any(agrees_within_rounding(f) for f in xpub), (
        "expected a cross-publisher cell agreeing within (not at) the rounding epsilon"
    )


def test_national_series_is_national_grain(national_series: list[SeriesFact]) -> None:
    assert national_series
    for f in national_series:
        assert f.key.geo_level is GeoLevel.NATIONAL
        assert f.key.state_code is None and f.key.district_code is None


def test_national_households_span_2006_to_2026(national_series: list[SeriesFact]) -> None:
    years = sorted(f.key.fin_year for f in national_series if f.key.metric == HOUSEHOLDS_EMPLOYED)
    assert years[0] == "2006-07"
    assert years[-1] >= "2026-27"
    # continuous across the seam: pre- and post-2018 both present, no missing FY in between.
    assert any(y < "2018" for y in years) and any(y >= "2018-19" for y in years)


def test_national_pre2018_corroboration_is_single_publisher(
    national_series: list[SeriesFact],
) -> None:
    # The national historical sources are all MoSPI (Implementation + Financial Outcomes national),
    # so pre-2018 national corroboration is single-publisher multi-vintage, never cross-publisher.
    single_pub = [
        f
        for f in national_series
        if f.key.fin_year < "2018" and f.confidence is Confidence.SINGLE_PUBLISHER
    ]
    assert single_pub, "expected >=2 MoSPI-vintage agreement in the national pre-2018 spine"
    assert not any(
        f.confidence is Confidence.CROSS_PUBLISHER
        for f in national_series
        if f.key.fin_year < "2018"
    ), "national pre-2018 is MoSPI-only — must never be labelled cross-publisher"
