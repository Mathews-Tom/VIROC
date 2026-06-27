"""Feasibility remediation (doc §3, Option A): standalone SVG export.

`.docs/2026-06-27-no-go-renderer-remediation.md` §3 keeps "native vector" NO-GO as
an *embedded renderer* and reframes it as **SVG export consolidation**: expose a
first-class, dependency-light, byte-deterministic standalone ``.svg`` artifact, with
optional render-side rasterization to PNG/PDF (``rasterize.py``).

This is the distinct artifact I3.1 asks for. It differs from the existing targets:

* the HTML adapter emits an HTML/CSS/JS *page* (needs a browser to lay out and play);
* the interactive-web bundle emits ``timeline.json`` + a JS viewer that *draws* SVG
  at runtime (needs JS).

A standalone SVG is a single self-contained file with no HTML/JS: openable,
embeddable, printable, and headless-rasterizable. It reuses the same Concrete IR
geometry/floor-degradation policy as the interactive-web probe, lowered to SMIL
``<animate>`` / ``<animateTransform>`` instead of a JS runtime, so emit stays a pure
function of the Concrete IR (ADR-0002) and needs no Concrete IR change (I3.3).

Floor (``rect``/``arrow``/``text``) is native; above-floor (``icon``/``code``/
``formula``) degrades to the rect floor with a recorded note, matching the
production ``VIR5033`` policy and the Lottie/interactive-web probes. ``code`` could
be native via ``<foreignObject><pre>`` but that needs an HTML engine (browsers only;
not headless-rasterizable), so it stays off the dependency-light floor.
"""

from __future__ import annotations

from math import hypot

from viroc.core import canonical_json, hash_bytes
from viroc.ir import ConcreteIR, Keyframe, ResolvedObject

SVG_SOURCE_VERSION = "svg-source-v0.1"

# Deterministic enter offset (logical px) used to synthesize a `move` vector, since
# Concrete IR keyframes carry no positional delta (matches the Lottie probe).
_MOVE_ENTER_DX = -40.0

_DEGRADE_TO_RECT = frozenset({"icon", "code", "formula"})
NATIVE_PRIMITIVES = frozenset({"arrow", "rect", "text"})

# ease_in_out cubic-bezier control points; `spring` has no SMIL equivalent and is
# degraded to ease_in_out (recorded as a note, like the Lottie probe).
_EASE_SPLINE = "0.42 0 0.58 1"

_DEFS = (
    '<defs>'
    '<marker id="viroc-arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" '
    'orient="auto" markerUnits="strokeWidth">'
    '<path d="M0,0 L8,3 L0,6 Z" fill="#999999"/>'
    '</marker>'
    '</defs>'
)


def total_frames(ir: ConcreteIR) -> int:
    ends = [kf.end_f for kf in ir.keyframes] + [c.end_f for c in ir.captions]
    return max(ends) if ends else 0


def _fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _seconds(frame: int, fps: int) -> str:
    return _fmt(frame / fps)


def _spline_attrs(easing: str, stops: int) -> str:
    """Return SMIL spline attributes for non-linear easing; linear adds nothing."""
    if easing == "linear":
        return ""
    splines = ";".join([_EASE_SPLINE] * (stops - 1))
    return f' calcMode="spline" keySplines="{splines}"'


def _object_keyframes(ir: ConcreteIR) -> dict[str, list[Keyframe]]:
    by_object: dict[str, list[Keyframe]] = {}
    for kf in ir.keyframes:
        by_object.setdefault(kf.object_id, []).append(kf)
    for kfs in by_object.values():
        kfs.sort(key=lambda k: (k.start_f, k.end_f, k.kind))
    return by_object


def _opacity_animations(kfs: list[Keyframe], fps: int) -> list[str]:
    anims: list[str] = []
    for kf in kfs:
        if kf.kind not in {"fade_in", "fade_out"}:
            continue
        start, end = (0, 1) if kf.kind == "fade_in" else (1, 0)
        anims.append(
            f'<animate attributeName="opacity" from="{start}" to="{end}" '
            f'begin="{_seconds(kf.start_f, fps)}s" dur="{_seconds(kf.end_f - kf.start_f, fps)}s" '
            f'fill="freeze"{_spline_attrs(kf.easing, 2)}/>'
        )
    return anims


def _transform_animations(obj: ResolvedObject, kfs: list[Keyframe], fps: int) -> list[str]:
    anims: list[str] = []
    for kf in kfs:
        dur = f'begin="{_seconds(kf.start_f, fps)}s" dur="{_seconds(kf.end_f - kf.start_f, fps)}s" fill="freeze"'
        if kf.kind == "move":
            anims.append(
                f'<animateTransform attributeName="transform" type="translate" additive="sum" '
                f'values="{_fmt(_MOVE_ENTER_DX)},0;0,0" keyTimes="0;1" {dur}{_spline_attrs(kf.easing, 2)}/>'
            )
        elif kf.kind == "highlight":
            anims.append(
                f'<animateTransform attributeName="transform" type="scale" additive="sum" '
                f'values="1;1.06;1" keyTimes="0;0.5;1" {dur}{_spline_attrs(kf.easing, 3)}/>'
            )
    return anims


