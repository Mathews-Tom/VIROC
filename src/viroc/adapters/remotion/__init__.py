"""Remotion source emitter: deterministic React/TypeScript project generation."""

from __future__ import annotations

from collections.abc import Iterable

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
from viroc.core import BuildArtifact, BuildContext, Diagnostic
from viroc.ir import Caption, ConcreteIR

id = "remotion"
version = "0.1"
source_filename = "project.json"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """PR-5 fills the impure Remotion toolchain checks."""
    _ = ctx
    return []


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(
        id,
        capabilities,
        ir,
        primitive_fallback_backends=("html", "manim"),
    )


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: Iterable[Caption] = (),
) -> BuildArtifact:
    """PR-5 fills the impure Remotion render path."""
    _ = (source, ctx, tuple(captions))
    raise NotImplementedError("Remotion render is added in the PR-5 branch")


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "check_environment",
    "emit",
    "id",
    "materialize_source",
    "project_tree",
    "render",
    "source_filename",
    "source_for",
    "source_tree",
    "supports",
    "version",
]
