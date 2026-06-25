"""Manim renderer adapter: pure byte-deterministic emit and impure render."""

from __future__ import annotations

from viroc.adapters.manim.emit import emit, source_for
from viroc.core import BuildContext, Diagnostic, DiagnosticClass, code
from viroc.ir import ConcreteIR

id = "manim"
version = "0.1"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = SUPPORTED_PRIMITIVES | SUPPORTED_ANIMATIONS

VIR_UNSUPPORTED_PRIMITIVE = code(DiagnosticClass.RENDERER, 31)
VIR_UNSUPPORTED_ANIMATION = code(DiagnosticClass.RENDERER, 32)


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """M9 emit is pure; impure Manim/FFmpeg probing arrives with render()."""
    _ = ctx
    return []


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    diagnostics: list[Diagnostic] = []
    for obj in ir.objects:
        if obj.primitive not in SUPPORTED_PRIMITIVES:
            diagnostics.append(
                Diagnostic(
                    code=VIR_UNSUPPORTED_PRIMITIVE,
                    message=f'renderer "manim" does not support primitive "{obj.primitive}"',
                    help=(
                        'use renderer "html", or provide a fallback image asset '
                        f'for object "{obj.id}"'
                    ),
                )
            )
    for keyframe in ir.keyframes:
        if keyframe.kind not in SUPPORTED_ANIMATIONS:
            diagnostics.append(
                Diagnostic(
                    code=VIR_UNSUPPORTED_ANIMATION,
                    message=(
                        f'renderer "manim" does not support animation "{keyframe.kind}"'
                    ),
                    help=(
                        f'lower object "{keyframe.object_id}" to a supported animation '
                        "or select a backend that supports this keyframe kind"
                    ),
                )
            )
    return diagnostics


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "check_environment",
    "emit",
    "id",
    "source_for",
    "supports",
    "version",
]
