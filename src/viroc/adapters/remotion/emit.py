"""Pure byte-deterministic Remotion project emitter."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

from viroc.adapters import _palette
from viroc.adapters._text import display_text
from viroc.adapters.remotion.templates import (
    INDEX_TS,
    PACKAGE_JSON_TEMPLATE,
    SOURCE_HEADER,
    TSCONFIG_JSON_TEMPLATE,
)
from viroc.core import BuildArtifact, BuildContext, artifact_from_text, canonical_json
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "remotion-source-v0.3"
_COMPOSITION_ID = "VirocScene"
_SANS_FONT = 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
_MONO_FONT = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into a deterministic Remotion project tree without I/O."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Serialize the generated Remotion project tree as canonical JSON."""
    return f"{canonical_json(project_tree(ir))}\n"


def project_tree(ir: ConcreteIR) -> dict[str, str]:
    """Return the generated project files keyed by relative path."""
    return {
        "package.json": _json_file(PACKAGE_JSON_TEMPLATE),
        "tsconfig.json": _json_file(TSCONFIG_JSON_TEMPLATE),
        "src/index.ts": f"{SOURCE_HEADER}{INDEX_TS}",
        "src/Root.tsx": _root_source(ir),
        "src/Composition.tsx": _composition_source(ir),
    }


def materialize_source(source: BuildArtifact, destination: Path) -> BuildArtifact:
    """Write a serialized Remotion project tree to ``destination`` and return it."""
    tree = source_tree(source)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in tree.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return BuildArtifact(kind=source.kind, digest=source.digest, path=destination)


