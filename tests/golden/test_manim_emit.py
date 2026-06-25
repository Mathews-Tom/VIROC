"""Golden Manim scene.py emission for rag-pipeline (M9, PR-4).

The committed ``rag_pipeline_scene.py`` is the byte-level source artifact VIROC
can guarantee: Concrete IR lowering is pure and stable across runs; rendering the
source remains an environment-dependent M10 concern.
"""

from __future__ import annotations

import os
from pathlib import Path

from pytest import MonkeyPatch

import viroc.adapters.manim as manim
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, ConcreteIR, ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_scene.py"


def _compile() -> CompileState:
    """Load the rag fixture and run the full P1→P9 compile to Concrete IR."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    root = Path("/tmp/viroc-golden-manim-emit-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    state = run_pipeline(ir, ctx)
    assert state.diagnostics == []
    return state


def _ctx(root: Path = Path("/tmp/viroc-golden-manim-emit-test")) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _golden_bytes() -> bytes:
    return _GOLDEN.read_bytes()


def _unsupported_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[
            ResolvedObject(
                id="demo_panel",
                primitive="icon",
                box=Box(x=100.0, y=100.0, w=80.0, h=80.0),
                style_ref="icon.default",
            )
        ],
        keyframes=[],
        captions=[],
    )


def test_emit_rag_pipeline_matches_golden_scene_py() -> None:
    artifact = manim.emit(_compile().concrete, _ctx())

    assert artifact.data == _golden_bytes()
    assert artifact.digest == hash_bytes(_golden_bytes())


def test_emit_source_hash_is_stable_across_two_calls() -> None:
    concrete = _compile().concrete

    first = manim.emit(concrete, _ctx())
    second = manim.emit(concrete, _ctx())

    assert first.data == second.data == _golden_bytes()
    assert first.digest == second.digest == hash_bytes(_golden_bytes())


def test_unsupported_primitive_is_vir5031_with_help() -> None:
    diagnostics = manim.supports(_unsupported_ir())

    assert [diag.code for diag in diagnostics] == [manim.VIR_UNSUPPORTED_PRIMITIVE]
    assert diagnostics[0].code == "VIR5031"
    assert diagnostics[0].message == 'renderer "manim" does not support primitive "icon"'
    assert diagnostics[0].help == (
        'use renderer "html", or provide a fallback image asset for object "demo_panel"'
    )


def test_emit_is_invariant_to_context_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    concrete = _compile().concrete
    first = manim.emit(concrete, _ctx()).data

    monkeypatch.setenv("MANIM_BIN", "/different/manim")
    monkeypatch.setenv("FFMPEG_BIN", "/different/ffmpeg")
    changed_ctx = BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "rendered"),
        config={"project": "different"},
        renderer={"quality": "low"},
    )

    assert manim.emit(concrete, changed_ctx).data == first


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

    assert manim.emit(concrete, _ctx()).data == expected
