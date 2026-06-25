"""Renderer adapter registry behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from viroc.adapters import RendererAdapter
from viroc.adapters.registry import (
    VIR_DUPLICATE_BACKEND,
    VIR_UNKNOWN_BACKEND,
    AdapterRegistry,
    DuplicateBackendError,
    UnknownBackendError,
)
from viroc.core import BuildArtifact, BuildContext, BuildPaths, Diagnostic, artifact_from_text
from viroc.ir import ConcreteIR


class _Adapter:
    def __init__(self, adapter_id: str) -> None:
        self.id = adapter_id
        self.version = "0.1"
        self.capabilities = frozenset({"rect"})

    def check_environment(self, ctx: BuildContext) -> list[Diagnostic]:
        _ = ctx
        return []

    def supports(self, ir: ConcreteIR) -> list[Diagnostic]:
        _ = ir
        return []

    def emit(self, ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
        _ = (ir, ctx)
        return artifact_from_text("source", "scene = None\n")

    def render(self, source: BuildArtifact, ctx: BuildContext) -> BuildArtifact:
        _ = (source, ctx)
        return artifact_from_text("video", "video-bytes")


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-adapter-registry-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _ir() -> ConcreteIR:
    return ConcreteIR(fps=30, resolution=(1920, 1080), objects=[], keyframes=[], captions=[])


def test_registry_registers_gets_and_lists_ids_in_sorted_order() -> None:
    registry = AdapterRegistry()
    alpha = _Adapter("alpha")
    beta = _Adapter("beta")

    registry.register(beta)
    registry.register(alpha)

    assert isinstance(alpha, RendererAdapter)
    assert registry.get("alpha") is alpha
    assert registry.require("beta") is beta
    assert registry.ids() == ("alpha", "beta")


def test_registry_returns_none_for_unknown_backend_from_get() -> None:
    registry = AdapterRegistry([_Adapter("manim")])

    assert registry.get("html") is None


def test_registry_raises_unknown_backend_with_available_ids() -> None:
    registry = AdapterRegistry([_Adapter("manim"), _Adapter("static")])

    with pytest.raises(UnknownBackendError) as exc_info:
        registry.require("html")

    diagnostic = exc_info.value.diagnostic
    assert diagnostic.code == VIR_UNKNOWN_BACKEND
    assert diagnostic.message == 'renderer backend "html" is not registered'
    assert diagnostic.help == 'available backends: "manim", "static"'


def test_registry_raises_duplicate_backend_with_registered_refs() -> None:
    registry = AdapterRegistry([_Adapter("manim")])

    with pytest.raises(DuplicateBackendError) as exc_info:
        registry.register(_Adapter("manim"))

    diagnostic = exc_info.value.diagnostic
    assert diagnostic.code == VIR_DUPLICATE_BACKEND
    assert diagnostic.message == 'renderer backend "manim" is already registered'
    assert "existing adapter: tests.unit.test_adapter_registry._Adapter" in diagnostic.help
    assert "duplicate adapter: tests.unit.test_adapter_registry._Adapter" in diagnostic.help


def test_registry_keeps_adapter_contract_intact() -> None:
    registry = AdapterRegistry([_Adapter("manim")])
    adapter: RendererAdapter = registry.require("manim")

    artifact = adapter.emit(_ir(), _ctx())

    assert artifact.kind == "source"
    assert artifact.digest.startswith("sha256:")
