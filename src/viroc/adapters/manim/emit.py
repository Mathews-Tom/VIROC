"""Pure byte-deterministic Manim source emitter."""

from __future__ import annotations

import json
from collections import defaultdict

from viroc.adapters import _palette
from viroc.adapters._text import display_text
from viroc.adapters.manim.templates import HELPERS, SOURCE_HEADER
from viroc.core import BuildArtifact, BuildContext, artifact_from_text
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "manim-source-v0.3"
_FRAME_HEIGHT = 8.0

DEGRADED_PRIMITIVES: dict[str, str] = {"code": "rect", "formula": "rect"}
"""Above-floor primitives Manim renders as their floor primitive (design §19)."""


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into deterministic ``scene.py`` bytes without I/O."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Render the Manim ``scene.py`` source for ``ir`` as a pure string."""
    frame_width = _FRAME_HEIGHT * ir.resolution[0] / ir.resolution[1]
    sections: list[str] = [
        SOURCE_HEADER,
        f"# viroc-adapter-source-version: {_ADAPTER_SOURCE_VERSION}\n",
        f"config.pixel_width = {ir.resolution[0]}\n",
        f"config.pixel_height = {ir.resolution[1]}\n",
        f"config.frame_width = {_fmt(frame_width)}\n",
        f"config.frame_height = {_fmt(_FRAME_HEIGHT)}\n",
        f"config.frame_rate = {ir.fps}\n\n",
        HELPERS,
        "class VirocScene(Scene):\n",
        "    def construct(self) -> None:\n",
        "        self.camera.background_color = _BACKGROUND\n",
        "        objects = {}\n",
        _object_lines(ir.objects),
        _timeline_lines(ir.keyframes, ir.captions),
    ]
    return "".join(sections)


def _object_lines(objects: list[ResolvedObject]) -> str:
    if not objects:
        return "        return\n"
    lines: list[str] = []
    indexed = list(enumerate(objects))
    for _, obj in sorted(indexed, key=lambda item: (item[1].z, item[0])):
        lines.append(f"        objects[{_string(obj.id)}] = {_object_expression(obj)}\n")
    lines.append("\n")
    return "".join(lines)


def _object_expression(obj: ResolvedObject) -> str:
    box = obj.box
    geom = ", ".join([_fmt(box.x), _fmt(box.y), _fmt(box.w), _fmt(box.h)])
    primitive = DEGRADED_PRIMITIVES.get(obj.primitive, obj.primitive)
    if primitive == "rect":
        fill, stroke = _palette.box_style(obj.style_ref)
        return f"_rect({geom}, {_string(fill)}, {_string(stroke)})"
    if primitive == "text":
        style = _palette.text_style(obj.style_ref)
        return (
            f"_text({_string(display_text(obj))}, {geom}, {_string(style.color)}, "
            f"{style.size}, {style.bold}, {style.mono}, {_string(style.align)})"
        )
    if primitive == "arrow":
        return f"_arrow({geom}, {_string(_palette.edge_color(obj.style_ref))})"
    raise ValueError(f"Manim emitter cannot lower primitive {obj.primitive!r}")


def _timeline_lines(keyframes: list[Keyframe], captions: list[Caption]) -> str:
    sorted_captions = sorted(captions, key=lambda c: (c.start_f, c.end_f, c.text))
    if not keyframes:
        lines = ["        self.add(*objects.values())\n"]
        if sorted_captions:
            lines.append(f"        self.add(_caption({_string(sorted_captions[0].text)}))\n")
        return "".join(lines)

    lines: list[str] = ["        timeline_f = 0\n"]
    for start_f, end_f, members in _keyframe_groups(keyframes):
        caption = _active_caption(sorted_captions, start_f)
        if caption is not None:
            lines.append(f"        caption = _caption({_string(caption)})\n")
            lines.append("        self.add(caption)\n")
        if start_f > 0:
            lines.append(
                "        if timeline_f < "
                f"{start_f}:\n"
                f"            self.wait(({start_f} - timeline_f) / config.frame_rate)\n"
            )
        lines.append("        self.play(\n")
        for member in members:
            lines.append(f"            {_animation_expression(member)},\n")
        lines.append(
            f"            run_time={_fmt(float(end_f - start_f))} / config.frame_rate,\n"
        )
        lines.append("        )\n")
        if caption is not None:
            lines.append("        self.remove(caption)\n")
        lines.append(f"        timeline_f = {end_f}\n")
    return "".join(lines)


def _active_caption(captions: list[Caption], frame: int) -> str | None:
    for caption in captions:
        if caption.start_f <= frame < caption.end_f:
            return caption.text
    return None


def _keyframe_groups(
    keyframes: list[Keyframe],
) -> list[tuple[int, int, list[Keyframe]]]:
    grouped: dict[tuple[int, int], list[Keyframe]] = defaultdict(list)
    for keyframe in keyframes:
        grouped[(keyframe.start_f, keyframe.end_f)].append(keyframe)
    ordered = sorted(grouped)
    return [(start, end, grouped[(start, end)]) for start, end in ordered]


def _animation_expression(keyframe: Keyframe) -> str:
    obj = f"objects[{_string(keyframe.object_id)}]"
    rate = f"rate_func=_rate_func({_string(keyframe.easing)})"
    if keyframe.kind == "fade_in":
        return f"FadeIn({obj}, {rate})"
    if keyframe.kind == "fade_out":
        return f"FadeOut({obj}, {rate})"
    if keyframe.kind == "draw":
        return f"Create({obj}, {rate})"
    if keyframe.kind == "highlight":
        return f'Indicate({obj}, color="#FDE68A", scale_factor=1.06, {rate})'
    if keyframe.kind == "move":
        return f"FadeIn({obj}, {rate})"
    raise ValueError(f"Manim emitter cannot lower keyframe kind {keyframe.kind!r}")


def _fmt(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


__all__ = ["DEGRADED_PRIMITIVES", "emit", "source_for"]
