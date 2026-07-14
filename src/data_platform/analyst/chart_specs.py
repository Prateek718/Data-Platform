"""The four charts, built from report.json — the artifact the verifier already blessed.

This module is the only place that decides *what* is plotted. It reads verified series figures and
cohort counts out of the report, never from the dataset directly: a chart cannot show a number the
report did not verify, because it has no way to obtain one.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from data_platform.analyst import charts
from data_platform.analyst.charts import Annotation, Chart, Point

# MGNREGA was repealed effective 30 June 2026, so FY 2026-27 holds April 2026 alone. It is a real
# fact and it is reported in the prose and the figure tables — but it is NOT a yearly datapoint, and
# plotting one month beside twenty full years would draw a collapse that never happened. It is
# excluded from every chart and stated as a note beneath each one instead.
INCOMPLETE_YEAR: Final = "2026-27"
_STUB_NOTE: Final = (
    "FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds "
    "April 2026 alone and a single month cannot be plotted against full years. Its figures are "
    "reported in the text and the tables."
)


def build_charts(report: dict[str, object]) -> list[Chart]:
    """Every chart the report can draw from the figures it verified."""
    built: list[Chart] = []
    for section in _sections(report):
        key = str(section.get("key"))
        if key == "national_series":
            built.extend(_national_charts(section))
        elif key == "coverage":
            built.extend(_coverage_charts(section))
        elif key == "districts":
            built.extend(_district_charts(section))
    return built


def _national_charts(section: dict[str, Any]) -> list[Chart]:
    persondays = _series_points(section, "persondays_generated")
    expenditure = _series_points(section, "total_expenditure")
    out: list[Chart] = []

    if persondays:
        out.append(
            charts.line_chart(
                id="national-persondays",
                title="Person-days of employment generated, all-India, FY 2006-07 to 2025-26",
                caption=(
                    "Every point is a verified fact in the canonical series; a year the record "
                    "withholds is drawn as no point, never as zero, and the line breaks there. "
                    + _STUB_NOTE
                ),
                section_key="national_series",
                points=persondays,
                y_label="billion person-days",
                y_scale=Decimal(1_000_000_000),
                boundary_after="2017-18",
                annotations=(
                    Annotation("2017-18", "the seam year"),
                    Annotation("2020-21", "COVID-year peak"),
                ),
            )
        )
    if expenditure:
        out.append(
            charts.line_chart(
                id="national-expenditure",
                title="Total expenditure, all-India, FY 2008-09 to 2025-26",
                caption=(
                    "Expenditure in lakh crore rupees, reconciled across publishers. The pre-2018 "
                    "points come from archived MoSPI and Rajya Sabha sources; from FY 2018-19 the "
                    "flagship district MIS is the production authority. " + _STUB_NOTE
                ),
                section_key="national_series",
                points=expenditure,
                y_label="Rs lakh crore",
                y_scale=Decimal(10_000_000),  # INR lakh -> INR lakh crore
                boundary_after="2017-18",
                annotations=(Annotation("2020-21", "COVID-year peak"),),
            )
        )
    return out


def _coverage_charts(section: dict[str, Any]) -> list[Chart]:
    points = _cohort_points(section, prefix="nulls_by_year_")
    if not points:
        return []
    return [
        charts.bar_chart(
            id="nulls-by-year",
            title="Null cells in the state series, by financial year",
            caption=(
                "A null cell is data carrying a reason, never a zero. Almost all of them fall in "
                "FY 2017-18 — the seam between the two sourcing eras, the year before the flagship "
                "MIS begins. The record's weakest year is exactly where its two eras meet. "
                + _STUB_NOTE
            ),
            section_key="coverage",
            points=points,
            y_label="null cells",
            annotations=(Annotation("2017-18", "the seam"),),
        )
    ]


def _district_charts(section: dict[str, Any]) -> list[Chart]:
    points = _cohort_points(section, prefix="districts_by_year_")
    if not points:
        return []
    return [
        charts.bar_chart(
            id="districts-by-year",
            title="Districts reporting person-days, by financial year",
            caption=(
                "Districts split over the life of the scheme. Each fact stays filed under the "
                "geography that existed at its own period and is never forward-mapped across a "
                "split, so the rise is districts dividing, not territory being added. " + _STUB_NOTE
            ),
            section_key="districts",
            points=points,
            y_label="districts reporting",
        )
    ]


def _sections(report: dict[str, object]) -> list[dict[str, Any]]:
    sections = report.get("sections")
    return [s for s in sections if isinstance(s, dict)] if isinstance(sections, list) else []


def _series_points(section: dict[str, Any], metric: str) -> list[Point]:
    """Plot points from the section's verified chart series, in financial-year order."""
    series = section.get("series")
    if not isinstance(series, list):
        return []
    points = [
        Point(period=str(f["period"]), value=Decimal(str(f["value"])), source_id=str(f["id"]))
        for f in series
        if isinstance(f, dict) and f.get("metric") == metric and f.get("period") != INCOMPLETE_YEAR
    ]
    return sorted(points, key=lambda p: p.period)


def _cohort_points(section: dict[str, Any], *, prefix: str) -> list[Point]:
    """Plot points from per-year cohort counts (a count per financial year)."""
    cohorts = section.get("series_cohorts")
    if not isinstance(cohorts, list):
        return []
    points: list[Point] = []
    for c in cohorts:
        if not isinstance(c, dict) or not str(c.get("id", "")).startswith(prefix):
            continue
        query = c.get("query")
        period = query.get("fy_from") if isinstance(query, dict) else None
        if period is None or period == INCOMPLETE_YEAR:
            continue
        points.append(
            Point(period=str(period), value=Decimal(str(c["value"])), source_id=str(c["id"]))
        )
    return sorted(points, key=lambda p: p.period)
