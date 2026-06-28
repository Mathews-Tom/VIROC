"""The ``showcase`` grammar's template layout (design §4, pipeline phase P6).

Layout places the abstract objects expansion produced into resolved boxes. It is
*template-driven, not a general solver* (ADR-0003). A box node becomes a uniform
primary box carrying its content: the title is centred inside the box near the
top, body lines are stacked inside beneath the title, and an optional detail
sub-caption sits in the reserved slot just below the box. A text-primary node
(``heading`` / ``statement``) carries no box; a scene made entirely of them is
laid out as a centred vertical stack of standalone typography (a title card or a
run of claims).

Box nodes are placed with one of three connectivity-selected templates — grid,
fan-out, or comparison — exactly as before; only the *content* each cell carries
is new. The composition is centred inside the safe frame and is overlap-free and
in-frame by geometry, not search. Text measurement lives here, in the Resolver
(design §10, ADR-0002): :func:`measure_text` is a fixed-advance, font-independent
metric, so layout can size cells to their content while ``emit()`` stays
environment-invariant. All arithmetic is integer-valued, so output is byte-stable
across runs and machines (the golden-digest guarantee).
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from viroc.core import BuildContext
from viroc.grammars import AbstractObject
from viroc.grammars.showcase import (
    DETAIL_STYLE_REF,
    HEADING_STYLE_REF,
    TITLE_STYLE_REF,
)
from viroc.ir import Box, ResolvedObject

CHAR_W = 14
"""Per-character advance for the fixed-advance text metric (logical units)."""
LINE_H = 36
"""Single-line title height (logical units)."""
PAD_X = 28
"""Horizontal padding inside a cell, each side, around its content."""
CARD_H = 168
"""Uniform height of every primary composition box (logical units)."""
CARD_MIN_W = 240
"""Floor on the uniform cell width so short titles still read as cards."""
TITLE_GAP = 12
"""Vertical gap between a primary box's bottom and its detail sub-caption."""
COL_GAP = 88
"""Horizontal gap between columns; holds a connector in flow templates."""
ROW_GAP = 64
"""Vertical gap between rows of cells."""
ARROW_T = 8
"""Thickness of a connector's band in the inter-column gap."""
MARGIN_PCT = 7
"""Safe-frame inset as a percent of each axis; wider than the validator's floor."""
INNER_PAD_TOP = 22
"""Vertical inset of the title from the top of its box."""
BODY_LINE_H = 32
"""Height of one body line stacked inside a box."""
BODY_GAP = 10
"""Vertical gap between the title and the first body line."""
HEADING_H = 132
"""Box height of a ``heading`` text node in a statement stack."""
STATEMENT_H = 104
"""Box height of a ``statement`` text node in a statement stack."""
STATEMENT_GAP = 56
"""Vertical gap between stacked text nodes."""
STATEMENT_W_PCT = 82
"""Width of a stacked text node as a percent of the safe-frame width."""

_GROUP_H = CARD_H + TITLE_GAP + LINE_H
"""Full cell height: primary box, gap, then the single-line detail beneath it."""
_COMPARE_STYLE = "edge.compare"
"""Connector style ref that selects the comparison template."""

# A placement pairs a primary object id with its resolved box; a connector adds
# the style ref to draw, since some connectors (comparison) are synthesized
# rather than carried by an expanded arrow.
_Placement = tuple[str, Box]
_Connector = tuple[str, str, Box]


def measure_text(text: str) -> tuple[int, int]:
    """Return the ``(width, height)`` of ``text`` in logical units.

    A fixed-advance metric (``CHAR_W`` per character, ``LINE_H`` tall) that is
    font- and environment-independent so layout stays deterministic and the
    determinism boundary (measurement in the Resolver, not the adapter) holds.
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
    then the content it owns, followed by any drawn connectors — laid out
    overlap-free and within the safe frame. A scene whose nodes are all text
    primaries is laid out as a centred vertical stack; otherwise the box nodes are
    placed with the grid / fan-out / comparison template their connectivity
    selects and each carries its title, body, and detail.

    ``ctx`` is part of the grammar contract (it threads config and, for grammars
    that need it, the measurement environment); the showcase templates read no
    settings from it and centre against a fixed safe margin.
    """
    _ = ctx
    nodes = [obj for obj in objects if obj.role == "node"]
    if not nodes:
        return []
    frame = safe_frame(resolution)

    if all(node.primitive == "text" for node in nodes):
        return _statement_stack(nodes, frame)

    nodes_by_id = {node.id: node for node in nodes}
    owned_by_owner: dict[str, list[AbstractObject]] = {}
    for obj in objects:
        if obj.role == "label" and obj.owner is not None:
            owned_by_owner.setdefault(obj.owner, []).append(obj)
    arrows = [obj for obj in objects if obj.role == "arrow"]

    cell_w = _cell_width(nodes, owned_by_owner)
    placements, connectors = _place(nodes, arrows, cell_w, frame)
    return _resolve(placements, connectors, nodes_by_id, owned_by_owner, cell_w)


