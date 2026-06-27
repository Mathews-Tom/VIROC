"""The ``showcase`` grammar's template layout (design §4, pipeline phase P6).

Layout places the abstract objects expansion produced into resolved boxes. Like
``pipeline`` it is *template-driven, not a general solver* (ADR-0003), but where
``pipeline`` lays out a single left-to-right row, ``showcase`` selects one of
three deterministic *non-row* templates from the scene's connectivity:

- **comparison** — a ``compare`` edge is present: two columns placed side by side,
  paired row by row, with a horizontal connector per row in the central gap;
- **fan-out** — one node sources two or more edges: that hub sits left, its
  targets stack in a right column, and each connector is a horizontal stub at its
  target's row in the column gap;
- **grid** — otherwise: a row-major lattice of ``ceil(sqrt(n))`` columns, the
  default "set of panels" arrangement.

Every template is overlap-free and in-frame *by geometry*, not by search: cells
are pitched a positive gap apart on an integer lattice, a uniform cell width
sized to the widest title keeps each title within its own column, and connectors
live strictly in the inter-column gap at a primary's vertical centre, so they
never enter a cell or share a row with another connector. All arithmetic is
integer, so output is byte-stable across runs and machines (the golden-digest
guarantee).

Text measurement lives here, in the Resolver, never in an adapter's ``emit()``
(design §10, ADR-0002): :func:`measure_text` is a fixed-advance, font-independent
metric so layout can size cells to their titles while ``emit()`` stays
environment-invariant.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from viroc.core import BuildContext
from viroc.grammars import AbstractObject
from viroc.ir import Box, ResolvedObject

CHAR_W = 14
"""Per-character advance for the fixed-advance text metric (logical units)."""
LINE_H = 36
"""Single-line title height (logical units)."""
PAD_X = 28
"""Horizontal padding inside a cell, each side, around its title."""
CARD_H = 168
"""Uniform height of every primary composition box (logical units)."""
CARD_MIN_W = 240
"""Floor on the uniform cell width so short titles still read as cards."""
TITLE_GAP = 12
"""Vertical gap between a primary box's bottom and its title."""
COL_GAP = 88
"""Horizontal gap between columns; holds a connector in flow templates."""
ROW_GAP = 64
"""Vertical gap between rows of cells."""
ARROW_T = 8
"""Thickness of a connector's band in the inter-column gap."""
MARGIN_PCT = 7
"""Safe-frame inset as a percent of each axis; wider than the validator's floor."""

_GROUP_H = CARD_H + TITLE_GAP + LINE_H
"""Full cell height: primary box, gap, then the single-line title beneath it."""
_COMPARE_STYLE = "edge.compare"
"""Connector style ref that selects the comparison template."""

# A placement pairs a primary object id with its resolved box; a connector adds
# the style ref to draw, since some connectors (comparison) are synthesized
# rather than carried by an expanded arrow.
_Placement = tuple[str, Box]
_Connector = tuple[str, str, Box]


def measure_text(text: str) -> tuple[int, int]:
    """Return the ``(width, height)`` of ``text`` in logical units.

    A deterministic fixed-advance metric: width is the character count times a
    fixed advance, height a single line. Measurement is font-independent by
    construction, so it is byte-stable and stays in the Resolver rather than
    leaking environment state into an adapter's ``emit()`` (design §10).
    """
    return (max(len(text), 1) * CHAR_W, LINE_H)


def safe_frame(resolution: tuple[int, int], margin_pct: int = MARGIN_PCT) -> Box:
    """Return the safe frame: ``resolution`` inset by ``margin_pct`` on each axis."""
    width, height = resolution
    mx = width * margin_pct // 100
    my = height * margin_pct // 100
    return Box(x=mx, y=my, w=width - 2 * mx, h=height - 2 * my)


