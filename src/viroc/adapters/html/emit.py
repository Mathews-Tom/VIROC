"""Pure byte-deterministic HTML source emitter."""

from __future__ import annotations

import html

from viroc.adapters import _palette
from viroc.adapters._text import display_text
from viroc.adapters.html.templates import BASE_CSS, RUNTIME_SCRIPT, SOURCE_HEADER
from viroc.core import BuildArtifact, BuildContext, artifact_from_text, canonical_json
from viroc.ir import Caption, ConcreteIR, Keyframe, ResolvedObject

_ADAPTER_SOURCE_VERSION = "html-source-v0.2"


def emit(ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR into deterministic HTML/CSS/JS without I/O."""
    _ = ctx
    return artifact_from_text("source", source_for(ir))


def source_for(ir: ConcreteIR) -> str:
    """Render the self-contained HTML source for ``ir`` as a pure string."""
    width, height = ir.resolution
    sections = [
        SOURCE_HEADER,
        f"<!-- viroc-adapter-source-version: {_ADAPTER_SOURCE_VERSION} -->\n",
        BASE_CSS,
        "</head>\n<body>\n",
        (
            f'<main id="scene" role="img" aria-label="VIROC scene" '
            f'data-fps="{ir.fps}" data-total-frames="{_total_frames(ir)}" '
            f'style="width:{width}px;height:{height}px">\n'
        ),
        '  <div class="layer" id="object-layer">\n',
        _object_markup(ir.objects),
        "  </div>\n",
        '  <div class="caption" id="caption" aria-live="off"></div>\n',
        "</main>\n",
        _runtime_block(ir),
        "</body>\n</html>\n",
    ]
    return "".join(sections)


def _object_markup(objects: list[ResolvedObject]) -> str:
    lines: list[str] = []
    indexed = list(enumerate(objects))
    for _, obj in sorted(indexed, key=lambda item: (item[1].z, item[0])):
        lines.append(_object_element(obj))
    return "".join(lines)


def _object_element(obj: ResolvedObject) -> str:
    style_class = _style_class(obj.style_ref)
    box = obj.box
    common = (
        f'    <div class="object primitive-{obj.primitive} style-{style_class}" '
        f'data-object-id="{html.escape(obj.id, quote=True)}" '
        f'style="left:{_fmt(box.x)}px;top:{_fmt(box.y)}px;width:{_fmt(box.w)}px;'
        f'height:{_fmt(box.h)}px;z-index:{obj.z};{_css_vars(obj.style_ref)}">'
    )
    if obj.primitive == "rect":
        body = "</div>\n"
    elif obj.primitive == "text":
        body = f"<span>{html.escape(display_text(obj))}</span></div>\n"
    elif obj.primitive == "code":
        body = f"<pre><code>{html.escape(display_text(obj))}</code></pre></div>\n"
    elif obj.primitive == "formula":
        body = f"<div>{html.escape(display_text(obj))}</div></div>\n"
    elif obj.primitive == "icon":
        body = f"<div>{html.escape(_icon_glyph(obj))}</div></div>\n"
    elif obj.primitive == "arrow":
        body = (
            f'<svg viewBox="0 0 {_fmt(box.w)} {_fmt(box.h)}" preserveAspectRatio="none" '
            'aria-hidden="true">'
            f'<line x1="0" y1="{_fmt(box.h / 2)}" x2="{_fmt(box.w - max(box.h, 12.0))}" '
            f'y2="{_fmt(box.h / 2)}" stroke-width="{_fmt(max(box.h, 2.0))}" />'
            f'<path d="M {_fmt(box.w - max(box.h, 12.0))} 0 '
            f'L {_fmt(box.w)} {_fmt(box.h / 2)} '
            f'L {_fmt(box.w - max(box.h, 12.0))} {_fmt(box.h)} Z" />'
            '</svg></div>\n'
        )
    else:
        raise ValueError(f"HTML emitter cannot lower primitive {obj.primitive!r}")
    return common + body


def _runtime_block(ir: ConcreteIR) -> str:
    data = {
        "fps": ir.fps,
        "resolution": list(ir.resolution),
        "total_frames": _total_frames(ir),
        "objects": [_object_data(obj) for obj in ir.objects],
        "keyframes": [_keyframe_data(keyframe) for keyframe in _sorted_keyframes(ir.keyframes)],
        "captions": [_caption_data(caption) for caption in _sorted_captions(ir.captions)],
    }
    payload = canonical_json(data)
    return RUNTIME_SCRIPT.replace("__VIROC_DATA__", payload) + "\n"


def _object_data(obj: ResolvedObject) -> dict[str, object]:
    return {
        "id": obj.id,
        "primitive": obj.primitive,
        "style_ref": obj.style_ref,
        "z": obj.z,
        "length": obj.box.w,
    }


def _keyframe_data(keyframe: Keyframe) -> dict[str, object]:
    return {
        "object_id": keyframe.object_id,
        "kind": keyframe.kind,
        "start_f": keyframe.start_f,
        "end_f": keyframe.end_f,
        "easing": keyframe.easing,
    }


def _caption_data(caption: Caption) -> dict[str, object]:
    return {
        "text": caption.text,
        "start_f": caption.start_f,
        "end_f": caption.end_f,
    }


def _sorted_keyframes(keyframes: list[Keyframe]) -> list[Keyframe]:
    return sorted(keyframes, key=lambda item: (item.start_f, item.end_f, item.object_id, item.kind))


def _sorted_captions(captions: list[Caption]) -> list[Caption]:
    return sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))


def _total_frames(ir: ConcreteIR) -> int:
    end_frames = [keyframe.end_f for keyframe in ir.keyframes]
    end_frames.extend(caption.end_f for caption in ir.captions)
    return max(end_frames, default=0)


def _css_vars(style_ref: str) -> str:
    if style_ref.startswith("edge."):
        return f"--color:{_palette.edge_color(style_ref)}"
    if style_ref in ("label", "showcase.title"):
        return f"--color:{_palette.LABEL_COLOR}"
    fill, stroke = _palette.box_style(style_ref)
    return f"--fill-color:{fill};--stroke-color:{stroke}"


def _style_class(style_ref: str) -> str:
    return style_ref.replace(".", "-").replace("_", "-")


def _icon_glyph(obj: ResolvedObject) -> str:
    text = display_text(obj)
    initials = [part[0] for part in text.split() if part]
    if not initials:
        return "•"
    return "".join(initials[:2]).upper()


def _fmt(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


__all__ = ["emit", "source_for"]
