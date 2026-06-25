"""HTML renderer adapter: pure deterministic emit with render gated until PR-5."""

from __future__ import annotations

from collections.abc import Iterable

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.html.emit import emit, source_for
from viroc.core import BuildArtifact, BuildContext, Diagnostic, DiagnosticClass, code
from viroc.ir import Caption, ConcreteIR

VIR_RENDER_UNAVAILABLE = code(DiagnosticClass.RENDERER, 39)


class RenderEnvironmentError(RuntimeError):
    """Raised when the HTML render path is unavailable in this stack slice."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("html render environment is unavailable")
        self.diagnostics = diagnostics


id = "html"
version = "0.1"
source_filename = "scene.html"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """Return the explicit gate until the impure browser render slice lands."""
    _ = ctx
    return [
        Diagnostic(
            code=VIR_RENDER_UNAVAILABLE,
            message='renderer "html" does not provide browser render in this revision',
            help='use "viroc compile --backend html" for deterministic source, or apply the render slice',
        )
    ]


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(id, capabilities, ir)


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: Iterable[Caption] = (),
) -> BuildArtifact:
    """Fail loudly until the impure browser render implementation lands."""
    _ = (source, captions)
    diagnostics = check_environment(ctx)
    raise RenderEnvironmentError(diagnostics)


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_RENDER_UNAVAILABLE",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "RenderEnvironmentError",
    "capabilities",
    "check_environment",
    "emit",
    "id",
    "render",
    "source_filename",
    "source_for",
    "supports",
    "version",
]
