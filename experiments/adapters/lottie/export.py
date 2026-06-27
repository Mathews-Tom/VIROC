"""Feasibility probe: lower the sample Concrete IR to a Lottie-subset JSON document.

This is a *prototype*, not a production adapter. It exists to answer one question
from `.docs/viroc-draft.md` §4.3 / §5.6: can VIROC export a Concrete IR as a
Lottie animation *as an export format* (not a full timeline renderer) while
preserving the ADR-0002 byte-deterministic emit boundary?

Findings (see `README.md` and `../RESULTS.md` for the full capability map):

* Lottie is an open JSON schema, so the lowering is pure stdlib + the Concrete IR
  and is serialized with :func:`viroc.core.canonical_json` — byte-identical across
  runs, exactly like the production adapters' ``source_hash``.
* The portable floor maps natively: ``rect``/``arrow`` -> shape layers,
  ``text`` -> a Lottie text layer (player-resolved font, no glyph baking so emit
  stays deterministic), ``fade_in``/``fade_out`` -> layer opacity keyframes,
  ``draw`` -> a Trim Paths modifier, ``move`` -> a position keyframe.
* Above-floor primitives and non-floor motions are recorded as explicit
  degradations rather than silently dropped: ``icon``/``code``/``formula`` fall to
  the rect floor (Lottie has no semantic icon/code/LaTeX construct; faithful
  lowering needs a baked raster asset, which would break determinism), ``highlight``
  degrades to a scale pulse (no native highlight property), and ``spring`` easing
  degrades to an ease-in-out bezier (Lottie has no spring interpolator).
* Captions are emitted to an SRT sidecar, exactly as production adapters do —
  Lottie has no subtitle track.

The motion convention for ``move`` is a deliberate finding: Concrete IR keyframes
carry only ``(kind, window, easing)``, not a property delta, so any position
animation uses an adapter-chosen, deterministic enter offset — the motion vector is
adapter policy, not IR data.
"""

from __future__ import annotations

from typing import Any

from viroc.core import canonical_json
from viroc.ir import ConcreteIR, Keyframe, ResolvedObject

LOTTIE_VERSION = "5.7.0"
_PROBE_NAME = "viroc-sample"

# Deterministic enter offset (logical px) used to synthesize a `move` vector,
# since Concrete IR keyframes carry no positional delta.
_MOVE_ENTER_DX = -40.0

# Easings VIROC understands -> Lottie cubic-bezier control handles. `spring` has
# no Lottie equivalent and is degraded to `ease_in_out` (recorded as a note).
_BEZIER = {
    "linear": ({"x": [1.0], "y": [1.0]}, {"x": [0.0], "y": [0.0]}),
    "ease_in_out": ({"x": [0.42], "y": [0.0]}, {"x": [0.58], "y": [1.0]}),
}

_DEGRADE_TO_RECT = frozenset({"icon", "code", "formula"})


def total_frames(ir: ConcreteIR) -> int:
    """Out point of the composition: the last frame any keyframe or caption ends."""
    ends = [kf.end_f for kf in ir.keyframes]
    ends += [c.end_f for c in ir.captions]
    return max(ends) if ends else 0


def _easing_handles(easing: str) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    out_handle, in_handle = _BEZIER.get(easing, _BEZIER["ease_in_out"])
    return out_handle, in_handle


def _opacity_property(obj_kfs: list[Keyframe]) -> dict[str, Any]:
    """Animate layer opacity from fade_in/fade_out keyframes; else fully opaque."""
    stops: list[dict[str, Any]] = []
    for kf in obj_kfs:
        if kf.kind not in {"fade_in", "fade_out"}:
            continue
        start_val = 0.0 if kf.kind == "fade_in" else 100.0
        end_val = 100.0 if kf.kind == "fade_in" else 0.0
        out_h, in_h = _easing_handles(kf.easing)
        stops.append({"t": kf.start_f, "s": [start_val], "o": out_h, "i": in_h})
        stops.append({"t": kf.end_f, "s": [end_val]})
    if not stops:
        return {"a": 0, "k": 100}
    stops.sort(key=lambda s: int(s["t"]))  # type: ignore[arg-type]
    return {"a": 1, "k": stops}


def _position_property(obj: ResolvedObject, obj_kfs: list[Keyframe]) -> dict[str, Any]:
    """Animate position for a `move` keyframe (deterministic enter offset); else static."""
    cx = obj.box.x + obj.box.w / 2
    cy = obj.box.y + obj.box.h / 2
    move = next((kf for kf in obj_kfs if kf.kind == "move"), None)
    if move is None:
        return {"a": 0, "k": [cx, cy, 0]}
    out_h, in_h = _easing_handles(move.easing)
    return {
        "a": 1,
        "k": [
            {"t": move.start_f, "s": [cx + _MOVE_ENTER_DX, cy, 0], "o": out_h, "i": in_h},
            {"t": move.end_f, "s": [cx, cy, 0]},
        ],
    }


def _scale_property(obj_kfs: list[Keyframe]) -> dict[str, Any]:
    """`highlight` has no native Lottie property -> degrade to a scale pulse."""
    hl = next((kf for kf in obj_kfs if kf.kind == "highlight"), None)
    if hl is None:
        return {"a": 0, "k": [100, 100, 100]}
    mid = (hl.start_f + hl.end_f) // 2
    out_h, in_h = _easing_handles(hl.easing)
    return {
        "a": 1,
        "k": [
            {"t": hl.start_f, "s": [100, 100, 100], "o": out_h, "i": in_h},
            {"t": mid, "s": [110, 110, 100], "o": out_h, "i": in_h},
            {"t": hl.end_f, "s": [100, 100, 100]},
        ],
    }


