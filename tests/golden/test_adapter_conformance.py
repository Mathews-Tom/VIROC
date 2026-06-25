"""Shared renderer-adapter conformance checks for built-in backends."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import viroc.adapters.manim as manim
from viroc.adapters import CapabilityManifest, RendererAdapter
from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    support_diagnostics,
)
from viroc.adapters.registry import builtin_registry
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import (
    BuildArtifact,
    BuildContext,
    BuildPaths,
    Diagnostic,
    artifact_from_text,
    hash_bytes,
)
from viroc.ir import Box, Caption, ConcreteIR, Keyframe, ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_scene.py"


class _FakeAdapter:
    id = "fake"
    version = "0.1-test"
    capabilities = CapabilityManifest(
        primitives={"rect"},
        animations={"fade_in"},
        features={"programmatic_video": "partial"},
    )

    def check_environment(self, ctx: BuildContext) -> list[Diagnostic]:
        _ = ctx
        return []

    def supports(self, ir: ConcreteIR) -> list[Diagnostic]:
        return support_diagnostics(self.id, self.capabilities, ir)

    def emit(self, ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
        _ = ctx
        return artifact_from_text("source", f"# fake-renderer\n# fps={ir.fps}\n")

    def render(
        self,
        source: BuildArtifact,
        ctx: BuildContext,
        *,
        captions: Iterable[Caption] = (),
    ) -> BuildArtifact:
        _ = (source, ctx, tuple(captions))
        return artifact_from_text("video", "fake-video")


def _compile() -> CompileState:
    doc = load_document(_FIXTURE)
    ir, diagnostics = validate_schema(doc)
    assert ir is not None
    assert diagnostics == []
    ctx = _ctx()
    state = run_pipeline(ir, ctx)
    assert state.diagnostics == []
    return state


def _ctx(root: Path = Path("/tmp/viroc-adapter-conformance-test")) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _object(
    object_id: str,
    primitive: str,
    *,
    style_ref: str = "node.process",
) -> ResolvedObject:
    return ResolvedObject.model_validate(
        {
            "id": object_id,
            "primitive": primitive,
            "box": Box(x=0.0, y=0.0, w=100.0, h=50.0).model_dump(),
            "style_ref": style_ref,
        }
    )


def _supported_fake_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[_object("demo.panel", "rect")],
        keyframes=[
            Keyframe(
                object_id="demo.panel",
                kind="fade_in",
                start_f=0,
                end_f=24,
                easing="linear",
            )
        ],
        captions=[],
    )


def _unsupported_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[_object("demo.panel", "icon")],
        keyframes=[
            Keyframe(
                object_id="demo.panel",
                kind="move",
                start_f=0,
                end_f=24,
                easing="linear",
            )
        ],
        captions=[],
    )


def _assert_adapter_conformance(
    adapter: RendererAdapter,
    *,
    supported_ir: ConcreteIR,
    unsupported_ir: ConcreteIR,
    expected_hash: str | None = None,
) -> None:
    ctx = _ctx()

    assert isinstance(adapter, RendererAdapter)
    env_diagnostics = adapter.check_environment(ctx)
    assert all(isinstance(diagnostic, Diagnostic) for diagnostic in env_diagnostics)
    assert all(diagnostic.code.startswith("VIR5") for diagnostic in env_diagnostics)
    assert adapter.supports(supported_ir) == []

    unsupported = adapter.supports(unsupported_ir)
    assert [diagnostic.code for diagnostic in unsupported] == [
        VIR_UNSUPPORTED_PRIMITIVE,
        VIR_UNSUPPORTED_ANIMATION,
    ]

    first = adapter.emit(supported_ir, ctx)
    second = adapter.emit(supported_ir, ctx)
    assert first.kind == second.kind == "source"
    assert first.digest == second.digest
    assert first.data == second.data
    assert first.digest.startswith("sha256:")
    if expected_hash is not None:
        assert first.digest == expected_hash


def test_manim_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        manim,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_ir(),
        expected_hash=hash_bytes(_GOLDEN.read_bytes()),
    )


def test_fake_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        _FakeAdapter(),
        supported_ir=_supported_fake_ir(),
        unsupported_ir=_unsupported_ir(),
    )


def test_registry_dispatch_preserves_manim_emit_hash() -> None:
    registry = builtin_registry()
    assert registry.ids() == ("manim",)
    adapter = registry.require("manim")
    concrete = _compile().concrete
    ctx = _ctx()

    direct = manim.emit(concrete, ctx)
    dispatched = adapter.emit(concrete, ctx)

    assert dispatched.digest == direct.digest == hash_bytes(_GOLDEN.read_bytes())
    assert dispatched.data == direct.data
