"""Charts — drawn by code, from verified figures only. No LLM anywhere in this module.

A chart is a claim, so it is held to the report's rule: it may plot ONLY values that already passed
verification. Every chart reads its points out of ``report.json`` — the artifact the verifier
already blessed — and its manifest entry names the exact figure (or cohort) ids it plotted, so a
reader can check every plotted point against the figure tables and, from there, against lineage.

Output is a standalone SVG per chart: no JavaScript, no external fonts, no network. Each carries
its own light/dark styling via ``prefers-color-scheme``, so it reads correctly in either theme.

Design follows the project's single-series convention: one blue series (categorical slot 1, the
validated palette), recessive axes and gridlines, selective direct labels on the points that carry
the argument (the peak, the boundary, the stub) rather than a number on every point.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# Categorical slot 1 (blue) from the validated palette, in both modes; text and grid are ink, never
# the series colour.
_SERIES_LIGHT: Final = "#2a78d6"
_SERIES_DARK: Final = "#3987e5"

_WIDTH: Final = 880
_HEIGHT: Final = 380
_MARGIN_LEFT: Final = 78
_MARGIN_RIGHT: Final = 24
_MARGIN_TOP: Final = 28
_MARGIN_BOTTOM: Final = 56

_STYLE: Final = f"""
  .surface {{ fill: #fcfcfb; }}
  .grid {{ stroke: #e6e5e1; stroke-width: 1; }}
  .axis {{ stroke: #b5b3ad; stroke-width: 1; }}
  .tick {{ fill: #52514e; font-size: 11px; }}
  .label {{ fill: #0b0b0b; font-size: 12px; }}
  .muted {{ fill: #6f6e6a; font-size: 11px; }}
  .series {{ stroke: {_SERIES_LIGHT}; fill: none; stroke-width: 2; }}
  .point {{ fill: {_SERIES_LIGHT}; }}
  .bar {{ fill: {_SERIES_LIGHT}; }}
  .marker {{ stroke: #b5b3ad; stroke-width: 1; stroke-dasharray: 4 3; }}
  @media (prefers-color-scheme: dark) {{
    .surface {{ fill: #1a1a19; }}
    .grid {{ stroke: #35342f; }}
    .axis {{ stroke: #56554f; }}
    .tick {{ fill: #c3c2b7; }}
    .label {{ fill: #ffffff; }}
    .muted {{ fill: #9c9b93; }}
    .series {{ stroke: {_SERIES_DARK}; }}
    .point {{ fill: {_SERIES_DARK}; }}
    .bar {{ fill: {_SERIES_DARK}; }}
    .marker {{ stroke: #56554f; }}
  }}
"""


@dataclass(frozen=True)
class Point:
    """One plotted value and the verified id it came from."""

    period: str
    value: Decimal
    source_id: str  # the figure id or cohort id in report.json


@dataclass(frozen=True)
class Annotation:
    """A direct label on the one or two points that carry the argument."""

    period: str
    text: str


@dataclass(frozen=True)
class Chart:
    """A rendered chart plus the manifest entry that says exactly what it plots."""

    id: str
    filename: str
    title: str
    caption: str
    section_key: str
    svg: str
    source_ids: tuple[str, ...]

    def manifest_entry(self) -> dict[str, object]:
        return {
            "id": self.id,
            "file": f"charts/{self.filename}",
            "title": self.title,
            "caption": self.caption,
            "section": self.section_key,
            "plots": list(self.source_ids),
        }


def line_chart(
    *,
    id: str,
    title: str,
    caption: str,
    section_key: str,
    points: list[Point],
    y_label: str,
    y_scale: Decimal = Decimal(1),
    annotations: tuple[Annotation, ...] = (),
    boundary_after: str | None = None,
) -> Chart:
    """A line over financial years. ``y_scale`` divides the axis into readable units.

    The x axis is the REAL span of years, not the list of points: a year the record withholds gets
    its own slot on the axis and no marker, and the line BREAKS there. Spacing the points evenly
    would draw a straight line across a three-year hole and silently assert a continuity the record
    does not have — the visual equivalent of coercing a null to a value.
    """
    by_period = {p.period: p.value / y_scale for p in points}
    scaled = [(period, by_period.get(period)) for period in _span(list(by_period))]
    svg = _render(
        title=title,
        y_label=y_label,
        rows=scaled,
        annotations=annotations,
        boundary_after=boundary_after,
        as_bars=False,
    )
    return Chart(
        id=id,
        filename=f"{id}.svg",
        title=title,
        caption=caption,
        section_key=section_key,
        svg=svg,
        source_ids=tuple(p.source_id for p in points),
    )


def bar_chart(
    *,
    id: str,
    title: str,
    caption: str,
    section_key: str,
    points: list[Point],
    y_label: str,
    annotations: tuple[Annotation, ...] = (),
) -> Chart:
    """Bars over financial years — for counts (null cells, districts reporting)."""
    by_period = {p.period: p.value for p in points}
    rows = [(period, by_period.get(period)) for period in _span(list(by_period))]
    svg = _render(
        title=title,
        y_label=y_label,
        rows=rows,
        annotations=annotations,
        boundary_after=None,
        as_bars=True,
    )
    return Chart(
        id=id,
        filename=f"{id}.svg",
        title=title,
        caption=caption,
        section_key=section_key,
        svg=svg,
        source_ids=tuple(p.source_id for p in points),
    )


def _span(periods: list[str]) -> list[str]:
    """Every financial year from the earliest point to the latest — gaps included."""
    if not periods:
        raise ValueError("a chart needs at least one point")
    years = sorted(int(p[:4]) for p in periods)
    return [f"{y}-{str(y + 1)[2:]}" for y in range(years[0], years[-1] + 1)]


def _render(
    *,
    title: str,
    y_label: str,
    rows: list[tuple[str, Decimal | None]],
    annotations: tuple[Annotation, ...],
    boundary_after: str | None,
    as_bars: bool,
) -> str:
    present = [value for _, value in rows if value is not None]
    if not present:
        raise ValueError("a chart needs at least one point")

    plot_w = _WIDTH - _MARGIN_LEFT - _MARGIN_RIGHT
    plot_h = _HEIGHT - _MARGIN_TOP - _MARGIN_BOTTOM
    top = _axis_top(max(present))
    step = plot_w / len(rows)

    def x_of(index: int) -> float:
        return _MARGIN_LEFT + step * (index + 0.5)

    def y_of(value: Decimal) -> float:
        return _MARGIN_TOP + plot_h * (1 - float(value) / float(top))

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        f'width="{_WIDTH}" height="{_HEIGHT}" role="img" aria-label="{_esc(title)}" '
        'font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
        f"<style>{_STYLE}</style>",
        f'<rect class="surface" width="{_WIDTH}" height="{_HEIGHT}"/>',
        f'<text class="label" x="{_MARGIN_LEFT}" y="18">{_esc(title)}</text>',
    ]

    # Horizontal gridlines + y ticks.
    for fraction in (0, 0.25, 0.5, 0.75, 1.0):
        tick_value = top * Decimal(str(fraction))
        y = y_of(tick_value)
        parts.append(
            f'<line class="grid" x1="{_MARGIN_LEFT}" y1="{y:.1f}" '
            f'x2="{_WIDTH - _MARGIN_RIGHT}" y2="{y:.1f}"/>'
        )
        parts.append(
            f'<text class="tick" x="{_MARGIN_LEFT - 8}" y="{y + 4:.1f}" '
            f'text-anchor="end">{_tick(tick_value)}</text>'
        )
    parts.append(f'<text class="muted" x="{_MARGIN_LEFT}" y="{_HEIGHT - 8}">{_esc(y_label)}</text>')

    # X axis + labels (every other year, so they never collide).
    axis_y = _MARGIN_TOP + plot_h
    parts.append(
        f'<line class="axis" x1="{_MARGIN_LEFT}" y1="{axis_y}" '
        f'x2="{_WIDTH - _MARGIN_RIGHT}" y2="{axis_y}"/>'
    )
    # Label every other year, and always the last one — dropping its neighbour rather than letting
    # the two collide.
    labelled = set(range(0, len(rows), 2))
    if len(rows) - 1 not in labelled:
        labelled.discard(len(rows) - 2)
        labelled.add(len(rows) - 1)
    for index, (period, _) in enumerate(rows):
        if index in labelled:
            parts.append(
                f'<text class="tick" x="{x_of(index):.1f}" y="{axis_y + 18}" '
                f'text-anchor="middle">{_esc(period)}</text>'
            )

    if boundary_after is not None:
        for index, (period, _) in enumerate(rows):
            if period == boundary_after and index + 1 < len(rows):
                x = (x_of(index) + x_of(index + 1)) / 2
                parts.append(
                    f'<line class="marker" x1="{x:.1f}" y1="{_MARGIN_TOP}" '
                    f'x2="{x:.1f}" y2="{axis_y}"/>'
                )
                parts.append(
                    f'<text class="muted" x="{x + 6:.1f}" y="{_MARGIN_TOP + 12}">'
                    "flagship MIS era begins</text>"
                )

    if as_bars:
        width = step * 0.62
        for index, (_, value) in enumerate(rows):
            if value is None:
                continue
            y = y_of(value)
            parts.append(
                f'<rect class="bar" x="{x_of(index) - width / 2:.1f}" y="{y:.1f}" '
                f'width="{width:.1f}" height="{axis_y - y:.1f}" rx="2"/>'
            )
    else:
        # The path BREAKS at a withheld year: a new "M" starts the next run of data, so a gap is
        # drawn as a gap. Nothing is interpolated across a year the record does not have.
        commands: list[str] = []
        pen_down = False
        for index, (_, value) in enumerate(rows):
            if value is None:
                pen_down = False
                continue
            commands.append(f"{'L' if pen_down else 'M'}{x_of(index):.1f},{y_of(value):.1f}")
            pen_down = True
        parts.append(f'<path class="series" d="{" ".join(commands)}"/>')
        for index, (_, value) in enumerate(rows):
            if value is None:
                continue
            parts.append(
                f'<circle class="point" cx="{x_of(index):.1f}" cy="{y_of(value):.1f}" r="3"/>'
            )

    # Name the hole, so a reader sees an absence rather than wondering about a kink in the line.
    withheld = [period for period, value in rows if value is None]
    if withheld and not as_bars:
        parts.append(
            f'<text class="muted" x="{_WIDTH - _MARGIN_RIGHT}" y="{_HEIGHT - 8}" '
            'text-anchor="end">no line where the record withholds a year: '
            f"{', '.join(withheld)}</text>"
        )

    index_of = {period: i for i, (period, _) in enumerate(rows)}
    for note in annotations:
        if note.period not in index_of:
            continue
        index = index_of[note.period]
        _, value = rows[index]
        if value is None:
            continue
        x, y = x_of(index), y_of(value)
        anchor = "end" if index > len(rows) * 0.7 else "start"
        dx = -8 if anchor == "end" else 8
        parts.append(
            f'<text class="muted" x="{x + dx:.1f}" y="{y - 10:.1f}" '
            f'text-anchor="{anchor}">{_esc(note.text)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _axis_top(largest: Decimal) -> Decimal:
    """A round ceiling above the biggest point, so the y ticks read as human numbers."""
    if largest <= 0:
        return Decimal(1)
    magnitude = Decimal(10) ** (largest.adjusted() - 1)
    for step in (Decimal(1), Decimal(2), Decimal(2.5), Decimal(5), Decimal(10), Decimal(20)):
        top = magnitude * step * 10
        if top >= largest:
            return top
    return largest


def _tick(value: Decimal) -> str:
    if value == value.to_integral_value():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