def layout(
    objects: list[AbstractObject],
    resolution: tuple[int, int],
    ctx: BuildContext,
) -> list[ResolvedObject]:
    """Place ``objects`` with the showcase template selected from connectivity.

    Returns the resolved objects in deterministic reading order — each primary
    then its title in placement order, followed by any drawn connectors — laid
    out overlap-free and within the safe frame. ``resolution`` is the target
    frame size; the composition is centred on it.

    ``ctx`` is part of the grammar contract (it threads config and, for grammars
    that need it, the measurement environment); the showcase templates read no
    settings from it and centre against a fixed safe margin.
    """
    _ = ctx
    nodes = [obj for obj in objects if obj.role == "node"]
    if not nodes:
        return []
    nodes_by_id = {node.id: node for node in nodes}
    labels_by_owner = {obj.owner: obj for obj in objects if obj.role == "label"}
    arrows = [obj for obj in objects if obj.role == "arrow"]

    cell_w = _cell_width(nodes, labels_by_owner)
    frame = safe_frame(resolution)

    placements, connectors = _place(nodes, arrows, cell_w, frame)
    return _resolve(placements, connectors, nodes_by_id, labels_by_owner, cell_w)


def _cell_width(
    nodes: list[AbstractObject], labels_by_owner: dict[str | None, AbstractObject]
) -> int:
    """Size a uniform cell to fit the widest title, floored at ``CARD_MIN_W``."""
    title_widths = [
        measure_text(label.text)[0]
        for node in nodes
        if (label := labels_by_owner.get(node.id)) is not None and label.text
    ]
    return max([CARD_MIN_W, *(width + 2 * PAD_X for width in title_widths)])


def _place(
    nodes: list[AbstractObject],
    arrows: list[AbstractObject],
    cell_w: int,
    frame: Box,
) -> tuple[list[_Placement], list[_Connector]]:
    """Select a template and return primary placements plus drawn connectors."""
    if any(arrow.style_ref == _COMPARE_STYLE for arrow in arrows):
        return _comparison(nodes, arrows, cell_w, frame)
    hub = _fan_out_hub(nodes, arrows)
    if hub is not None:
        return _fan_out(nodes, arrows, hub, cell_w, frame)
    return _grid(nodes, cell_w, frame)


def _fan_out_hub(
    nodes: list[AbstractObject], arrows: list[AbstractObject]
) -> AbstractObject | None:
    """Return the first node sourcing two or more edges, or ``None``."""
    for node in nodes:
        if sum(1 for arrow in arrows if arrow.source == node.id) >= 2:
            return node
    return None


