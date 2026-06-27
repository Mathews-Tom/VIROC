"""Manim renderer adapter: pure byte-deterministic emit and impure render."""

from __future__ import annotations

from viroc.adapters.capabilities import (
    VIR_DEGRADED_PRIMITIVE,
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.manim.emit import DEGRADED_PRIMITIVES, emit, source_for
from viroc.adapters.manim.render import (
    VIR_MISSING_FFMPEG,
    VIR_MISSING_FFPROBE,
    VIR_MISSING_MANIM,
    VIR_TOOL_PROBE_FAILED,
    RenderCommandError,
    RenderEnvironmentError,
    captions_to_srt,
    check_environment,
    manim_version,
    render,
)
from viroc.core import Diagnostic
from viroc.ir import ConcreteIR

id = "manim"
version = "0.1"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
    degradations=DEGRADED_PRIMITIVES,
)
tool_version = manim_version

def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(
        id,
        capabilities,
        ir,
        primitive_fallback_backend="html",
    )


__all__ = [
    "DEGRADED_PRIMITIVES",
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_DEGRADED_PRIMITIVE",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "RenderCommandError",
    "RenderEnvironmentError",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_MANIM",
    "VIR_TOOL_PROBE_FAILED",
    "capabilities",
    "captions_to_srt",
    "check_environment",
    "emit",
    "id",
    "manim_version",
    "tool_version",
    "render",
    "source_for",
    "supports",
    "version",
]