def _cell_width(
    nodes: list[AbstractObject], owned_by_owner: dict[str, list[AbstractObject]]
) -> int:
    """Size a uniform cell to fit the widest content line, floored at ``CARD_MIN_W``."""
    widths = [CARD_MIN_W]
    for node in nodes:
        for obj in owned_by_owner.get(node.id, []):
            if obj.text:
                widths.append(measure_text(obj.text)[0] + 2 * PAD_X)
    return max(widths)


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


def _statement_stack(
    nodes: list[AbstractObject], frame: Box
) -> list[ResolvedObject]:
    """Place text-primary nodes as a centred vertical stack of standalone text."""
    heights = [_text_node_height(node) for node in nodes]
    total_h = sum(heights) + STATEMENT_GAP * (len(nodes) - 1)
    width = frame.w * STATEMENT_W_PCT // 100
    start_x = frame.x + (frame.w - width) // 2
    cursor_y = frame.y + (frame.h - total_h) // 2

    resolved: list[ResolvedObject] = []
    for node, height in zip(nodes, heights, strict=True):
        resolved.append(
            ResolvedObject(
                id=node.id,
                primitive="text",
                box=Box(x=start_x, y=cursor_y, w=width, h=height),
                z=node.z,
                style_ref=node.style_ref,
                text=node.text,
            )
        )
        cursor_y += height + STATEMENT_GAP
    return resolved


def _text_node_height(node: AbstractObject) -> int:
    """Box height for a stacked text node, by its heading/statement tier."""
    return HEADING_H if node.style_ref == HEADING_STYLE_REF else STATEMENT_H


def _resolve(
    placements: list[_Placement],
    connectors: list[_Connector],
    nodes_by_id: dict[str, AbstractObject],
    owned_by_owner: dict[str, list[AbstractObject]],
    cell_w: int,
) -> list[ResolvedObject]:
    """Build resolved primaries with their inner content, then connectors."""
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
                text=node.text,
            )
        )
        resolved.extend(_content(box, cell_w, owned_by_owner.get(primary_id, [])))
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


def _content(
    box: Box, cell_w: int, owned: list[AbstractObject]
) -> list[ResolvedObject]:
    """Place a box's title (inside top), body lines (inside), and detail (below)."""
    title = next((obj for obj in owned if obj.style_ref == TITLE_STYLE_REF), None)
    detail = next((obj for obj in owned if obj.style_ref == DETAIL_STYLE_REF), None)
    bodies = [
        obj
        for obj in owned
        if obj.style_ref not in (TITLE_STYLE_REF, DETAIL_STYLE_REF)
    ]

    resolved: list[ResolvedObject] = []
    if title is not None and title.text:
        width = measure_text(title.text)[0]
        resolved.append(
            ResolvedObject(
                id=title.id,
                primitive="text",
                box=Box(
                    x=box.x + (cell_w - width) // 2,
                    y=box.y + INNER_PAD_TOP,
                    w=width,
                    h=LINE_H,
                ),
                z=title.z,
                style_ref=title.style_ref,
                text=title.text,
            )
        )

    body_y = box.y + INNER_PAD_TOP + LINE_H + BODY_GAP
    for index, body in enumerate(bodies):
        if not body.text:
            continue
        width = measure_text(body.text)[0]
        left_aligned = body.style_ref.startswith(("code_card.", "evidence."))
        x = box.x + PAD_X if left_aligned else box.x + (cell_w - width) // 2
        resolved.append(
            ResolvedObject(
                id=body.id,
                primitive="text",
                box=Box(x=x, y=body_y + index * BODY_LINE_H, w=width, h=BODY_LINE_H),
                z=body.z,
                style_ref=body.style_ref,
                text=body.text,
            )
        )

    if detail is not None and detail.text:
        width = measure_text(detail.text)[0]
        resolved.append(
            ResolvedObject(
                id=detail.id,
                primitive="text",
                box=Box(
                    x=box.x + (cell_w - width) // 2,
                    y=box.y + CARD_H + TITLE_GAP,
                    w=width,
                    h=LINE_H,
                ),
                z=detail.z,
                style_ref=detail.style_ref,
                text=detail.text,
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
