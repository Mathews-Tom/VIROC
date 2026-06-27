"""Pure byte-deterministic static storyboard review emitter."""

# ruff: noqa: E501

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import cast

from viroc.adapters._text import display_text
from viroc.core import (
    BuildArtifact,
    BuildContext,
    artifact_from_text,
    canonical_json,
    hash_bytes,
)
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "static-storyboard-source-v0.1"
REVIEW_MANIFEST_FILENAME = "review-manifest.json"


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into deterministic static storyboard review artifacts."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Serialize the generated storyboard artifact tree as canonical JSON."""
    return f"{canonical_json(_artifact_tree(ir))}\n"


def materialize_source(source: BuildArtifact, destination: Path) -> BuildArtifact:
    """Write the serialized storyboard artifact tree to ``destination``."""
    tree = source_tree(source)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in tree.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return BuildArtifact(kind=source.kind, digest=source.digest, path=destination)


def source_tree(source: BuildArtifact) -> dict[str, str]:
    """Decode a serialized storyboard artifact tree from a build artifact."""
    if source.data is None:
        raise ValueError("static-storyboard source artifact did not carry project bytes")
    payload_obj: object = json.loads(source.data.decode("utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError("static-storyboard source artifact must decode to a file map")
    payload = cast(dict[object, object], payload_obj)
    tree: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("static-storyboard source artifact entries must be string pairs")
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"static-storyboard source path escapes project root: {key!r}")
        tree[str(relative)] = value
    return dict(sorted(tree.items()))


def review_manifest(source: BuildArtifact) -> str:
    """Serialize a deterministic manifest linking each review artifact to its hash.

    The manifest is derived from the materialized source tree, so it carries the
    overall source digest plus a per-file content hash for ``storyboard.md``,
    ``script.md``, ``scene-cards.json``, and ``captions.md``. It is a review
    surface only and is never part of the source tree, so it does not affect the
    backend source hash or any committed generated-source baseline.
    """
    tree = source_tree(source)
    artifacts = {name: hash_bytes(body.encode("utf-8")) for name, body in tree.items()}
    manifest: dict[str, object] = {
        "adapter_source_version": _ADAPTER_SOURCE_VERSION,
        "artifacts": artifacts,
        "source_hash": source.digest,
    }
    return f"{canonical_json(manifest)}\n"


def scene_cards(ir: ConcreteIR) -> list[dict[str, object]]:
    """Return deterministic scene-card data grouped by scene prefix."""
    objects_by_scene: dict[str, list[ResolvedObject]] = defaultdict(list)
    keyframes_by_scene: dict[str, list[Keyframe]] = defaultdict(list)
    for obj in _sorted_objects(ir.objects):
        objects_by_scene[_scene_id(obj.id)].append(obj)
    for keyframe in _sorted_keyframes(ir.keyframes):
        keyframes_by_scene[_scene_id(keyframe.object_id)].append(keyframe)
    scene_names = sorted(objects_by_scene)
    scene_ranges: dict[str, tuple[int, int]] = {}
    for scene in scene_names:
        scene_keyframes = keyframes_by_scene.get(scene, [])
        start_f = min((keyframe.start_f for keyframe in scene_keyframes), default=0)
        end_f = max((keyframe.end_f for keyframe in scene_keyframes), default=start_f)
        scene_ranges[scene] = (start_f, end_f)
    captions_by_scene: dict[str, list[Caption]] = {scene: [] for scene in scene_names}
    for caption in _sorted_captions(ir.captions):
        scene = _caption_scene(caption, scene_ranges)
        if scene is not None:
            captions_by_scene[scene].append(caption)
    cards: list[dict[str, object]] = []
    for scene in scene_names:
        scene_objects = objects_by_scene[scene]
        scene_keyframes = keyframes_by_scene.get(scene, [])
        scene_captions = captions_by_scene.get(scene, [])
        start_f, end_f = scene_ranges[scene]
        if scene_captions:
            start_f = min(start_f, min(caption.start_f for caption in scene_captions))
            end_f = max(end_f, max(caption.end_f for caption in scene_captions))
        cards.append(
            {
                "caption_lines": [caption.text for caption in scene_captions],
                "end_frame": end_f,
                "end_seconds": _seconds(end_f, ir.fps),
                "object_count": len(scene_objects),
                "objects": [_object_data(obj) for obj in scene_objects],
                "scene_id": scene,
                "start_frame": start_f,
                "start_seconds": _seconds(start_f, ir.fps),
                "timeline": [_keyframe_data(keyframe) for keyframe in scene_keyframes],
            }
        )
    return cards


def storyboard_markdown(ir: ConcreteIR) -> str:
    """Render a PDF-ready Markdown storyboard from scene cards."""
    cards = scene_cards(ir)
    lines = [
        "# Static storyboard review\n",
        "\n",
        f"- adapter source version: `{_ADAPTER_SOURCE_VERSION}`\n",
        f"- resolution: `{ir.resolution[0]}x{ir.resolution[1]}`\n",
        f"- fps: `{ir.fps}`\n",
        f"- scenes: `{len(cards)}`\n",
        "\n",
    ]
    for card in cards:
        lines.extend(
            [
                f"## Scene `{card['scene_id']}`\n",
                "\n",
                f"- frames: `{card['start_frame']}–{card['end_frame']}`\n",
                f"- seconds: `{card['start_seconds']}–{card['end_seconds']}`\n",
                f"- object count: `{card['object_count']}`\n",
                "\n",
                "### Objects\n",
                "\n",
            ]
        )
        for obj in cast(list[dict[str, object]], card["objects"]):
            lines.append(
                f"- `{obj['id']}` — {obj['primitive']} @ ({obj['x']}, {obj['y']}) {obj['w']}×{obj['h']}\n"
            )
        lines.extend(["\n", "### Script review\n", "\n"])
        captions = cast(list[str], card["caption_lines"])
        if captions:
            for caption in captions:
                lines.append(f"- {caption}\n")
        else:
            lines.append("- (no captions)\n")
        lines.append("\n")
    return "".join(lines)


def _artifact_tree(ir: ConcreteIR) -> dict[str, str]:
    cards = scene_cards(ir)
    return {
        "captions.md": _captions_markdown(ir.captions),
        "scene-cards.json": f"{canonical_json(cards)}\n",
        "script.md": _script_markdown(cards),
        "storyboard.md": storyboard_markdown(ir),
    }


def _captions_markdown(captions: list[Caption]) -> str:
    lines = ["# Captions\n", "\n"]
    if not captions:
        lines.append("(none)\n")
        return "".join(lines)
    for caption in _sorted_captions(captions):
        lines.append(f"- `{caption.start_f}–{caption.end_f}` {caption.text}\n")
    return "".join(lines)


def _script_markdown(cards: list[dict[str, object]]) -> str:
    lines = ["# Script review\n", "\n"]
    for card in cards:
        lines.append(f"## {card['scene_id']}\n\n")
        captions = cast(list[str], card["caption_lines"])
        if captions:
            for caption in captions:
                lines.append(f"- {caption}\n")
        else:
            lines.append("- (no captions)\n")
        lines.append("\n")
    return "".join(lines)


def _caption_scene(
    caption: Caption, scene_ranges: dict[str, tuple[int, int]]
) -> str | None:
    for scene, (start_f, end_f) in scene_ranges.items():
        if start_f <= caption.start_f < max(end_f, start_f + 1):
            return scene
        if caption.start_f < start_f and caption.end_f > start_f:
            return scene
    if not scene_ranges:
        return None
    return min(
        scene_ranges,
        key=lambda scene: abs(caption.start_f - scene_ranges[scene][0]),
    )


def _object_data(obj: ResolvedObject) -> dict[str, object]:
    return {
        "id": obj.id,
        "primitive": obj.primitive,
        "style_ref": obj.style_ref,
        "text": display_text(obj),
        "w": obj.box.w,
        "h": obj.box.h,
        "x": obj.box.x,
        "y": obj.box.y,
        "z": obj.z,
    }


def _keyframe_data(keyframe: Keyframe) -> dict[str, object]:
    return {
        "easing": keyframe.easing,
        "end_f": keyframe.end_f,
        "kind": keyframe.kind,
        "object_id": keyframe.object_id,
        "start_f": keyframe.start_f,
    }


def _scene_id(object_id: str) -> str:
    return object_id.split(".", 1)[0]


def _sorted_objects(objects: list[ResolvedObject]) -> list[ResolvedObject]:
    return sorted(objects, key=lambda item: (item.z, item.id))


def _sorted_keyframes(keyframes: list[Keyframe]) -> list[Keyframe]:
    return sorted(keyframes, key=lambda item: (item.start_f, item.end_f, item.object_id, item.kind))


def _sorted_captions(captions: list[Caption]) -> list[Caption]:
    return sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))


def _seconds(frame: int, fps: int) -> float:
    return round(frame / fps, 4)


__all__ = [
    "REVIEW_MANIFEST_FILENAME",
    "emit",
    "materialize_source",
    "review_manifest",
    "scene_cards",
    "source_for",
    "source_tree",
    "storyboard_markdown",
]
