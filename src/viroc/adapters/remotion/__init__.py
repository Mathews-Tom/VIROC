"""Remotion renderer adapter: deterministic emit and env-gated CLI render."""

from __future__ import annotations

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.remotion.emit import (
    emit,
    materialize_source,
    project_tree,
    source_for,
    source_tree,
)
from viroc.adapters.remotion.render import (
    VIR_MISSING_FFMPEG,
    VIR_MISSING_FFPROBE,
    VIR_MISSING_NODE,
    VIR_MISSING_NPX,
    VIR_MISSING_REMOTION,
    VIR_TOOL_PROBE_FAILED,
    RenderCommandError,
    RenderEnvironmentError,
    captions_to_srt,
    check_environment,
    remotion_version,
    render,
)
from viroc.core import Diagnostic
from viroc.ir import ConcreteIR

id = "remotion"
version = "0.1"
source_filename = "project.json"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)
tool_version = remotion_version


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(
        id,
        capabilities,
        ir,
        primitive_fallback_backends=("html", "manim"),
    )


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "RenderCommandError",
    "RenderEnvironmentError",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_NODE",
    "VIR_MISSING_NPX",
    "VIR_MISSING_REMOTION",
    "VIR_TOOL_PROBE_FAILED",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "captions_to_srt",
    "check_environment",
    "emit",
    "id",
    "materialize_source",
    "project_tree",
    "render",
    "remotion_version",
    "source_filename",
    "source_for",
    "source_tree",
    "supports",
    "tool_version",
    "version",
]
