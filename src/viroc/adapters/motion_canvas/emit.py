"""Pure byte-deterministic Motion Canvas project emitter."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import cast

from viroc.adapters.motion_canvas.templates import (
    MOTION_CANVAS_D_TS,
    PACKAGE_JSON_TEMPLATE,
    SOURCE_HEADER,
    STYLE_TOKENS,
    TSCONFIG_JSON_TEMPLATE,
    VITE_CONFIG_TS,
)
from viroc.core import BuildArtifact, BuildContext, artifact_from_text, canonical_json
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "motion-canvas-source-v0.1"
_DEFAULT_STYLE = {"color": "#E5E7EB"}
_SCENE_FILENAME = "src/scenes/viroc.tsx"
_PROJECT_FILENAME = "src/project.ts"


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into a deterministic Motion Canvas project tree."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Serialize the generated Motion Canvas project tree as canonical JSON."""
    return f"{canonical_json(project_tree(ir))}\n"


def project_tree(ir: ConcreteIR) -> dict[str, str]:
    """Return the generated project files keyed by relative path."""
    return {
        "package.json": _json_file(PACKAGE_JSON_TEMPLATE),
        "tsconfig.json": _json_file(TSCONFIG_JSON_TEMPLATE),
        "vite.config.ts": VITE_CONFIG_TS,
        "src/motion-canvas.d.ts": MOTION_CANVAS_D_TS,
        _PROJECT_FILENAME: _project_source(),
        _SCENE_FILENAME: _scene_source(ir),
    }


def materialize_source(source: BuildArtifact, destination: Path) -> BuildArtifact:
    """Write a serialized Motion Canvas project tree to ``destination``."""
    tree = source_tree(source)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in tree.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return BuildArtifact(kind=source.kind, digest=source.digest, path=destination)