def _transform(obj: ResolvedObject, obj_kfs: list[Keyframe]) -> dict[str, Any]:
    return {
        "o": _opacity_property(obj_kfs),
        "r": {"a": 0, "k": 0},
        "p": _position_property(obj, obj_kfs),
        "a": {"a": 0, "k": [0, 0, 0]},
        "s": _scale_property(obj_kfs),
    }


def _fill_for(style_ref: str) -> dict[str, Any]:
    # Deterministic neutral fill; production styling lives in the resolver, not here.
    return {"ty": "fl", "c": {"a": 0, "k": [0.5, 0.5, 0.5, 1]}, "o": {"a": 0, "k": 100}, "nm": style_ref}


def _rect_shapes(obj: ResolvedObject, draw: bool) -> list[dict[str, Any]]:
    group: list[dict[str, Any]] = [
        {"ty": "rc", "p": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [obj.box.w, obj.box.h]}, "r": {"a": 0, "k": 0}},
        _fill_for(obj.style_ref),
    ]
    if draw:
        group.append(_trim_paths())
    return [{"ty": "gr", "nm": obj.id, "it": group}]


def _arrow_shapes(obj: ResolvedObject, draw: bool) -> list[dict[str, Any]]:
    path = {
        "ty": "sh",
        "ks": {
            "a": 0,
            "k": {
                "c": False,
                "v": [[0, 0], [obj.box.w, obj.box.h]],
                "i": [[0, 0], [0, 0]],
                "o": [[0, 0], [0, 0]],
            },
        },
    }
    group: list[dict[str, Any]] = [
        path,
        {"ty": "st", "c": {"a": 0, "k": [0.6, 0.6, 0.6, 1]}, "o": {"a": 0, "k": 100}, "w": {"a": 0, "k": 4}},
    ]
    if draw:
        group.append(_trim_paths())
    return [{"ty": "gr", "nm": obj.id, "it": group}]


def _trim_paths() -> dict[str, Any]:
    return {
        "ty": "tm",
        "s": {"a": 0, "k": 0},
        "e": {"a": 1, "k": [{"t": 0, "s": [0]}, {"t": 1, "s": [100]}]},
        "o": {"a": 0, "k": 0},
        "m": 1,
    }


def lower(ir: ConcreteIR) -> tuple[dict[str, Any], list[str]]:
    """Lower Concrete IR to a (Lottie document, degradation notes) pair (pure)."""
    width, height = ir.resolution
    layers: list[dict[str, Any]] = []
    degradations: list[str] = []
    kf_by_obj: dict[str, list[Keyframe]] = {}
    for kf in ir.keyframes:
        kf_by_obj.setdefault(kf.object_id, []).append(kf)

    for index, obj in enumerate(ir.objects, start=1):
        obj_kfs = kf_by_obj.get(obj.id, [])
        has_draw = any(kf.kind == "draw" for kf in obj_kfs)
        if any(kf.kind == "highlight" for kf in obj_kfs):
            degradations.append(f'object "{obj.id}": keyframe "highlight" degraded to a scale pulse')
        for kf in obj_kfs:
            if kf.easing == "spring":
                degradations.append(f'object "{obj.id}": easing "spring" degraded to "ease_in_out"')

        primitive = obj.primitive
        if primitive in _DEGRADE_TO_RECT:
            degradations.append(f'object "{obj.id}": primitive "{primitive}" degraded to the rect floor')
            shapes = _rect_shapes(obj, has_draw)
            layer_ty = 4
        elif primitive == "rect":
            shapes = _rect_shapes(obj, has_draw)
            layer_ty = 4
        elif primitive == "arrow":
            shapes = _arrow_shapes(obj, has_draw)
            layer_ty = 4
        else:  # text -> Lottie text layer (player-resolved font)
            shapes = []
            layer_ty = 5
        layer: dict[str, Any] = {
            "ty": layer_ty,
            "nm": obj.id,
            "ind": index,
            "ip": 0,
            "op": total_frames(ir),
            "st": 0,
            "ao": 0,
            "ks": _transform(obj, obj_kfs),
        }
        if layer_ty == 4:
            layer["shapes"] = shapes
        else:
            layer["t"] = _text_document(obj)
        layers.append(layer)

    if ir.captions:
        degradations.append(f"{len(ir.captions)} caption(s) emitted to an SRT sidecar (Lottie has no subtitle track)")

    document = {
        "v": LOTTIE_VERSION,
        "nm": _PROBE_NAME,
        "fr": ir.fps,
        "ip": 0,
        "op": total_frames(ir),
        "w": width,
        "h": height,
        "ddd": 0,
        "assets": [],
        "layers": layers,
    }
    return document, degradations


def _text_document(obj: ResolvedObject) -> dict[str, Any]:
    # Minimal Lottie text-data block; the glyph is the object id (no measurement,
    # so emit stays deterministic). The player resolves the named font at render.
    return {
        "d": {
            "k": [
                {
                    "t": 0,
                    "s": {
                        "t": obj.id,
                        "f": "viroc-default",
                        "s": 48,
                        "lh": 56,
                        "fc": [0.9, 0.9, 0.9],
                        "j": 0,
                    },
                }
            ]
        }
    }


def export_json(ir: ConcreteIR) -> str:
    """Serialize the Lottie document as canonical JSON (byte-deterministic)."""
    document, _ = lower(ir)
    return f"{canonical_json(document)}\n"


def degradations(ir: ConcreteIR) -> list[str]:
    """Return the ordered degradation notes recorded while lowering ``ir``."""
    _, notes = lower(ir)
    return notes


__all__ = ["LOTTIE_VERSION", "degradations", "export_json", "lower", "total_frames"]
