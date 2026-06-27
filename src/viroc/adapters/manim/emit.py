"""Pure byte-deterministic Manim source emitter."""

from __future__ import annotations

import json
from collections import defaultdict

from viroc.adapters._text import display_text
from viroc.adapters.manim.templates import GEOMETRY_HELPERS, SOURCE_HEADER, STYLE_BLOCK
from viroc.core import BuildArtifact, BuildContext, artifact_from_text
from viroc.ir import ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "manim-source-v0.1"
_FRAME_HEIGHT = 8.0


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
        STYLE_BLOCK,
        GEOMETRY_HELPERS,
        "class VirocScene(Scene):\n",
        "    def construct(self) -> None:\n",
        "        self.camera.background_color = _BACKGROUND\n",
        "        objects = {}\n",
        _object_lines(ir.objects),
        _timeline_lines(ir.keyframes),
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
    args = ", ".join(
        [
            _fmt(box.x),
            _fmt(box.y),
            _fmt(box.w),
            _fmt(box.h),
            _string(obj.style_ref),
        ]
    )
    if obj.primitive == "rect":
        return f"_rect({args})"
    if obj.primitive == "text":
        return f"_text({_string(display_text(obj))}, {args})"
    if obj.primitive == "arrow":
        return f"_arrow({args})"
    raise ValueError(f"Manim emitter cannot lower primitive {obj.primitive!r}")


def _timeline_lines(keyframes: list[Keyframe]) -> str:
    if not keyframes:
        return "        self.add(*objects.values())\n"

    lines: list[str] = ["        timeline_f = 0\n"]
    for group in _keyframe_groups(keyframes):
        start_f, end_f, members = group
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
        lines.append(f"        timeline_f = {end_f}\n")
    return "".join(lines)


def _keyframe_groups(
    keyframes: list[Keyframe],
) -> list[tuple[int, int, list[Keyframe]]]:
    grouped: dict[tuple[int, int], list[Keyframe]] = defaultdict(list)
    for keyframe in sorted(
        keyframes, key=lambda item: (item.start_f, item.end_f, item.object_id)
    ):
        grouped[(keyframe.start_f, keyframe.end_f)].append(keyframe)
    return [(start, end, members) for (start, end), members in grouped.items()]


def _animation_expression(keyframe: Keyframe) -> str:
    obj = f"objects[{_string(keyframe.object_id)}]"
    if keyframe.kind == "fade_in":
        return f"FadeIn({obj}, rate_func=_rate_func({_string(keyframe.easing)}))"
    if keyframe.kind == "draw":
        return f"Create({obj}, rate_func=_rate_func({_string(keyframe.easing)}))"
    if keyframe.kind == "highlight":
        return (
            f"Indicate({obj}, color=\"#FBBF24\", "
            f"rate_func=_rate_func({_string(keyframe.easing)}))"
        )
    if keyframe.kind == "fade_out":
        return f"FadeOut({obj}, rate_func=_rate_func({_string(keyframe.easing)}))"
    raise ValueError(f"Manim emitter cannot lower keyframe kind {keyframe.kind!r}")


def _fmt(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


__all__ = ["emit", "source_for"]