def source_tree(source: BuildArtifact) -> dict[str, str]:
    """Decode a serialized Motion Canvas project tree from a build artifact."""
    if source.data is None:
        raise ValueError("Motion Canvas source artifact did not carry project bytes")
    payload_obj: object = json.loads(source.data.decode("utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("Motion Canvas source artifact must decode to a file map")
    payload = cast(dict[object, object], payload_obj)
    tree: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Motion Canvas source artifact entries must be string pairs")
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Motion Canvas source path escapes project root: {key!r}")
        tree[str(relative)] = value
    return dict(sorted(tree.items()))


def _project_source() -> str:
    return (
        f"{SOURCE_HEADER}"
        'import {makeProject} from "@motion-canvas/core";\n\n'
        'import viroc from "./scenes/viroc?scene";\n\n'
        "export default makeProject({\n"
        "  scenes: [viroc],\n"
        "});\n"
    )


def _scene_source(ir: ConcreteIR) -> str:
    lines = [
        f"{SOURCE_HEADER}",
        'import {Circle, Code, Line, Rect, Txt, makeScene2D} from "@motion-canvas/2d";\n',
        'import {all, createRef, waitFor} from "@motion-canvas/core";\n\n',
        f"/* viroc-adapter-source-version: {_ADAPTER_SOURCE_VERSION} */\n",
        f"const CAPTIONS = {canonical_json([_caption_data(caption) for caption in _sorted_captions(ir.captions)])};\n\n",
        "export default makeScene2D(function* (view) {\n",
        '  view.fill("#0B1020");\n',
        "\n",
    ]
    for obj in _sorted_objects(ir.objects):
        lines.append(f"  const {_ref_name(obj.id)} = createRef<{_ref_type(obj.primitive)}>();\n")
    lines.append("\n")
    for obj in _sorted_objects(ir.objects):
        lines.extend(_object_lines(obj, resolution=ir.resolution))
    if ir.captions:
        lines.append("\n")
        lines.append("  void CAPTIONS;\n")
    lines.append("\n")
    cursor = 0
    for start_f, end_f, keyframes in _keyframe_groups(ir.keyframes):
        if start_f > cursor:
            lines.append(f"  yield* waitFor({_seconds(start_f - cursor, ir.fps)});\n")
        expressions = [_animation_expression(keyframe, fps=ir.fps) for keyframe in keyframes]
        if len(expressions) == 1:
            lines.append(f"  yield* {expressions[0]};\n")
        else:
            lines.append("  yield* all(\n")
            for expression in expressions:
                lines.append(f"    {expression},\n")
            lines.append("  );\n")
        cursor = end_f
    lines.append("});\n")
    return "".join(lines)


def _object_lines(
    obj: ResolvedObject, *, resolution: tuple[int, int]
) -> list[str]:
    width, height = resolution
    center_x = obj.box.x + (obj.box.w / 2) - (width / 2)
    center_y = obj.box.y + (obj.box.h / 2) - (height / 2)
    ref = _ref_name(obj.id)
    if obj.primitive == "arrow":
        color = STYLE_TOKENS.get(obj.style_ref, _DEFAULT_STYLE)["color"]
        half = obj.box.w / 2
        return [
            "  view.add(\n",
            f"    <Line ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} points={{[[-{_fmt(half)}, 0], [{_fmt(half)}, 0]]}} stroke={{{_string(color)}}} lineWidth={{8}} end={{0}} endArrow />\n",
            "  );\n",
        ]
    if obj.primitive == "rect":
        style = STYLE_TOKENS.get(
            obj.style_ref,
            {"fill_color": "#1D4ED8", "stroke_color": "#E5E7EB"},
        )
        return [
            "  view.add(\n",
            f"    <Rect ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} width={{{_fmt(obj.box.w)}}} height={{{_fmt(obj.box.h)}}} radius={{18}} fill={{{_string(style['fill_color'])}}} stroke={{{_string(style['stroke_color'])}}} lineWidth={{4}} opacity={{0}} />\n",
            "  );\n",
        ]
    if obj.primitive == "text":
        color = STYLE_TOKENS.get(obj.style_ref, _DEFAULT_STYLE)["color"]
        return [
            "  view.add(\n",
            f"    <Txt ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} text={{{_string(_display_text(obj))}}} fill={{{_string(color)}}} fontFamily={{{_string('Inter, ui-sans-serif, system-ui')}}} fontSize={{32}} fontWeight={{600}} opacity={{0}} />\n",
            "  );\n",
        ]
    if obj.primitive == "code":
        color = STYLE_TOKENS.get(obj.style_ref, _DEFAULT_STYLE)["color"]
        return [
            "  view.add(\n",
            f"    <Code ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} code={{{_string(_display_text(obj))}}} fill={{{_string(color)}}} fontSize={{28}} opacity={{0}} />\n",
            "  );\n",
        ]
    if obj.primitive == "formula":
        color = STYLE_TOKENS.get(obj.style_ref, _DEFAULT_STYLE)["color"]
        return [
            "  view.add(\n",
            f"    <Txt ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} text={{{_string(_display_text(obj))}}} fill={{{_string(color)}}} fontFamily={{{_string('Times New Roman, serif')}}} fontStyle={{{_string('italic')}}} fontSize={{30}} opacity={{0}} />\n",
            "  );\n",
        ]
    if obj.primitive == "icon":
        style = STYLE_TOKENS.get(
            obj.style_ref,
            {"fill_color": "#0891B2", "stroke_color": "#E5E7EB"},
        )
        return [
            "  view.add(\n",
            f"    <Circle ref={{{ref}}} x={{{_fmt(center_x)}}} y={{{_fmt(center_y)}}} size={{{_fmt(min(obj.box.w, obj.box.h))}}} fill={{{_string(style['fill_color'])}}} stroke={{{_string(style['stroke_color'])}}} lineWidth={{4}} opacity={{0}}>\n",
            f"      <Txt text={{{_string(_icon_glyph(obj))}}} fill={{{_string('#E5E7EB')}}} fontSize={{26}} fontWeight={{700}} />\n",
            "    </Circle>\n",
            "  );\n",
        ]
    raise ValueError(f"Motion Canvas emitter cannot lower primitive {obj.primitive!r}")


def _animation_expression(keyframe: Keyframe, *, fps: int) -> str:
    ref = f"{_ref_name(keyframe.object_id)}()"
    duration = _seconds(keyframe.end_f - keyframe.start_f, fps)
    if keyframe.kind == "fade_in":
        return f"{ref}.opacity(1, {duration})"
    if keyframe.kind == "fade_out":
        return f"{ref}.opacity(0, {duration})"
    if keyframe.kind == "draw":
        return f"{ref}.end(1, {duration})"
    if keyframe.kind == "highlight":
        half = _seconds(max((keyframe.end_f - keyframe.start_f) / 2, 1), fps)
        return f"{ref}.scale(1.06, {half}).to(1, {half})"
    raise ValueError(f"Motion Canvas emitter cannot lower keyframe kind {keyframe.kind!r}")


def _keyframe_groups(keyframes: list[Keyframe]) -> list[tuple[int, int, list[Keyframe]]]:
    grouped: dict[tuple[int, int], list[Keyframe]] = {}
    for keyframe in _sorted_keyframes(keyframes):
        grouped.setdefault((keyframe.start_f, keyframe.end_f), []).append(keyframe)
    return [
        (start_f, end_f, grouped[(start_f, end_f)])
        for start_f, end_f in sorted(grouped)
    ]


def _sorted_objects(objects: list[ResolvedObject]) -> list[ResolvedObject]:
    return sorted(objects, key=lambda item: (item.z, item.id))


def _sorted_keyframes(keyframes: list[Keyframe]) -> list[Keyframe]:
    return sorted(
        keyframes,
        key=lambda item: (item.start_f, item.end_f, item.object_id, item.kind),
    )


def _sorted_captions(captions: list[Caption]) -> list[Caption]:
    return sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))


def _caption_data(caption: Caption) -> dict[str, object]:
    return {
        "end_f": caption.end_f,
        "start_f": caption.start_f,
        "text": caption.text,
    }


def _display_text(obj: ResolvedObject) -> str:
    parts = obj.id.split(".")
    source = parts[-2] if len(parts) >= 2 and parts[-1] == "label" else parts[-1]
    return source.replace("_", " ").title()


def _icon_glyph(obj: ResolvedObject) -> str:
    initials = [part[0] for part in _display_text(obj).split() if part]
    return "".join(initials[:2]).upper()


def _ref_name(object_id: str) -> str:
    sanitized: list[str] = []
    for char in object_id:
        sanitized.append(char if char.isalnum() else "_")
    return "ref_" + "".join(sanitized)


def _ref_type(primitive: str) -> str:
    if primitive == "arrow":
        return "Line"
    if primitive == "rect":
        return "Rect"
    if primitive == "text":
        return "Txt"
    if primitive == "code":
        return "Code"
    if primitive == "formula":
        return "Txt"
    if primitive == "icon":
        return "Circle"
    raise ValueError(f"Motion Canvas emitter does not know ref type for {primitive!r}")


def _seconds(frames: int | float, fps: int) -> str:
    return _fmt(float(frames) / fps)


def _fmt(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_file(value: dict[str, object]) -> str:
    return f"{canonical_json(value)}\n"


__all__ = [
    "emit",
    "materialize_source",
    "project_tree",
    "source_for",
    "source_tree",
]
