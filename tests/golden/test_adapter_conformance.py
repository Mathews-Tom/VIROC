"""Shared renderer-adapter conformance checks for built-in backends."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import viroc.adapters.html as html_adapter
import viroc.adapters.image_sequence as image_sequence_adapter
import viroc.adapters.manim as manim
import viroc.adapters.motion_canvas as motion_canvas_adapter
import viroc.adapters.remotion as remotion_adapter
import viroc.adapters.static_storyboard as static_storyboard_adapter
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
_MANIM_GOLDEN = _HERE / "rag_pipeline_scene.py"
_HTML_GOLDEN = _HERE / "rag_pipeline_scene.html"
_IMAGE_SEQUENCE_GOLDEN = _HERE / "rag_pipeline_image_sequence_artifacts.json"
_MOTION_CANVAS_GOLDEN = _HERE / "rag_pipeline_motion_canvas_project.json"
_REMOTION_GOLDEN = _HERE / "rag_pipeline_remotion_project.json"
_STATIC_STORYBOARD_GOLDEN = _HERE / "rag_pipeline_static_storyboard_artifacts.json"
_SHOWCASE_FIXTURE = _HERE.parent / "fixtures" / "showcase-composition.vidir.yaml"

class _FakeAdapter:
    id = "fake"
    version = "0.1-test"
    capabilities = CapabilityManifest(
        primitives=frozenset({"rect"}),
        animations=frozenset({"fade_in"}),
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


def _unsupported_fake_ir() -> ConcreteIR:
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


def _unsupported_html_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[
            ResolvedObject.model_construct(
                id="demo.embed",
                primitive="html_embed",
                box=Box(x=0.0, y=0.0, w=100.0, h=50.0),
                z=0,
                style_ref="embed.default",
            )
        ],
        keyframes=[
            Keyframe(
                object_id="demo.embed",
                kind="move",
                start_f=0,
                end_f=24,
                easing="linear",
            )
        ],
        captions=[],
    )


def _unsupported_remotion_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[
            ResolvedObject.model_construct(
                id="demo.webgl",
                primitive="webgl_mesh",
                box=Box(x=0.0, y=0.0, w=100.0, h=50.0),
                z=0,
                style_ref="mesh.default",
            )
        ],
        keyframes=[
            Keyframe(
                object_id="demo.webgl",
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
        unsupported_ir=_unsupported_fake_ir(),
        expected_hash=hash_bytes(_MANIM_GOLDEN.read_bytes()),
    )


def test_html_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        html_adapter,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_html_ir(),
        expected_hash=hash_bytes(_HTML_GOLDEN.read_bytes()),
    )


def test_remotion_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        remotion_adapter,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_remotion_ir(),
        expected_hash=hash_bytes(_REMOTION_GOLDEN.read_bytes()),
    )


def test_motion_canvas_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        motion_canvas_adapter,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_remotion_ir(),
        expected_hash=hash_bytes(_MOTION_CANVAS_GOLDEN.read_bytes()),
    )


def test_image_sequence_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        image_sequence_adapter,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_remotion_ir(),
        expected_hash=hash_bytes(_IMAGE_SEQUENCE_GOLDEN.read_bytes()),
    )


def test_static_storyboard_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        static_storyboard_adapter,
        supported_ir=_compile().concrete,
        unsupported_ir=_unsupported_remotion_ir(),
        expected_hash=hash_bytes(_STATIC_STORYBOARD_GOLDEN.read_bytes()),
    )


def test_fake_adapter_passes_shared_conformance_suite() -> None:
    _assert_adapter_conformance(
        _FakeAdapter(),
        supported_ir=_supported_fake_ir(),
        unsupported_ir=_unsupported_fake_ir(),
    )


def test_registry_dispatch_preserves_builtin_emit_hashes() -> None:
    registry = builtin_registry()
    assert registry.ids() == (
        "html",
        "image_sequence",
        "manim",
        "motion_canvas",
        "remotion",
        "static_storyboard",
    )
    assert registry.require("image_sequence").id == "image_sequence"
    assert registry.require("motion_canvas").id == "motion_canvas"
    assert registry.require("remotion").id == "remotion"
    assert registry.require("static_storyboard").id == "static_storyboard"
    concrete = _compile().concrete
    ctx = _ctx()

    html_direct = html_adapter.emit(concrete, ctx)
    html_dispatched = registry.require("html").emit(concrete, ctx)
    image_sequence_direct = image_sequence_adapter.emit(concrete, ctx)
    image_sequence_dispatched = registry.require("image_sequence").emit(concrete, ctx)
    manim_direct = manim.emit(concrete, ctx)
    manim_dispatched = registry.require("manim").emit(concrete, ctx)
    motion_canvas_direct = motion_canvas_adapter.emit(concrete, ctx)
    motion_canvas_dispatched = registry.require("motion_canvas").emit(concrete, ctx)
    remotion_direct = remotion_adapter.emit(concrete, ctx)
    remotion_dispatched = registry.require("remotion").emit(concrete, ctx)
    static_storyboard_direct = static_storyboard_adapter.emit(concrete, ctx)
    static_storyboard_dispatched = registry.require("static_storyboard").emit(concrete, ctx)

    assert html_dispatched.digest == html_direct.digest == hash_bytes(_HTML_GOLDEN.read_bytes())
    assert html_dispatched.data == html_direct.data
    assert (
        image_sequence_dispatched.digest
        == image_sequence_direct.digest
        == hash_bytes(_IMAGE_SEQUENCE_GOLDEN.read_bytes())
    )
    assert image_sequence_dispatched.data == image_sequence_direct.data
    assert manim_dispatched.digest == manim_direct.digest == hash_bytes(_MANIM_GOLDEN.read_bytes())
    assert manim_dispatched.data == manim_direct.data
    assert (
        motion_canvas_dispatched.digest
        == motion_canvas_direct.digest
        == hash_bytes(_MOTION_CANVAS_GOLDEN.read_bytes())
    )
    assert motion_canvas_dispatched.data == motion_canvas_direct.data
    assert (
        remotion_dispatched.digest
        == remotion_direct.digest
        == hash_bytes(_REMOTION_GOLDEN.read_bytes())
    )
    assert remotion_dispatched.data == remotion_direct.data
    assert (
        static_storyboard_dispatched.digest
        == static_storyboard_direct.digest
        == hash_bytes(_STATIC_STORYBOARD_GOLDEN.read_bytes())
    )
    assert static_storyboard_dispatched.data == static_storyboard_direct.data


def _compile_showcase() -> ConcreteIR:
    """Compile the showcase fixture to its fully-resolved Concrete IR."""
    ir, diagnostics = validate_schema(load_document(_SHOWCASE_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    state = run_pipeline(ir, _ctx())
    assert state.diagnostics == []
    return state.concrete


def test_showcase_composition_supported_by_review_html_remotion() -> None:
    """Backends carrying the code/formula primitives accept the showcase grammar."""
    concrete = _compile_showcase()
    for adapter in (static_storyboard_adapter, html_adapter, remotion_adapter):
        assert adapter.supports(concrete) == []


def test_showcase_composition_unsupported_on_manim_is_explicit() -> None:
    """Manim lacks code/formula, so showcase fails with explicit VIR5031, no downgrade."""
    diagnostics = manim.supports(_compile_showcase())
    assert diagnostics
    assert {diagnostic.code for diagnostic in diagnostics} == {VIR_UNSUPPORTED_PRIMITIVE}
    assert all(diagnostic.code.startswith("VIR5") for diagnostic in diagnostics)
    messages = " ".join(diagnostic.message for diagnostic in diagnostics)
    assert 'primitive "code"' in messages
    assert 'primitive "formula"' in messages
