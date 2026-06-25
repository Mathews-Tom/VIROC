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
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "emit",
    "id",
    "materialize_source",
    "project_tree",
    "source_filename",
    "source_for",
    "source_tree",
    "supports",
    "version",
]
