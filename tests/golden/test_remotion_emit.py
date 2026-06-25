"""Golden Remotion project emission for rag-pipeline (M14, PR-3).

The committed ``rag_pipeline_remotion_project.json`` is the byte-level source
artifact VIROC can guarantee for the Remotion backend: Concrete IR lowering is
pure and stable across runs; actual Remotion rendering remains an
environment-dependent concern.
"""

from __future__ import annotations

import os
from pathlib import Path

from pytest import MonkeyPatch

import viroc.adapters.remotion as remotion_adapter
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, ConcreteIR, ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_remotion_project.json"


def _compile() -> CompileState:
    """Load the rag fixture and run the full P1→P9 compile to Concrete IR."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    root = Path("/tmp/viroc-golden-remotion-emit-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    state = run_pipeline(ir, ctx)
    assert state.diagnostics == []
    return state


def _ctx(root: Path = Path("/tmp/viroc-golden-remotion-emit-test")) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _golden_bytes() -> bytes:
    return _GOLDEN.read_bytes()


def _unsupported_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[
            ResolvedObject.model_construct(
                id="demo_panel",
                primitive="webgl_mesh",
                box=Box(x=100.0, y=100.0, w=80.0, h=80.0),
                z=0,
                style_ref="mesh.default",
            )
        ],
        keyframes=[],
        captions=[],
    )


def test_emit_rag_pipeline_matches_golden_project_json() -> None:
    artifact = remotion_adapter.emit(_compile().concrete, _ctx())

    assert artifact.data == _golden_bytes()
    assert artifact.digest == hash_bytes(_golden_bytes())


def test_emit_source_hash_is_stable_across_two_calls() -> None:
    concrete = _compile().concrete

    first = remotion_adapter.emit(concrete, _ctx())
    second = remotion_adapter.emit(concrete, _ctx())

    assert first.data == second.data == _golden_bytes()
    assert first.digest == second.digest == hash_bytes(_golden_bytes())


def test_unsupported_primitive_is_vir5031_with_fallback_help() -> None:
    diagnostics = remotion_adapter.supports(_unsupported_ir())

    assert [diag.code for diag in diagnostics] == [remotion_adapter.VIR_UNSUPPORTED_PRIMITIVE]
    assert diagnostics[0].code == "VIR5031"
    assert diagnostics[0].message == 'renderer "remotion" does not support primitive "webgl_mesh"'
    assert diagnostics[0].help == (
        'use renderer "html", or "manim", or provide a fallback image asset '
        'for object "demo_panel"'
    )


def test_emit_is_invariant_to_context_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    concrete = _compile().concrete
    first = remotion_adapter.emit(concrete, _ctx()).data

    monkeypatch.setenv("NODE_PATH", "/different/node_modules")
    changed_ctx = BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "rendered"),
        config={"project": "different"},
        renderer={"remotion_command": "npx --no-install remotion"},
    )

    assert remotion_adapter.emit(concrete, changed_ctx).data == first


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

    assert remotion_adapter.emit(concrete, _ctx()).data == expected


def test_materialize_source_writes_project_tree(tmp_path: Path) -> None:
    artifact = remotion_adapter.emit(_compile().concrete, _ctx())
    materialized = remotion_adapter.materialize_source(artifact, tmp_path / "generated")
    root = materialized.path
    assert root is not None
    assert root == tmp_path / "generated"
    assert (root / "package.json").exists()
    assert (root / "tsconfig.json").exists()
    assert (root / "src" / "index.ts").exists()
    assert (root / "src" / "Root.tsx").exists()
    assert (root / "src" / "Composition.tsx").exists()
