"""Pure byte-deterministic image-sequence review emitter."""

# ruff: noqa: E501

from __future__ import annotations

import importlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

from viroc.core import BuildArtifact, BuildContext, artifact_from_text, canonical_json
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "image-sequence-source-v0.1"
_BACKGROUND = "#0B1020"
_DEFAULT_STYLE = {"color": "#E5E7EB"}
_STYLE_TOKENS: dict[str, dict[str, str]] = {
    "edge.default": {"color": "#94A3B8"},
    "edge.lookup": {"color": "#38BDF8"},
    "edge.split": {"color": "#38BDF8"},
    "edge.store": {"color": "#22C55E"},
    "edge.transform": {"color": "#A78BFA"},
    "label": {"color": "#E5E7EB"},
    "node.data_source": {"fill_color": "#1D4ED8", "stroke_color": "#60A5FA"},
    "node.intermediate": {"fill_color": "#7C3AED", "stroke_color": "#C4B5FD"},
    "node.model": {"fill_color": "#BE123C", "stroke_color": "#FDA4AF"},
    "node.process": {"fill_color": "#0891B2", "stroke_color": "#67E8F9"},
    "node.storage": {"fill_color": "#047857", "stroke_color": "#6EE7B7"},
}


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into deterministic image-sequence review artifacts."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Serialize the generated review artifact tree as canonical JSON."""
    return f"{canonical_json(_artifact_tree(ir))}\n"


def materialize_source(source: BuildArtifact, destination: Path) -> BuildArtifact:
    """Write the serialized image-sequence artifact tree to ``destination``."""
    tree = source_tree(source)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in tree.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _write_optional_png_snapshots(destination)
    return BuildArtifact(kind=source.kind, digest=source.digest, path=destination)