def _shape_markup(obj: ResolvedObject, primitive: str, draw_anim: str) -> str:
    box = obj.box
    if primitive == "text":
        cx = box.x + box.w / 2
        cy = box.y + box.h / 2
        return (
            f'<text x="{_fmt(cx)}" y="{_fmt(cy)}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="#E5E7EB" font-family="sans-serif">{obj.id}</text>'
        )
    if primitive == "arrow":
        x2 = box.x + box.w
        y2 = box.y + box.h
        length = hypot(box.w, box.h)
        dash = f' stroke-dasharray="{_fmt(length)}" stroke-dashoffset="{_fmt(length)}"' if draw_anim else ""
        return (
            f'<line x1="{_fmt(box.x)}" y1="{_fmt(box.y)}" x2="{_fmt(x2)}" y2="{_fmt(y2)}" '
            f'stroke="#999999" stroke-width="4" marker-end="url(#viroc-arrowhead)"{dash}>{draw_anim}</line>'
        )
    # rect floor (native rect + degraded icon/code/formula)
    perimeter = 2 * (box.w + box.h)
    dash = f' stroke-dasharray="{_fmt(perimeter)}" stroke-dashoffset="{_fmt(perimeter)}"' if draw_anim else ""
    return (
        f'<rect x="{_fmt(box.x)}" y="{_fmt(box.y)}" width="{_fmt(box.w)}" height="{_fmt(box.h)}" '
        f'fill="#808080" stroke="#999999" stroke-width="2"{dash}>{draw_anim}</rect>'
    )


def lower(ir: ConcreteIR) -> tuple[str, list[str]]:
    """Lower Concrete IR to a (standalone SVG string, degradation notes) pair (pure)."""
    width, height = ir.resolution
    fps = ir.fps
    by_object = _object_keyframes(ir)
    degradations: list[str] = []
    groups: list[str] = []

    for obj in sorted(ir.objects, key=lambda o: (o.z, o.id)):
        kfs = by_object.get(obj.id, [])
        primitive = obj.primitive
        if primitive in _DEGRADE_TO_RECT:
            degradations.append(f'object "{obj.id}": primitive "{primitive}" degraded to the rect floor')
            primitive = "rect"
        for kf in kfs:
            if kf.easing == "spring":
                degradations.append(f'object "{obj.id}": easing "spring" degraded to "ease_in_out"')

        has_draw = any(kf.kind == "draw" for kf in kfs)
        draw_anim = ""
        if has_draw:
            draw_kf = next(kf for kf in kfs if kf.kind == "draw")
            draw_anim = (
                f'<animate attributeName="stroke-dashoffset" to="0" '
                f'begin="{_seconds(draw_kf.start_f, fps)}s" dur="{_seconds(draw_kf.end_f - draw_kf.start_f, fps)}s" '
                f'fill="freeze"{_spline_attrs(draw_kf.easing, 2)}/>'
            )

        shape = _shape_markup(obj, primitive, draw_anim)
        anims = _opacity_animations(kfs, fps) + _transform_animations(obj, kfs, fps)
        groups.append(f'<g id="{obj.id}">{"".join(anims)}{shape}</g>')

    if ir.captions:
        degradations.append(
            f"{len(ir.captions)} caption(s) emitted to an SRT sidecar (SVG has no subtitle track)"
        )

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" version="1.1">'
        f"{_DEFS}{''.join(groups)}</svg>\n"
    )
    return svg, degradations


def export_svg(ir: ConcreteIR) -> str:
    """Serialize the standalone SVG document (byte-deterministic)."""
    svg, _ = lower(ir)
    return svg


def degradations(ir: ConcreteIR) -> list[str]:
    """Return the ordered degradation notes recorded while lowering ``ir``."""
    _, notes = lower(ir)
    return notes


def source_hash(ir: ConcreteIR) -> str:
    """The golden ``source_hash`` of the SVG emit (promotion-checklist artifact)."""
    return hash_bytes(export_svg(ir).encode("utf-8"))


def capability_manifest() -> str:
    """A canonical capability map for the SVG target (promotion-checklist sketch)."""
    return canonical_json(
        {
            "id": "svg",
            "version": SVG_SOURCE_VERSION,
            "native_primitives": sorted(NATIVE_PRIMITIVES),
            "degraded_primitives": {p: "rect" for p in sorted(_DEGRADE_TO_RECT)},
            "native_animations": ["draw", "fade_in", "fade_out", "highlight", "move"],
            "degraded_easings": {"spring": "ease_in_out"},
            "captions": "srt-sidecar",
        }
    )


__all__ = [
    "NATIVE_PRIMITIVES",
    "SVG_SOURCE_VERSION",
    "capability_manifest",
    "degradations",
    "export_svg",
    "lower",
    "source_hash",
    "total_frames",
]
