"""HTML renderer adapter: pure deterministic emit and env-gated browser render."""

from __future__ import annotations

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.html.emit import emit, source_for
from viroc.adapters.html.render import (
    VIR_MISSING_BROWSER,
    VIR_MISSING_FFMPEG,
    VIR_MISSING_FFPROBE,
    VIR_MISSING_NODE,
    VIR_TOOL_PROBE_FAILED,
    RenderCommandError,
    RenderEnvironmentError,
    browser_version,
    captions_to_srt,
    check_environment,
    render,
)
from viroc.core import Diagnostic
from viroc.ir import ConcreteIR

id = "html"
version = "0.1"
source_filename = "scene.html"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)
tool_version = browser_version


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(id, capabilities, ir)


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_MISSING_BROWSER",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_NODE",
    "VIR_TOOL_PROBE_FAILED",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "RenderCommandError",
    "RenderEnvironmentError",
    "browser_version",
    "capabilities",
    "captions_to_srt",
    "check_environment",
    "emit",
    "id",
    "render",
    "source_filename",
    "source_for",
    "supports",
    "tool_version",
    "version",
]
