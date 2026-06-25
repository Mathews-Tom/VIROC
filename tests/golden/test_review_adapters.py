"""Golden review-adapter emission for rag-pipeline (M15, PR-3).

Starts with the image-sequence review surface; the static storyboard surface is
added in the next stack slice.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import viroc.adapters.image_sequence as image_sequence
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, ConcreteIR, Keyframe, ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_IMAGE_SEQUENCE_GOLDEN = _HERE / "rag_pipeline_image_sequence_artifacts.json"


def _compile() -> CompileState:
    """Load the rag fixture and run the full P1→P9 compile to Concrete IR."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    root = Path("/tmp/viroc-golden-review-adapters-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    state = run_pipeline(ir, ctx)
    assert state.diagnostics == []
    return state


def _ctx(root: Path = Path("/tmp/viroc-golden-review-adapters-test")) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _golden_bytes() -> bytes:
    return _IMAGE_SEQUENCE_GOLDEN.read_bytes()


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


def test_image_sequence_emit_matches_golden_artifact_tree() -> None:
    artifact = image_sequence.emit(_compile().concrete, _ctx())

    assert artifact.data == _golden_bytes()
    assert artifact.digest == hash_bytes(_golden_bytes())


def test_image_sequence_source_hash_is_stable_across_two_calls() -> None:
    concrete = _compile().concrete

    first = image_sequence.emit(concrete, _ctx())
    second = image_sequence.emit(concrete, _ctx())

    assert first.data == second.data == _golden_bytes()
    assert first.digest == second.digest == hash_bytes(_golden_bytes())


def test_image_sequence_unsupported_features_are_vir5xxx_with_fallback_help() -> None:
    diagnostics = image_sequence.supports(_unsupported_ir())

    assert [diag.code for diag in diagnostics] == [
        image_sequence.VIR_UNSUPPORTED_PRIMITIVE,
        image_sequence.VIR_UNSUPPORTED_ANIMATION,
    ]
    assert diagnostics[0].code == "VIR5031"
    assert diagnostics[0].help == (
        'use renderer "html", "motion_canvas", "remotion", or "manim", or provide a fallback image asset '
        'for object "demo_panel"'
    )
    assert diagnostics[1].code == "VIR5032"


def test_image_sequence_emit_is_invariant_to_context_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    concrete = _compile().concrete
    first = image_sequence.emit(concrete, _ctx()).data

    monkeypatch.setenv("PILLOW_VERSION", "different")
    changed_ctx = BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "rendered"),
        config={"project": "different"},
        renderer={"sample_frames": 99},
    )

    assert image_sequence.emit(concrete, changed_ctx).data == first


def test_image_sequence_emit_performs_no_filesystem_or_env_reads(monkeypatch: MonkeyPatch) -> None:
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

    assert image_sequence.emit(concrete, _ctx()).data == expected


def test_image_sequence_materialize_source_writes_review_tree(tmp_path: Path) -> None:
    artifact = image_sequence.emit(_compile().concrete, _ctx())
    materialized = image_sequence.materialize_source(artifact, tmp_path / "generated")
    root = materialized.path
    assert root is not None
    assert root == tmp_path / "generated"
    assert (root / "frame-plan.json").exists()
    assert (root / "summary.md").exists()
    assert (root / "captions.md").exists()
    if importlib.util.find_spec("PIL") is not None:
        pngs = sorted((root / "frames").glob("*.png"))
        assert pngs
