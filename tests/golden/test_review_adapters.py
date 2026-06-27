"""Golden review-adapter emission for rag-pipeline (M15, PR-3/4).

Covers deterministic image-sequence and static-storyboard review outputs,
unsupported-feature reporting, and materialized review artifacts.
"""

# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import viroc.adapters.image_sequence as image_sequence
import viroc.adapters.static_storyboard as static_storyboard
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, hash_bytes
from viroc.ir import Box, Caption, ConcreteIR, Keyframe, ResolvedObject, load_document
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


def _multi_scene_ir() -> ConcreteIR:
    return ConcreteIR(
        fps=24,
        resolution=(1280, 720),
        objects=[
            ResolvedObject.model_construct(
                id="alpha.panel",
                primitive="rect",
                box=Box(x=0.0, y=0.0, w=100.0, h=50.0),
                z=0,
                style_ref="node.process",
            ),
            ResolvedObject.model_construct(
                id="beta.panel",
                primitive="rect",
                box=Box(x=120.0, y=0.0, w=100.0, h=50.0),
                z=0,
                style_ref="node.process",
            ),
        ],
        keyframes=[
            Keyframe(object_id="alpha.panel", kind="fade_in", start_f=0, end_f=12, easing="linear"),
            Keyframe(object_id="beta.panel", kind="fade_in", start_f=12, end_f=24, easing="linear"),
        ],
        captions=[
            Caption(text="alpha caption", start_f=0, end_f=12),
            Caption(text="beta caption", start_f=12, end_f=24),
        ],
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
    assert (image_root / "frames" / "status.json").exists()
    if importlib.util.find_spec("PIL") is not None:
        pngs = sorted((image_root / "frames").glob("*.png"))
        assert pngs

    image_render_ctx = _ctx(tmp_path / "image-render")
    image_render = image_sequence.render(image_materialized, image_render_ctx)
    assert image_render.kind == "video"
    assert image_render.path == image_root / "frame-plan.json"
    assert (image_render_ctx.paths.out_dir / "build.json").exists()

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

    storyboard_render_ctx = _ctx(tmp_path / "storyboard-render")
    storyboard_render = static_storyboard.render(
        storyboard_materialized,
        storyboard_render_ctx,
    )
    assert storyboard_render.kind == "video"
    assert storyboard_render.path == storyboard_root / "storyboard.md"
    assert (storyboard_render_ctx.paths.out_dir / "build.json").exists()


def test_static_storyboard_scene_cards_keep_multi_scene_captions() -> None:
    cards = static_storyboard.scene_cards(_multi_scene_ir())

    assert [card["scene_id"] for card in cards] == ["alpha", "beta"]
    assert cards[0]["caption_lines"] == ["alpha caption"]
    assert cards[1]["caption_lines"] == ["beta caption"]


def test_static_storyboard_review_manifest_links_artifact_hashes() -> None:
    source = static_storyboard.emit(_compile().concrete, _ctx())
    manifest = json.loads(static_storyboard.review_manifest(source))

    assert manifest["source_hash"] == source.digest
    assert manifest["adapter_source_version"] == "static-storyboard-source-v0.1"
    tree = static_storyboard.source_tree(source)
    assert manifest["artifacts"] == {
        name: hash_bytes(body.encode("utf-8")) for name, body in tree.items()
    }
    assert set(manifest["artifacts"]) == {
        "captions.md",
        "scene-cards.json",
        "script.md",
        "storyboard.md",
    }


def test_static_storyboard_review_manifest_is_deterministic() -> None:
    concrete = _compile().concrete
    first = static_storyboard.review_manifest(static_storyboard.emit(concrete, _ctx()))
    second = static_storyboard.review_manifest(static_storyboard.emit(concrete, _ctx()))
    assert first == second


def test_static_storyboard_materialize_review_writes_manifest(tmp_path: Path) -> None:
    source = static_storyboard.emit(_compile().concrete, _ctx())
    review_dir = tmp_path / "review"
    artifact = static_storyboard.materialize_review(source, review_dir)

    assert artifact.path == review_dir
    manifest_path = review_dir / static_storyboard.REVIEW_MANIFEST_FILENAME
    assert manifest_path.read_text(encoding="utf-8") == static_storyboard.review_manifest(source)
    for name in ("storyboard.md", "script.md", "scene-cards.json", "captions.md"):
        assert (review_dir / name).is_file()


def test_static_storyboard_invalidate_review_removes_stale_dir(tmp_path: Path) -> None:
    review_dir = tmp_path / "review"
    static_storyboard.materialize_review(static_storyboard.emit(_compile().concrete, _ctx()), review_dir)
    assert review_dir.exists()

    static_storyboard.invalidate_review(review_dir)
    assert not review_dir.exists()

    # Invalidating an absent directory is a no-op.
    static_storyboard.invalidate_review(review_dir)
    assert not review_dir.exists()