def source_tree(source: BuildArtifact) -> dict[str, str]:
    """Decode a serialized review artifact tree from a build artifact."""
    if source.data is None:
        raise ValueError("image-sequence source artifact did not carry project bytes")
    payload_obj: object = json.loads(source.data.decode("utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("image-sequence source artifact must decode to a file map")
    payload = cast(dict[object, object], payload_obj)
    tree: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("image-sequence source artifact entries must be string pairs")
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"image-sequence source path escapes project root: {key!r}")
        tree[str(relative)] = value
    return dict(sorted(tree.items()))


def frame_plan(ir: ConcreteIR) -> dict[str, object]:
    """Return the deterministic per-frame review plan."""
    frames = [frame_snapshot(ir, frame) for frame in range(total_frames(ir))]
    return {
        "adapter_source_version": _ADAPTER_SOURCE_VERSION,
        "fps": ir.fps,
        "frames": frames,
        "objects": [_object_data(obj) for obj in _sorted_objects(ir.objects)],
        "resolution": {"height": ir.resolution[1], "width": ir.resolution[0]},
        "total_frames": total_frames(ir),
    }


def frame_snapshot(ir: ConcreteIR, frame: int) -> dict[str, object]:
    """Return the deterministic review snapshot for one frame index."""
    snapshots: list[dict[str, object]] = []
    for obj in _sorted_objects(ir.objects):
        opacity = _opacity_at(obj.id, frame, ir.keyframes)
        draw_progress = _draw_progress_at(obj.id, frame, ir.keyframes)
        highlighted = _highlighted_at(obj.id, frame, ir.keyframes)
        if opacity <= 0 and draw_progress <= 0 and not highlighted:
            continue
        snapshots.append(
            {
                "draw_progress": _round(draw_progress),
                "highlighted": highlighted,
                "id": obj.id,
                "opacity": _round(opacity),
                "primitive": obj.primitive,
            }
        )
    return {
        "active_caption": _active_caption(ir.captions, frame),
        "frame": frame,
        "objects": snapshots,
    }


def total_frames(ir: ConcreteIR) -> int:
    """Return the reviewable timeline span in whole frames."""
    end_frames = [keyframe.end_f for keyframe in ir.keyframes]
    end_frames.extend(caption.end_f for caption in ir.captions)
    return max(end_frames, default=1)


def _artifact_tree(ir: ConcreteIR) -> dict[str, str]:
    plan = frame_plan(ir)
    return {
        "captions.md": _captions_markdown(ir.captions),
        "frame-plan.json": f"{canonical_json(plan)}\n",
        "summary.md": _summary_markdown(ir, plan),
    }


def _summary_markdown(ir: ConcreteIR, plan: dict[str, object]) -> str:
    objects = cast(list[dict[str, object]], plan["objects"])
    lines = [
        "# Image sequence review\n",
        "\n",
        f"- adapter source version: `{_ADAPTER_SOURCE_VERSION}`\n",
        f"- resolution: `{ir.resolution[0]}x{ir.resolution[1]}`\n",
        f"- fps: `{ir.fps}`\n",
        f"- total frames: `{plan['total_frames']}`\n",
        f"- object count: `{len(objects)}`\n",
        "\n",
        "## Objects\n",
        "\n",
    ]
    for obj in objects:
        lines.append(
            f"- `{obj['id']}` — {obj['primitive']} @ ({obj['x']}, {obj['y']}) {obj['w']}×{obj['h']}\n"
        )
    return "".join(lines)


def _captions_markdown(captions: list[Caption]) -> str:
    lines = ["# Captions\n", "\n"]
    if not captions:
        lines.append("(none)\n")
        return "".join(lines)
    for caption in _sorted_captions(captions):
        lines.append(f"- `{caption.start_f}–{caption.end_f}` {caption.text}\n")
    return "".join(lines)


def _object_data(obj: ResolvedObject) -> dict[str, object]:
    style = _STYLE_TOKENS.get(obj.style_ref, _DEFAULT_STYLE)
    payload: dict[str, object] = {
        "h": obj.box.h,
        "id": obj.id,
        "primitive": obj.primitive,
        "style": dict(sorted(style.items())),
        "style_ref": obj.style_ref,
        "text": _display_text(obj),
        "w": obj.box.w,
        "x": obj.box.x,
        "y": obj.box.y,
        "z": obj.z,
    }
    if obj.primitive == "icon":
        payload["glyph"] = _icon_glyph(obj)
    return payload


def _opacity_at(object_id: str, frame: int, keyframes: list[Keyframe]) -> float:
    opacity = 0.0
    for keyframe in _sorted_keyframes(keyframes):
        if keyframe.object_id != object_id:
            continue
        progress = _progress(frame, keyframe)
        if keyframe.kind == "fade_in":
            if frame >= keyframe.end_f:
                opacity = 1.0
            elif frame >= keyframe.start_f:
                opacity = progress
        elif keyframe.kind == "fade_out":
            if frame >= keyframe.end_f:
                opacity = 0.0
            elif frame >= keyframe.start_f:
                opacity = 1.0 - progress
    return max(0.0, min(opacity, 1.0))


def _draw_progress_at(object_id: str, frame: int, keyframes: list[Keyframe]) -> float:
    progress = 0.0
    for keyframe in _sorted_keyframes(keyframes):
        if keyframe.object_id != object_id or keyframe.kind != "draw":
            continue
        if frame >= keyframe.end_f:
            progress = 1.0
        elif frame >= keyframe.start_f:
            progress = max(progress, _progress(frame, keyframe))
    return max(0.0, min(progress, 1.0))


def _highlighted_at(object_id: str, frame: int, keyframes: list[Keyframe]) -> bool:
    return any(
        keyframe.object_id == object_id
        and keyframe.kind == "highlight"
        and keyframe.start_f <= frame < keyframe.end_f
        for keyframe in keyframes
    )


def _active_caption(captions: list[Caption], frame: int) -> str:
    for caption in _sorted_captions(captions):
        if caption.start_f <= frame < caption.end_f:
            return caption.text
    return ""


def _progress(frame: int, keyframe: Keyframe) -> float:
    span = max(keyframe.end_f - keyframe.start_f, 1)
    return max(0.0, min((frame - keyframe.start_f) / span, 1.0))


def _sorted_objects(objects: list[ResolvedObject]) -> list[ResolvedObject]:
    return sorted(objects, key=lambda item: (item.z, item.id))


def _sorted_keyframes(keyframes: list[Keyframe]) -> list[Keyframe]:
    return sorted(keyframes, key=lambda item: (item.start_f, item.end_f, item.object_id, item.kind))


def _sorted_captions(captions: list[Caption]) -> list[Caption]:
    return sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))


