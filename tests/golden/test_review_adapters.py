"""Golden review-adapter emission for rag-pipeline (M15, PR-3/4).

Covers deterministic image-sequence and static-storyboard review outputs,
unsupported-feature reporting, and materialized review artifacts.
"""

# ruff: noqa: E501


from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import viroc.adapters.image_sequence as image_sequence
import viroc.adapters.static_storyboard as static_storyboard
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, ConcreteIR, Keyframe, ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_IMAGE_SEQUENCE_GOLDEN = _HERE / "rag_pipeline_image_sequence_artifacts.json"
_STATIC_STORYBOARD_GOLDEN = _HERE / "rag_pipeline_static_storyboard_artifacts.json"


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

    assert artifact.data == _IMAGE_SEQUENCE_GOLDEN.read_bytes()
    assert artifact.digest == hash_bytes(_IMAGE_SEQUENCE_GOLDEN.read_bytes())


def test_static_storyboard_emit_matches_golden_artifact_tree() -> None:
    artifact = static_storyboard.emit(_compile().concrete, _ctx())

    assert artifact.data == _STATIC_STORYBOARD_GOLDEN.read_bytes()
    assert artifact.digest == hash_bytes(_STATIC_STORYBOARD_GOLDEN.read_bytes())


def test_review_adapter_source_hashes_are_stable_across_two_calls() -> None:
    concrete = _compile().concrete

    first_image = image_sequence.emit(concrete, _ctx())
    second_image = image_sequence.emit(concrete, _ctx())
    first_storyboard = static_storyboard.emit(concrete, _ctx())
    second_storyboard = static_storyboard.emit(concrete, _ctx())

    assert first_image.data == second_image.data == _IMAGE_SEQUENCE_GOLDEN.read_bytes()
    assert first_image.digest == second_image.digest == hash_bytes(_IMAGE_SEQUENCE_GOLDEN.read_bytes())
    assert first_storyboard.data == second_storyboard.data == _STATIC_STORYBOARD_GOLDEN.read_bytes()
    assert first_storyboard.digest == second_storyboard.digest == hash_bytes(
        _STATIC_STORYBOARD_GOLDEN.read_bytes()
    )


def test_review_adapters_report_vir5xxx_with_fallback_help() -> None:
    image_diagnostics = image_sequence.supports(_unsupported_ir())
    storyboard_diagnostics = static_storyboard.supports(_unsupported_ir())

    for diagnostics, expected_chain in (
        (
            image_diagnostics,
            'use renderer "html", "motion_canvas", "remotion", or "manim", or provide a fallback image asset '
            'for object "demo_panel"',
        ),
        (
            storyboard_diagnostics,
            'use renderer "html", "image_sequence", "motion_canvas", "remotion", or "manim", or provide a fallback image asset '
            'for object "demo_panel"',
        ),
    ):
        assert [diag.code for diag in diagnostics] == [
            image_sequence.VIR_UNSUPPORTED_PRIMITIVE,
            image_sequence.VIR_UNSUPPORTED_ANIMATION,
        ]
        assert diagnostics[0].code == "VIR5031"
        assert diagnostics[0].help == expected_chain
        assert diagnostics[1].code == "VIR5032"


def test_review_adapters_emit_is_invariant_to_context_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    concrete = _compile().concrete
    first_image = image_sequence.emit(concrete, _ctx()).data
    first_storyboard = static_storyboard.emit(concrete, _ctx()).data

    monkeypatch.setenv("PILLOW_VERSION", "different")
    changed_ctx = BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "rendered"),
        config={"project": "different"},
        renderer={"sample_frames": 99},
    )

    assert image_sequence.emit(concrete, changed_ctx).data == first_image
    assert static_storyboard.emit(concrete, changed_ctx).data == first_storyboard


def test_review_adapters_emit_performs_no_filesystem_or_env_reads(monkeypatch: MonkeyPatch) -> None:
    concrete = _compile().concrete
    expected_image = _IMAGE_SEQUENCE_GOLDEN.read_bytes()
    expected_storyboard = _STATIC_STORYBOARD_GOLDEN.read_bytes()

    def fail_read_text(_self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError("emit() must not read template files")

    def fail_read_bytes(_self: Path, *args: object, **kwargs: object) -> bytes:
        raise AssertionError("emit() must not read template files")

    def fail_getenv(*args: object, **kwargs: object) -> str | None:
        raise AssertionError("emit() must not read environment variables")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)
    monkeypatch.setattr(os, "getenv", fail_getenv)

    assert image_sequence.emit(concrete, _ctx()).data == expected_image
    assert static_storyboard.emit(concrete, _ctx()).data == expected_storyboard


def test_review_adapters_materialize_review_trees(tmp_path: Path) -> None:
    image_artifact = image_sequence.emit(_compile().concrete, _ctx())
    image_materialized = image_sequence.materialize_source(image_artifact, tmp_path / "image")
    image_root = image_materialized.path
    assert image_root is not None
    assert (image_root / "frame-plan.json").exists()
    assert (image_root / "summary.md").exists()
    assert (image_root / "captions.md").exists()
    if importlib.util.find_spec("PIL") is not None:
        pngs = sorted((image_root / "frames").glob("*.png"))
        assert pngs

    storyboard_artifact = static_storyboard.emit(_compile().concrete, _ctx())
    storyboard_materialized = static_storyboard.materialize_source(
        storyboard_artifact,
        tmp_path / "storyboard",
    )
    storyboard_root = storyboard_materialized.path
    assert storyboard_root is not None
    assert (storyboard_root / "storyboard.md").exists()
    assert (storyboard_root / "scene-cards.json").exists()
    assert (storyboard_root / "script.md").exists()
    assert (storyboard_root / "captions.md").exists()
