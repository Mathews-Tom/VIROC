"""Unit coverage for the pure Manim source emitter (M9, PR-2)."""

from __future__ import annotations

from pathlib import Path

from viroc.adapters.manim import emit, source_for
from viroc.core import BuildContext, BuildPaths
from viroc.ir import Box, ConcreteIR, Keyframe, ResolvedObject


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-manim-emit-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _ir() -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[
            ResolvedObject(
                id="pipeline.documents.box",
                primitive="rect",
                box=Box(x=264.0, y=482.0, w=258.0, h=68.0),
                style_ref="node.data_source",
            ),
            ResolvedObject(
                id="pipeline.documents.label",
                primitive="text",
                box=Box(x=330.0, y=562.0, w=126.0, h=36.0),
                style_ref="label",
            ),
        ],
        keyframes=[
            Keyframe(
                object_id="pipeline.documents.box",
                kind="fade_in",
                start_f=0,
                end_f=30,
                easing="ease_in_out",
            ),
            Keyframe(
                object_id="pipeline.documents.label",
                kind="fade_in",
                start_f=30,
                end_f=60,
                easing="ease_in_out",
            ),
        ],
        captions=[],
    )


def test_emit_returns_source_artifact_with_stable_digest() -> None:
    first = emit(_ir(), _ctx())
    second = emit(_ir(), _ctx())

    assert first.kind == "source"
    assert first.data == second.data
    assert first.digest == second.digest
    assert first.digest.startswith("sha256:")


def test_source_contains_mechanical_object_and_timeline_lowering() -> None:
    source = source_for(_ir())

    assert "class VirocScene(Scene):" in source
    assert 'objects["pipeline.documents.box"] = _rect(' in source
    assert 'objects["pipeline.documents.label"] = _text("Documents",' in source
    assert 'FadeIn(objects["pipeline.documents.box"])' in source
    assert "run_time=30 / config.frame_rate" in source