def _grid(
    nodes: list[AbstractObject], cell_w: int, frame: Box
) -> tuple[list[_Placement], list[_Connector]]:
    """Place every node on a row-major ``ceil(sqrt(n))``-column lattice."""
    count = len(nodes)
    cols = math.isqrt(count - 1) + 1
    rows = -(-count // cols)
    start_x, start_y = _block_origin(_lattice_width(cols, cell_w), rows, frame)
    placements: list[_Placement] = []
    for index, node in enumerate(nodes):
        row, col = divmod(index, cols)
        placements.append((node.id, _cell(start_x, start_y, row, col, cell_w)))
    return placements, []


def _fan_out(
    nodes: list[AbstractObject],
    arrows: list[AbstractObject],
    hub: AbstractObject,
    cell_w: int,
    frame: Box,
) -> tuple[list[_Placement], list[_Connector]]:
    """Hub on the left; targets then any other nodes stacked in a right column."""
    targets = _unique(
        arrow.target
        for arrow in arrows
        if arrow.source == hub.id and arrow.target is not None
    )
    others = [node.id for node in nodes if node.id not in {hub.id, *targets}]
    right_ids = [*targets, *others]
    rows = max(len(right_ids), 1)
    start_x, start_y = _block_origin(_lattice_width(2, cell_w), rows, frame)

    right_boxes = {
        primary_id: _cell(start_x, start_y, index, 1, cell_w)
        for index, primary_id in enumerate(right_ids)
    }
    hub_box = Box(
        x=start_x,
        y=start_y + (rows - 1) * (_GROUP_H + ROW_GAP) // 2,
        w=cell_w,
        h=CARD_H,
    )

    placements: list[_Placement] = [(hub.id, hub_box), *right_boxes.items()]
    connectors = [
        (arrow.id, arrow.style_ref, _connector(start_x + cell_w, right_boxes[arrow.target]))
        for arrow in arrows
        if arrow.source == hub.id and arrow.target in right_boxes
    ]
    return placements, connectors


def _comparison(
    nodes: list[AbstractObject],
    arrows: list[AbstractObject],
    cell_w: int,
    frame: Box,
) -> tuple[list[_Placement], list[_Connector]]:
    """Two columns from the compare edges, paired and connected row by row."""
    compare = [arrow for arrow in arrows if arrow.style_ref == _COMPARE_STYLE]
    left = _unique(arrow.source for arrow in compare if arrow.source is not None)
    right = _unique(arrow.target for arrow in compare if arrow.target is not None)
    placed = {*left, *right}
    for node in nodes:
        if node.id in placed:
            continue
        (left if len(left) <= len(right) else right).append(node.id)
        placed.add(node.id)

    rows = max(len(left), len(right), 1)
    start_x, start_y = _block_origin(_lattice_width(2, cell_w), rows, frame)

    placements: list[_Placement] = []
    for index, primary_id in enumerate(left):
        placements.append((primary_id, _cell(start_x, start_y, index, 0, cell_w)))
    for index, primary_id in enumerate(right):
        placements.append((primary_id, _cell(start_x, start_y, index, 1, cell_w)))

    scene = left[0].split(".", 1)[0]
    connectors = [
        (
            f"{scene}.compare.{index}",
            _COMPARE_STYLE,
            _connector(start_x + cell_w, _cell(start_x, start_y, index, 1, cell_w)),
        )
        for index in range(min(len(left), len(right)))
    ]
    return placements, connectors


def _resolve(
    placements: list[_Placement],
    connectors: list[_Connector],
    nodes_by_id: dict[str, AbstractObject],
    labels_by_owner: dict[str | None, AbstractObject],
    cell_w: int,
) -> list[ResolvedObject]:
    """Build resolved primaries with titles beneath them, then connectors."""
    resolved: list[ResolvedObject] = []
    for primary_id, box in placements:
        node = nodes_by_id[primary_id]
        resolved.append(
            ResolvedObject(
                id=node.id,
                primitive=node.primitive,
                box=box,
                z=node.z,
                style_ref=node.style_ref,
            )
        )
        label = labels_by_owner.get(primary_id)
        if label is not None:
            label_w = measure_text(label.text)[0] if label.text else 0
            resolved.append(
                ResolvedObject(
                    id=label.id,
                    primitive=label.primitive,
                    box=Box(
                        x=box.x + (cell_w - label_w) // 2,
                        y=box.y + CARD_H + TITLE_GAP,
                        w=label_w,
                        h=LINE_H,
                    ),
                    z=label.z,
                    style_ref=label.style_ref,
                )
            )
    for connector_id, style_ref, box in connectors:
        resolved.append(
            ResolvedObject(
                id=connector_id,
                primitive="arrow",
                box=box,
                z=0,
                style_ref=style_ref,
            )
        )
    return resolved


def _unique(items: Iterable[str]) -> list[str]:
    """Return ``items`` de-duplicated, preserving first-seen order."""
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def _lattice_width(cols: int, cell_w: int) -> int:
    """Total width of ``cols`` cells pitched ``COL_GAP`` apart."""
    return cols * cell_w + (cols - 1) * COL_GAP


def _block_origin(block_w: int, rows: int, frame: Box) -> tuple[float, float]:
    """Centre a ``block_w`` x ``rows``-tall lattice within the safe frame."""
    block_h = rows * _GROUP_H + (rows - 1) * ROW_GAP
    return (
        frame.x + (frame.w - block_w) // 2,
        frame.y + (frame.h - block_h) // 2,
    )


def _cell(start_x: float, start_y: float, row: int, col: int, cell_w: int) -> Box:
    """Return the primary box for the cell at ``(row, col)`` of the lattice."""
    return Box(
        x=start_x + col * (cell_w + COL_GAP),
        y=start_y + row * (_GROUP_H + ROW_GAP),
        w=cell_w,
        h=CARD_H,
    )


def _connector(gap_x: float, target_box: Box) -> Box:
    """A thin horizontal connector in the column gap at ``target_box``'s centre."""
    return Box(
        x=gap_x,
        y=target_box.y + CARD_H // 2 - ARROW_T // 2,
        w=COL_GAP,
        h=ARROW_T,
    )
