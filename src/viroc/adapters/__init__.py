"""Renderer adapter contract: consume Concrete IR and emit backend source."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from viroc.core import BuildArtifact, BuildContext, Diagnostic
from viroc.ir import ConcreteIR


@runtime_checkable
class RendererAdapter(Protocol):
    """Pure renderer-backend contract for lowering Concrete IR to source."""

    id: str
    version: str
    capabilities: frozenset[str]

    def check_environment(self, ctx: BuildContext) -> list[Diagnostic]:
        """Return environment diagnostics for impure render dependencies."""
        ...

    def supports(self, ir: ConcreteIR) -> list[Diagnostic]:
        """Return diagnostics for Concrete IR features this backend cannot render."""
        ...

    def emit(self, ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
        """Lower Concrete IR to byte-deterministic backend source without I/O."""
        ...


__all__ = ["RendererAdapter"]