def source_tree(source: BuildArtifact) -> dict[str, str]:
    """Decode a serialized Remotion project tree from a build artifact."""
    if source.data is None:
        raise ValueError("Remotion source artifact did not carry project bytes")
    payload_obj: object = json.loads(source.data.decode("utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("Remotion source artifact must decode to a file map")
    payload = cast(dict[object, object], payload_obj)
    tree: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Remotion source artifact entries must be string pairs")
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Remotion source path escapes project root: {key!r}")
        tree[str(relative)] = value
    return dict(sorted(tree.items()))


def _root_source(ir: ConcreteIR) -> str:
    width, height = ir.resolution
    total_frames = _total_frames(ir)
    return (
        f"{SOURCE_HEADER}"
        "import React from \"react\";\n"
        "import {Composition} from \"remotion\";\n"
        "import {VirocScene} from \"./Composition\";\n\n"
        "export const RemotionRoot: React.FC = () => {\n"
        "  return (\n"
        "    <>\n"
        "      <Composition\n"
        f'        id=\"{_COMPOSITION_ID}\"\n'
        "        component={VirocScene}\n"
        f"        durationInFrames={total_frames}\n"
        f"        fps={ir.fps}\n"
        f"        width={width}\n"
        f"        height={height}\n"
        "        defaultProps={{}}\n"
        "      />\n"
        "    </>\n"
        "  );\n"
        "};\n"
    )


def _composition_source(ir: ConcreteIR) -> str:
    payload = canonical_json(_scene_data(ir))
    return (
        f"{SOURCE_HEADER}"
        "import React from \"react\";\n"
        "import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from \"remotion\";\n\n"
        f"/* viroc-adapter-source-version: {_ADAPTER_SOURCE_VERSION} */\n\n"
        "type Primitive = \"arrow\" | \"code\" | \"formula\" | \"icon\" | \"rect\" | \"text\";\n"
        "type KeyframeKind = \"draw\" | \"fade_in\" | \"fade_out\" | \"highlight\" | \"move\";\n"
        "type Easing = \"ease_in_out\" | \"linear\" | \"spring\";\n\n"
        "type TextTypography = {\n"
        "  color: string;\n"
        "  fontFamily: string;\n"
        "  fontSize: number;\n"
        "  fontWeight: number;\n"
        "  textAlign: string;\n"
        "};\n\n"
        "type SceneObject = {\n"
        "  id: string;\n"
        "  primitive: Primitive;\n"
        "  styleRef: string;\n"
        "  style: Record<string, string>;\n"
        "  text: string;\n"
        "  textStyle: TextTypography | null;\n"
        "  glyph: string;\n"
        "  x: number;\n"
        "  y: number;\n"
        "  w: number;\n"
        "  h: number;\n"
        "  z: number;\n"
        "};\n\n"
        "type SceneKeyframe = {\n"
        "  easing: Easing;\n"
        "  end_f: number;\n"
        "  kind: KeyframeKind;\n"
        "  object_id: string;\n"
        "  start_f: number;\n"
        "};\n\n"
        "type SceneCaption = {\n"
        "  end_f: number;\n"
        "  start_f: number;\n"
        "  text: string;\n"
        "};\n\n"
        "type SceneData = {\n"
        "  background: string;\n"
        "  captions: SceneCaption[];\n"
        "  fps: number;\n"
        "  keyframes: SceneKeyframe[];\n"
        "  objects: SceneObject[];\n"
        "  totalFrames: number;\n"
        "};\n\n"
        f"const DATA: SceneData = {payload};\n\n"
        "const ANIMATIONS_BY_OBJECT = new Map<string, SceneKeyframe[]>();\n"
        "for (const keyframe of DATA.keyframes) {\n"
        "  const entries = ANIMATIONS_BY_OBJECT.get(keyframe.object_id) ?? [];\n"
        "  entries.push(keyframe);\n"
        "  ANIMATIONS_BY_OBJECT.set(keyframe.object_id, entries);\n"
        "}\n"
        "for (const entries of ANIMATIONS_BY_OBJECT.values()) {\n"
        "  entries.sort((a, b) => a.start_f - b.start_f || a.end_f - b.end_f || a.kind.localeCompare(b.kind));\n"
        "}\n\n"
        "type ObjectState = {\n"
        "  draw: number;\n"
        "  highlight: number;\n"
        "  opacity: number;\n"
        "  scale: number;\n"
        "  translateY: number;\n"
        "  visible: boolean;\n"
        "};\n\n"
        "const clamp = (value: number, min: number, max: number): number => {\n"
        "  return Math.min(max, Math.max(min, value));\n"
        "};\n\n"
        "const ease = (name: Easing, value: number): number => {\n"
        "  const t = clamp(value, 0, 1);\n"
        "  if (name === \"linear\") {\n"
        "    return t;\n"
        "  }\n"
        "  if (name === \"spring\") {\n"
        "    return 1 - Math.cos(t * Math.PI * 4) * Math.exp(-6 * t);\n"
        "  }\n"
        "  return t * t * (3 - 2 * t);\n"
        "};\n\n"
        "const stateFor = (objectId: string, frame: number, fps: number): ObjectState => {\n"
        "  const animations = ANIMATIONS_BY_OBJECT.get(objectId) ?? [];\n"
        "  if (animations.length === 0) {\n"
        "    return {draw: 1, highlight: 0, opacity: 1, scale: 1, translateY: 0, visible: true};\n"
        "  }\n"
        "  let visible = false;\n"
        "  let opacity = 0;\n"
        "  let scale = 0.96;\n"
        "  let translateY = 24;\n"
        "  let highlight = 0;\n"
        "  let draw = 0;\n"
        "  for (const keyframe of animations) {\n"
        "    if (frame < keyframe.start_f) {\n"
        "      continue;\n"
        "    }\n"
        "    const span = Math.max(1, keyframe.end_f - keyframe.start_f);\n"
        "    const progress = ease(keyframe.easing, (frame - keyframe.start_f) / span);\n"
        "    if (keyframe.kind === \"fade_in\") {\n"
        "      visible = true;\n"
        "      opacity = Math.max(opacity, progress);\n"
        "      scale = 0.96 + progress * 0.04;\n"
        "      translateY = (1 - progress) * 24;\n"
        "      continue;\n"
        "    }\n"
        "    if (keyframe.kind === \"draw\") {\n"
        "      visible = true;\n"
        "      opacity = 1;\n"
        "      scale = 1;\n"
        "      translateY = 0;\n"
        "      draw = frame >= keyframe.end_f ? 1 : progress;\n"
        "      continue;\n"
        "    }\n"
        "    if (keyframe.kind === \"highlight\") {\n"
        "      visible = true;\n"
        "      opacity = 1;\n"
        "      scale = 1 + 0.02 * progress;\n"
        "      translateY = 0;\n"
        "      highlight = frame >= keyframe.end_f ? 0 : progress;\n"
        "      continue;\n"
        "    }\n"
        "    if (keyframe.kind === \"fade_out\") {\n"
        "      visible = frame < keyframe.end_f;\n"
        "      opacity = frame >= keyframe.end_f ? 0 : 1 - progress;\n"
        "      scale = 1;\n"
        "      translateY = 0;\n"
        "    }\n"
        "  }\n"
        "  if (visible && opacity <= 0) {\n"
        "    opacity = 1;\n"
        "  }\n"
        "  if (draw <= 0 && visible) {\n"
        "    draw = 1;\n"
        "  }\n"
        "  if (!visible) {\n"
        "    const entry = spring({frame, fps, config: {damping: 18}});\n"
        "    return {draw: 0, highlight: 0, opacity: 0, scale: 0.96 + entry * 0.04, translateY: 24, visible: false};\n"
        "  }\n"
        "  return {draw, highlight, opacity: clamp(opacity, 0, 1), scale, translateY, visible};\n"
        "};\n\n"
        "const captionForFrame = (frame: number): string => {\n"
        "  for (const caption of DATA.captions) {\n"
        "    if (frame >= caption.start_f && frame < caption.end_f) {\n"
        "      return caption.text;\n"
        "    }\n"
        "  }\n"
        "  return \"\";\n"
        "};\n\n"
        "const objectStyle = (object: SceneObject, state: ObjectState): React.CSSProperties => ({\n"
        "  position: \"absolute\",\n"
        "  left: object.x,\n"
        "  top: object.y,\n"
        "  width: object.w,\n"
        "  height: object.h,\n"
        "  zIndex: object.z,\n"
        "  opacity: state.opacity,\n"
        "  transform: `translateY(${state.translateY}px) scale(${state.scale})`,\n"
        "  transformOrigin: \"center center\",\n"
        "  filter: state.highlight > 0 ? `drop-shadow(0 0 ${12 + 12 * state.highlight}px rgba(251, 191, 36, ${0.2 + state.highlight * 0.35}))` : undefined,\n"
        "  boxSizing: \"border-box\",\n"
        "  pointerEvents: \"none\",\n"
        "});\n\n"
        "const arrowStrokeWidth = (object: SceneObject): number => Math.max(object.h, 2);\n\n"
        "const ArrowObject: React.FC<{object: SceneObject; state: ObjectState}> = ({object, state}) => {\n"
        "  const stroke = object.style.color ?? \"#E5E7EB\";\n"
        "  const lineWidth = object.w * clamp(state.draw, 0, 1);\n"
        "  const headStart = Math.max(0, lineWidth - 12);\n"
        "  const centerY = object.h / 2;\n"
        "  return (\n"
        "    <svg viewBox={`0 0 ${object.w} ${object.h}`} preserveAspectRatio=\"none\" aria-hidden=\"true\" style={{display: \"block\", width: \"100%\", height: \"100%\", overflow: \"visible\"}}>\n"
        "      <line x1={0} y1={centerY} x2={Math.max(0, lineWidth - 12)} y2={centerY} stroke={stroke} strokeWidth={arrowStrokeWidth(object)} strokeLinecap=\"round\" />\n"
        "      {lineWidth > 0 ? <path d={`M ${headStart} 0 L ${lineWidth} ${centerY} L ${headStart} ${object.h} Z`} fill={stroke} /> : null}\n"
        "    </svg>\n"
        "  );\n"
        "};\n\n"
        "const renderObject = (object: SceneObject, state: ObjectState): React.ReactNode => {\n"
        "  if (!state.visible && state.opacity <= 0) {\n"
        "    return null;\n"
        "  }\n"
        "  const baseStyle = objectStyle(object, state);\n"
        "  if (object.primitive === \"rect\") {\n"
        "    return <div style={{...baseStyle, borderRadius: 18, border: `2px solid ${object.style.stroke_color ?? \"#E5E7EB\"}`, background: `linear-gradient(180deg, color-mix(in srgb, ${object.style.fill_color ?? \"#1D4ED8\"} 82%, white 18%), ${object.style.fill_color ?? \"#1D4ED8\"})`, boxShadow: \"0 10px 28px rgba(11, 16, 32, 0.45)\"}} />;\n"
        "  }\n"
        "  if (object.primitive === \"arrow\") {\n"
        "    return <div style={baseStyle}><ArrowObject object={object} state={state} /></div>;\n"
        "  }\n"
        "  if (object.primitive === \"code\") {\n"
        "    return (\n"
        "      <div style={{...baseStyle, display: \"grid\", placeItems: \"center\", color: object.style.color ?? \"#E5E7EB\"}}>\n"
        "        <pre style={{margin: 0, width: \"100%\", height: \"100%\", display: \"grid\", placeItems: \"center\", padding: \"14px 18px\", borderRadius: 14, background: \"rgba(15, 23, 42, 0.78)\", border: \"1px solid rgba(148, 163, 184, 0.28)\", boxShadow: \"0 10px 28px rgba(11, 16, 32, 0.45)\", fontFamily: \"ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace\", fontSize: 20, fontWeight: 600, lineHeight: 1.3}}>{object.text}</pre>\n"
        "      </div>\n"
        "    );\n"
        "  }\n"
        "  if (object.primitive === \"formula\") {\n"
        "    return (\n"
        "      <div style={{...baseStyle, display: \"grid\", placeItems: \"center\", color: object.style.color ?? \"#E5E7EB\"}}>\n"
        "        <div style={{width: \"100%\", height: \"100%\", display: \"grid\", placeItems: \"center\", borderRadius: 16, background: \"rgba(15, 23, 42, 0.42)\", border: \"1px solid rgba(229, 231, 235, 0.24)\", fontFamily: '\"Times New Roman\", Georgia, serif', fontSize: 26, fontStyle: \"italic\", fontWeight: 600, lineHeight: 1.2}}>{object.text}</div>\n"
        "      </div>\n"
        "    );\n"
        "  }\n"
        "  if (object.primitive === \"icon\") {\n"
        "    return (\n"
        "      <div style={{...baseStyle, display: \"grid\", placeItems: \"center\", color: object.style.color ?? \"#E5E7EB\"}}>\n"
        "        <div style={{width: \"100%\", height: \"100%\", display: \"grid\", placeItems: \"center\", borderRadius: 999, background: `radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.2), transparent 35%), ${object.style.fill_color ?? \"#0891B2\"}`, border: `2px solid ${object.style.stroke_color ?? \"rgba(229, 231, 235, 0.4)\"}`, boxShadow: \"0 10px 28px rgba(11, 16, 32, 0.45)\", fontSize: 34, fontWeight: 700}}>{object.glyph}</div>\n"
        "      </div>\n"
        "    );\n"
        "  }\n"
        "  const ts = object.textStyle!;\n"
        "  return (\n"
        "    <div style={{...baseStyle, display: \"grid\", placeItems: \"center\"}}>\n"
        "      <span style={{color: ts.color, fontFamily: ts.fontFamily, fontSize: ts.fontSize, fontWeight: ts.fontWeight, letterSpacing: \"-0.02em\", lineHeight: 1.1, textAlign: ts.textAlign as React.CSSProperties[\"textAlign\"], width: \"100%\"}}>{object.text}</span>\n"
        "    </div>\n"
        "  );\n"
        "};\n\n"
        "export const VirocScene: React.FC = () => {\n"
        "  const frame = useCurrentFrame();\n"
        "  const {fps, width, height} = useVideoConfig();\n"
        "  const caption = captionForFrame(frame);\n"
        "  return (\n"
        "    <AbsoluteFill style={{backgroundColor: DATA.background, color: \"#E5E7EB\", fontFamily: \"Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \\\"Segoe UI\\\", sans-serif\"}}>\n"
        "      <AbsoluteFill style={{display: \"grid\", placeItems: \"center\"}}>\n"
        "        <div style={{position: \"relative\", width, height, overflow: \"hidden\", background: \"linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(11, 16, 32, 1))\", boxShadow: \"0 24px 64px rgba(0, 0, 0, 0.35)\", isolation: \"isolate\"}}>\n"
        "          {DATA.objects.map((object) => renderObject(object, stateFor(object.id, frame, fps)))}\n"
        "          <div style={{position: \"absolute\", left: 96, right: 96, bottom: 48, minHeight: 72, display: \"grid\", alignItems: \"center\", justifyItems: \"center\", padding: \"14px 18px\", borderRadius: 18, background: \"rgba(11, 16, 32, 0.72)\", border: \"1px solid rgba(229, 231, 235, 0.14)\", fontSize: 28, fontWeight: 500, lineHeight: 1.25, letterSpacing: \"-0.01em\", textAlign: \"center\", opacity: caption ? 1 : 0}}>\n"
        "            {caption}\n"
        "          </div>\n"
        "        </div>\n"
        "      </AbsoluteFill>\n"
        "    </AbsoluteFill>\n"
        "  );\n"
        "};\n"
    )


def _scene_data(ir: ConcreteIR) -> dict[str, Any]:
    return {
        "background": "#0B1020",
        "captions": [_caption_data(caption) for caption in _sorted_captions(ir.captions)],
        "fps": ir.fps,
        "keyframes": [_keyframe_data(keyframe) for keyframe in _sorted_keyframes(ir.keyframes)],
        "objects": [_object_data(obj) for obj in _sorted_objects(ir.objects)],
        "totalFrames": _total_frames(ir),
    }


def _style_for(style_ref: str) -> dict[str, str]:
    if style_ref.startswith("edge."):
        return {"color": _palette.edge_color(style_ref)}
    if style_ref in ("label", "showcase.title"):
        return {"color": _palette.LABEL_COLOR}
    fill, stroke = _palette.box_style(style_ref)
    return {"fill_color": fill, "stroke_color": stroke}


def _object_data(obj: ResolvedObject) -> dict[str, Any]:
    if obj.primitive == "text":
        ts = _palette.text_style(obj.style_ref)
        text_style_data: dict[str, Any] | None = {
            "color": ts.color,
            "fontFamily": _MONO_FONT if ts.mono else _SANS_FONT,
            "fontSize": ts.size,
            "fontWeight": 700 if ts.bold else 400,
            "textAlign": ts.align,
        }
        obj_style: dict[str, str] = {}
    else:
        text_style_data = None
        obj_style = _style_for(obj.style_ref)
    return {
        "glyph": _icon_glyph(obj),
        "h": obj.box.h,
        "id": obj.id,
        "primitive": obj.primitive,
        "style": dict(sorted(obj_style.items())),
        "styleRef": obj.style_ref,
        "text": display_text(obj),
        "textStyle": text_style_data,
        "w": obj.box.w,
        "x": obj.box.x,
        "y": obj.box.y,
        "z": obj.z,
    }


def _keyframe_data(keyframe: Keyframe) -> dict[str, Any]:
    return {
        "easing": keyframe.easing,
        "end_f": keyframe.end_f,
        "kind": keyframe.kind,
        "object_id": keyframe.object_id,
        "start_f": keyframe.start_f,
    }


def _caption_data(caption: Caption) -> dict[str, Any]:
    return {
        "end_f": caption.end_f,
        "start_f": caption.start_f,
        "text": caption.text,
    }


def _sorted_objects(objects: list[ResolvedObject]) -> list[ResolvedObject]:
    return sorted(objects, key=lambda item: (item.z, item.id))


def _sorted_keyframes(keyframes: list[Keyframe]) -> list[Keyframe]:
    return sorted(keyframes, key=lambda item: (item.start_f, item.end_f, item.object_id, item.kind))


def _sorted_captions(captions: list[Caption]) -> list[Caption]:
    return sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))


def _total_frames(ir: ConcreteIR) -> int:
    end_frames = [keyframe.end_f for keyframe in ir.keyframes]
    end_frames.extend(caption.end_f for caption in ir.captions)
    return max(end_frames, default=1)


def _icon_glyph(obj: ResolvedObject) -> str:
    initials = [part[0] for part in display_text(obj).split() if part]
    return "".join(initials[:2]).upper()


def _json_file(value: dict[str, Any]) -> str:
    return f"{canonical_json(value)}\n"


__all__ = [
    "emit",
    "materialize_source",
    "project_tree",
    "source_for",
    "source_tree",
]
