"""The ``pipeline`` grammar's template layout (design §4, pipeline phase P6).

Layout places the abstract objects expansion produced into resolved boxes. It is
*template-driven, not a general solver* (ADR-0003): the ``pipeline`` template is a
single left-to-right row of uniform node-boxes, each label centered beneath its
box, and each arrow occupying the gap between its endpoint boxes. The row is
centered inside the safe frame.

The template is constructed to be overlap-free and in-frame *by geometry*, not by
search: node columns are pitched a positive ``GAP`` apart; a uniform box width
sized to the widest label keeps every label within its own column and below the
boxes; arrows live strictly in the inter-box gaps, vertically centered on the row
band above the labels. All arithmetic is integer, so output is byte-stable across
runs and machines (the golden-digest guarantee).

Text measurement lives here, in the Resolver, never in an adapter's ``emit()``
(design §10, ADR-0002): :func:`measure_text` is a fixed-advance, font-independent
metric so layout can size boxes to their text while ``emit()`` stays
environment-invariant.

Template assumption (a design §10 finding): the ``pipeline`` template lays nodes
out in a single left-to-right row and assumes edges connect nodes within that
row. The five v1 topics are linear flows that fit; a topology that does not (a
skip edge spanning columns, more nodes than the row width admits) is out of the
template's scope and is the signal to revisit ADR-0003, not to special-case here.
"""

from __future__ import annotations

from viroc.core import BuildContext
from viroc.grammars import AbstractObject
from viroc.ir import Box, ResolvedObject

CHAR_W = 14
"""Per-character advance for the fixed-advance text metric (logical units)."""
LINE_H = 36
"""Single-line text height (logical units)."""
PAD_X = 24
"""Horizontal padding inside a node-box, each side."""
PAD_Y = 16
"""Vertical padding inside a node-box, top and bottom."""
GAP = 120
"""Horizontal gap between node columns; holds the connecting arrow."""
LABEL_GAP = 12
"""Vertical gap between a node-box's bottom and its label."""
ARROW_H = 8
"""Thickness of an arrow's band in the inter-box gap."""
MIN_BOX_W = 160
"""Floor on node-box width so short labels still read as boxes."""
MARGIN_PCT = 5
"""Safe-frame inset as a percent of each axis (overridable via BuildContext)."""


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
    """Place ``objects`` into resolved boxes with the ``pipeline`` row template.

    Returns the resolved objects in a deterministic order — each node-box then
    its label in node order, followed by the arrows — laid out overlap-free and
    within the safe frame. ``resolution`` is the target frame size; the row is
    centered on it.

    ``ctx`` is part of the grammar contract (it threads config and, for grammars
    that need it, the measurement environment); the v1 ``pipeline`` template
    reads no settings from it and centers against a fixed safe margin.
    """
    frame = safe_frame(resolution)

    nodes = [obj for obj in objects if obj.role == "node"]
    labels_by_owner = {obj.owner: obj for obj in objects if obj.role == "label"}
    arrows = [obj for obj in objects if obj.role == "arrow"]

    # Size a uniform node-box to fit the widest label; labels then sit within
    # their own column, guaranteeing no label crosses into a neighbour.
    label_widths: dict[str, int] = {}
    for node in nodes:
        label = labels_by_owner.get(node.id)
        label_widths[node.id] = measure_text(label.text)[0] if label and label.text else 0
    box_w = max([MIN_BOX_W, *(lw + 2 * PAD_X for lw in label_widths.values())])
    box_h = LINE_H + 2 * PAD_Y

    count = len(nodes)
    row_w = count * box_w + (count - 1) * GAP if count else 0
    group_h = box_h + LABEL_GAP + LINE_H
    start_x = frame.x + (frame.w - row_w) // 2
    row_y = frame.y + (frame.h - group_h) // 2

    resolved: list[ResolvedObject] = []
    box_by_id: dict[str, Box] = {}
    for index, node in enumerate(nodes):
        node_x = start_x + index * (box_w + GAP)
        node_box = Box(x=node_x, y=row_y, w=box_w, h=box_h)
        box_by_id[node.id] = node_box
        resolved.append(
            ResolvedObject(
                id=node.id,
                primitive=node.primitive,
                box=node_box,
                z=node.z,
                style_ref=node.style_ref,
            )
        )
        label = labels_by_owner.get(node.id)
        if label is not None:
            label_w = label_widths[node.id]
            label_box = Box(
                x=node_x + (box_w - label_w) // 2,
                y=row_y + box_h + LABEL_GAP,
                w=label_w,
                h=LINE_H,
            )
            resolved.append(
                ResolvedObject(
                    id=label.id,
                    primitive=label.primitive,
                    box=label_box,
                    z=label.z,
                    style_ref=label.style_ref,
                )
            )

    arrow_cy = row_y + box_h // 2
    for arrow in arrows:
        if arrow.source is None or arrow.target is None:
            raise ValueError(f"arrow {arrow.id!r} is missing an endpoint")
        source_box = box_by_id[arrow.source]
        target_box = box_by_id[arrow.target]
        left = source_box.x + source_box.w
        right = target_box.x
        arrow_box = Box(
            x=min(left, right),
            y=arrow_cy - ARROW_H // 2,
            w=abs(right - left),
            h=ARROW_H,
        )
        resolved.append(
            ResolvedObject(
                id=arrow.id,
                primitive=arrow.primitive,
                box=arrow_box,
                z=arrow.z,
                style_ref=arrow.style_ref,
            )
        )

    return resolved
