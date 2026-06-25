"""Renderer adapter contract tests (M9, PR-1)."""

from __future__ import annotations

from pathlib import Path

from viroc.adapters import CapabilityManifest, RendererAdapter
from viroc.core import BuildArtifact, BuildContext, BuildPaths, Diagnostic, artifact_from_text
from viroc.ir import ConcreteIR


class _Adapter:
    """Tiny concrete adapter proving the public Protocol shape."""

    id = "test"
    version = "0.1"
    capabilities = CapabilityManifest(primitives=frozenset({"rect"}), animations=frozenset())

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
    root = Path("/tmp/viroc-adapter-contract-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _ir() -> ConcreteIR:
    return ConcreteIR(fps=30, resolution=(1920, 1080), objects=[], keyframes=[], captions=[])


def test_renderer_adapter_protocol_is_runtime_checkable() -> None:
    adapter = _Adapter()

    assert isinstance(adapter, RendererAdapter)
    assert adapter.id == "test"
    assert adapter.version == "0.1"
    assert adapter.capabilities.primitives == frozenset({"rect"})


def test_renderer_adapter_emit_contract_returns_source_artifact() -> None:
    adapter: RendererAdapter = _Adapter()

    artifact = adapter.emit(_ir(), _ctx())

    assert artifact.kind == "source"
    assert artifact.data == b"scene = None\n"
    assert artifact.digest.startswith("sha256:")


def test_renderer_adapter_render_contract_returns_video_artifact() -> None:
    adapter: RendererAdapter = _Adapter()

    artifact = adapter.render(artifact_from_text("source", "scene = None\n"), _ctx())

    assert artifact.kind == "video"
    assert artifact.data == b"video-bytes"
    assert artifact.digest.startswith("sha256:")
