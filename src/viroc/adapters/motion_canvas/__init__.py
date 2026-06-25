"""Motion Canvas renderer adapter: deterministic TypeScript generator emission."""

from __future__ import annotations

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.motion_canvas.emit import (
    emit,
    materialize_source,
    project_tree,
    source_for,
    source_tree,
)
from viroc.adapters.motion_canvas.render import (
    VIR_MISSING_FFMPEG,
    VIR_MISSING_FFPROBE,
    VIR_MISSING_MOTION_CANVAS,
    VIR_MISSING_NODE,
    VIR_MISSING_NPX,
    VIR_TOOL_PROBE_FAILED,
    RenderCommandError,
    RenderEnvironmentError,
    captions_to_srt,
    check_environment,
    motion_canvas_version,
    render,
)
from viroc.core import Diagnostic
from viroc.ir import ConcreteIR

id = "motion_canvas"
version = "0.1"
source_filename = "project.json"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)
tool_version = motion_canvas_version


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(
        id,
        capabilities,
        ir,
        primitive_fallback_backends=("html", "remotion", "manim"),
    )


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "RenderCommandError",
    "RenderEnvironmentError",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_MOTION_CANVAS",
    "VIR_MISSING_NODE",
    "VIR_MISSING_NPX",
    "VIR_TOOL_PROBE_FAILED",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "captions_to_srt",
    "check_environment",
    "emit",
    "id",
    "materialize_source",
    "motion_canvas_version",
    "project_tree",
    "render",
    "source_filename",
    "source_for",
    "source_tree",
    "supports",
    "tool_version",
    "version",
]