def _display_text(obj: ResolvedObject) -> str:
    parts = obj.id.split(".")
    source = parts[-2] if len(parts) >= 2 and parts[-1] == "label" else parts[-1]
    return source.replace("_", " ").title()


def _icon_glyph(obj: ResolvedObject) -> str:
    initials = [part[0] for part in _display_text(obj).split() if part]
    return "".join(initials[:2]).upper()


def _round(value: float) -> float:
    return round(value, 4)


def _write_optional_png_snapshots(destination: Path) -> None:
    try:
        image_module = cast(Any, importlib.import_module("PIL.Image"))
        draw_module = cast(Any, importlib.import_module("PIL.ImageDraw"))
    except ModuleNotFoundError:
        return
    plan_path = destination / "frame-plan.json"
    plan = cast(dict[str, object], json.loads(plan_path.read_text(encoding="utf-8")))
    frames = cast(list[dict[str, object]], plan["frames"])
    objects = cast(list[dict[str, object]], plan["objects"])
    resolution = cast(dict[str, object], plan["resolution"])
    frame_dir = destination / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    sample_set = _sampled_frame_numbers(frames)
    width = _field_int(resolution, "width")
    height = _field_int(resolution, "height")
    for frame_number in sample_set:
        snapshot = frames[frame_number]
        image = image_module.new("RGBA", (480, 270), _BACKGROUND)
        draw = draw_module.Draw(image)
        _draw_snapshot(draw, snapshot, objects, width=width, height=height)
        image.save(frame_dir / f"frame-{frame_number:04d}.png")


def _sampled_frame_numbers(frames: list[dict[str, object]]) -> list[int]:
    if not frames:
        return []
    picks = {0, len(frames) - 1}
    for snapshot in frames:
        frame = cast(int, snapshot["frame"])
        objects = cast(list[dict[str, object]], snapshot["objects"])
        if any(cast(bool, item["highlighted"]) for item in objects):
            picks.add(frame)
        if any(cast(float, item["draw_progress"]) not in (0.0, 1.0) for item in objects):
            picks.add(frame)
    return sorted(picks)


def _draw_snapshot(
    draw: Any,
    snapshot: dict[str, object],
    objects: list[dict[str, object]],
    *,
    width: int,
    height: int,
) -> None:
    object_index = {cast(str, obj["id"]): obj for obj in objects}
    scale_x = 480 / max(width, 1)
    scale_y = 270 / max(height, 1)
    for item in cast(list[dict[str, object]], snapshot["objects"]):
        obj = object_index[cast(str, item["id"])]
        primitive = cast(str, obj["primitive"])
        x = int(_field_float(obj, "x") * scale_x)
        y = int(_field_float(obj, "y") * scale_y)
        w = max(int(_field_float(obj, "w") * scale_x), 1)
        h = max(int(_field_float(obj, "h") * scale_y), 1)
        style = cast(dict[str, str], obj["style"])
        fill = style.get("fill_color", _BACKGROUND)
        stroke = style.get("stroke_color", style.get("color", "#E5E7EB"))
        if primitive == "arrow":
            draw.line((x, y + h // 2, x + w, y + h // 2), fill=stroke, width=3)
        else:
            draw.rounded_rectangle(
                (x, y, x + w, y + h),
                radius=8,
                fill=fill,
                outline=stroke,
                width=2,
            )
            draw.text((x + 8, y + 6), cast(str, obj["text"]), fill=style.get("color", "#E5E7EB"))
    caption = cast(str, snapshot["active_caption"])
    if caption:
        draw.rounded_rectangle((32, 214, 448, 252), radius=10, fill="#111827")
        draw.text((44, 226), caption[:64], fill="#E5E7EB")


def _field_float(mapping: dict[str, object], key: str) -> float:
    return float(cast(float | int, mapping[key]))


def _field_int(mapping: dict[str, object], key: str) -> int:
    return int(cast(int, mapping[key]))


__all__ = [
    "emit",
    "frame_plan",
    "frame_snapshot",
    "materialize_source",
    "source_for",
    "source_tree",
    "total_frames",
]
