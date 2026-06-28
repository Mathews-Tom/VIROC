"""Post-resolve layout validation over Concrete IR (pipeline phase P9)."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from viroc.core import BuildContext, Diagnostic, DiagnosticClass, code
from viroc.ir import Box, ConcreteIR, ResolvedObject

VIR_OBJECT_OVERLAP = code(DiagnosticClass.LAYOUT, 1)
"""Two resolved objects share positive area."""

VIR_OBJECT_CLIPPING = code(DiagnosticClass.LAYOUT, 2)
"""A resolved object cannot fit its frame or minimum text bounds."""

VIR_UNSAFE_MARGIN = code(DiagnosticClass.LAYOUT, 3)
"""A resolved object lies outside the configured safe frame."""

_TEXT_PRIMITIVES = frozenset({"text", "code", "formula"})


def validate_layout(ir: ConcreteIR, ctx: BuildContext) -> list[Diagnostic]:
    """Return all Concrete IR layout diagnostics.

    These checks assert only necessary renderer-neutral conditions: boxes must not
    overlap, boxes must be drawable inside the physical frame, text-like objects
    must not be smaller than configured minimums, and every object must remain
    inside the configured safe margin.
    """
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_overlap_diagnostics(ir.objects))
    diagnostics.extend(_clipping_diagnostics(ir.objects, ir.resolution, ctx))
    diagnostics.extend(_margin_diagnostics(ir.objects, ir.resolution, ctx))
    return diagnostics


def _overlap_diagnostics(objects: list[ResolvedObject]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    by_scene: dict[str, list[ResolvedObject]] = defaultdict(list)
    for obj in objects:
        by_scene[_scene_id(obj.id)].append(obj)
    for scene_objects in by_scene.values():
        for first, second in combinations(scene_objects, 2):
            if not _overlaps(first.box, second.box):
                continue
            if _is_nested_content(first, second):
                continue
            diagnostics.append(
                Diagnostic(
                    code=VIR_OBJECT_OVERLAP,
                    message=f"objects {first.id!r} and {second.id!r} overlap",
                    help="Adjust the grammar layout so resolved boxes share no positive area.",
                )
            )
    return diagnostics


def _is_nested_content(a: ResolvedObject, b: ResolvedObject) -> bool:
    """Whether one object is a ``text`` object fully contained by the other box.

    Content (titles, body lines) sits *inside* its node box by design, so a text
    object wholly within a container box is legitimate nesting, not an overlap
    defect. Box-on-box overlap, and text that only partially overlaps a box it
    does not belong to, are still reported.
    """
    a_text = a.primitive == "text"
    b_text = b.primitive == "text"
    if a_text == b_text:
        return False
    text, container = (a, b) if a_text else (b, a)
    return _contains(container.box, text.box)


def _clipping_diagnostics(
    objects: list[ResolvedObject], resolution: tuple[int, int], ctx: BuildContext
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    frame = Box(x=0.0, y=0.0, w=float(resolution[0]), h=float(resolution[1]))
    for obj in objects:
        if obj.box.w <= 0 or obj.box.h <= 0:
            diagnostics.append(
                Diagnostic(
                    code=VIR_OBJECT_CLIPPING,
                    message=f"object {obj.id!r} has non-positive box {obj.box!r}",
                    help="Resolve every object to a positive-width, positive-height box.",
                )
            )
            continue
        if not _contains(frame, obj.box):
            diagnostics.append(
                Diagnostic(
                    code=VIR_OBJECT_CLIPPING,
                    message=(
                        f"object {obj.id!r} is clipped by the "
                        f"{resolution[0]}x{resolution[1]} frame"
                    ),
                    help="Keep resolved boxes within the physical output frame.",
                )
            )
            continue
        if obj.primitive in _TEXT_PRIMITIVES and (
            obj.box.w < ctx.validation.min_text_box_width
            or obj.box.h < ctx.validation.min_text_box_height
        ):
            diagnostics.append(
                Diagnostic(
                    code=VIR_OBJECT_CLIPPING,
                    message=f"text object {obj.id!r} is smaller than configured minimums",
                    help="Increase the text box or lower BuildContext.validation text thresholds.",
                )
            )
    return diagnostics


def _margin_diagnostics(
    objects: list[ResolvedObject], resolution: tuple[int, int], ctx: BuildContext
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    safe_frame = _safe_frame(resolution, ctx.validation.safe_margin_pct)
    for obj in objects:
        if not _contains(safe_frame, obj.box):
            diagnostics.append(
                Diagnostic(
                    code=VIR_UNSAFE_MARGIN,
                    message=f"object {obj.id!r} lies outside the safe frame",
                    help="Keep layout within BuildContext.validation.safe_margin_pct.",
                )
            )
    return diagnostics


def _overlaps(a: Box, b: Box) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def _contains(outer: Box, inner: Box) -> bool:
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and inner.x + inner.w <= outer.x + outer.w
        and inner.y + inner.h <= outer.y + outer.h
    )


def _safe_frame(resolution: tuple[int, int], margin_pct: float) -> Box:
    width, height = resolution
    mx = width * margin_pct / 100.0
    my = height * margin_pct / 100.0
    return Box(x=mx, y=my, w=width - 2 * mx, h=height - 2 * my)


def _scene_id(object_id: str) -> str:
    return object_id.split(".", 1)[0]
