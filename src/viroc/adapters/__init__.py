"""Renderer adapter contract: consume Concrete IR and emit backend source."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from viroc.adapters.capabilities import CapabilityManifest
from viroc.core import BuildArtifact, BuildContext, Diagnostic
from viroc.ir import ConcreteIR


@runtime_checkable
class RendererAdapter(Protocol):
    """Renderer-backend contract for lowering source and rendering artifacts."""

    id: str
    version: str
    capabilities: CapabilityManifest

    def check_environment(self, ctx: BuildContext) -> list[Diagnostic]:
        """Return environment diagnostics for impure render dependencies."""
        ...

    def supports(self, ir: ConcreteIR) -> list[Diagnostic]:
        """Return diagnostics for Concrete IR features this backend cannot render."""
        ...

    def emit(self, ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
        """Lower Concrete IR to byte-deterministic backend source without I/O."""
        ...

    def render(self, source: BuildArtifact, ctx: BuildContext) -> BuildArtifact:
        """Invoke the backend and return the rendered video artifact."""
        ...


__all__ = ["CapabilityManifest", "RendererAdapter"]
