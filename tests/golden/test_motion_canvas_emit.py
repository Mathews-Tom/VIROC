"""Golden Motion Canvas project emission for rag-pipeline (M15, PR-1).

Covers deterministic TypeScript generator emission, unsupported-feature
reporting, and project-tree materialization for the Motion Canvas adapter.
"""

from __future__ import annotations

import os
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import viroc.adapters.motion_canvas as motion_canvas
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, ConcreteIR, Keyframe, ResolvedObject, load_document
from viroc.validators import validate_schema
_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_motion_canvas_project.json"


def _compile() -> CompileState:
    """Load the rag fixture and run the full P1→P9 compile to Concrete IR."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    root = Path("/tmp/viroc-golden-motion-canvas-emit-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    state = run_pipeline(ir, ctx)
    assert state.diagnostics == []
    return state


def _ctx(root: Path = Path("/tmp/viroc-golden-motion-canvas-emit-test")) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))

def _golden_bytes() -> bytes:
    return _GOLDEN.read_bytes()


def _unsupported_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[
            ResolvedObject.model_construct(
                id="demo_panel",
                primitive="webgl_mesh",
                box=Box(x=0.0, y=0.0, w=100.0, h=50.0),
                z=0,
                style_ref="mesh.default",
            )
        ],
        keyframes=[
            Keyframe(
                object_id="demo_panel",
                kind="move",
                start_f=0,
                end_f=24,
                easing="linear",
            )
        ],
        captions=[],
    )


def test_emit_rag_pipeline_matches_golden_project_json() -> None:
    artifact = motion_canvas.emit(_compile().concrete, _ctx())

    assert artifact.data == _golden_bytes()
    assert artifact.digest == hash_bytes(_golden_bytes())


def test_emit_source_hash_is_stable_across_two_calls() -> None:
    concrete = _compile().concrete

    first = motion_canvas.emit(concrete, _ctx())
    second = motion_canvas.emit(concrete, _ctx())

    assert first.data == second.data == _golden_bytes()
    assert first.digest == second.digest == hash_bytes(_golden_bytes())


def test_unsupported_features_are_vir5xxx_with_fallback_help() -> None:
    diagnostics = motion_canvas.supports(_unsupported_ir())

    assert [diag.code for diag in diagnostics] == [
        motion_canvas.VIR_UNSUPPORTED_PRIMITIVE,
        motion_canvas.VIR_UNSUPPORTED_ANIMATION,
    ]
    assert diagnostics[0].code == "VIR5031"
    assert diagnostics[0].message == (
        'renderer "motion_canvas" does not support primitive "webgl_mesh"'
    )
    assert diagnostics[0].help == (
        'use renderer "html", "remotion", or "manim", or provide a fallback image asset '
        'for object "demo_panel"'
    )
    assert diagnostics[1].code == "VIR5032"
    assert diagnostics[1].message == (
        'renderer "motion_canvas" does not support animation "move"'
    )


def test_emit_is_invariant_to_context_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    concrete = _compile().concrete
    first = motion_canvas.emit(concrete, _ctx()).data

    monkeypatch.setenv("NODE_PATH", "/different/node_modules")
    changed_ctx = BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "rendered"),
        config={"project": "different"},
        renderer={"motion_canvas_command": "npx --no-install motion-canvas"},
    )

    assert motion_canvas.emit(concrete, changed_ctx).data == first


def test_emit_performs_no_filesystem_or_env_reads(monkeypatch: MonkeyPatch) -> None:
    concrete = _compile().concrete
    expected = _golden_bytes()

    def fail_read_text(_self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError("emit() must not read template files")

    def fail_read_bytes(_self: Path, *args: object, **kwargs: object) -> bytes:
        raise AssertionError("emit() must not read template files")

    def fail_getenv(*args: object, **kwargs: object) -> str | None:
        raise AssertionError("emit() must not read environment variables")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    monkeypatch.setattr(os, "getenv", fail_getenv)

    assert motion_canvas.emit(concrete, _ctx()).data == expected


def test_materialize_source_writes_project_tree(tmp_path: Path) -> None:
    artifact = motion_canvas.emit(_compile().concrete, _ctx())
    materialized = motion_canvas.materialize_source(artifact, tmp_path / "generated")
    root = materialized.path
    assert root is not None
    assert root == tmp_path / "generated"
    assert (root / "package.json").exists()
    assert (root / "tsconfig.json").exists()
    assert (root / "vite.config.ts").exists()
    assert (root / "src" / "project.ts").exists()
    assert (root / "src" / "scenes" / "viroc.tsx").exists()
