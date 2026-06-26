"""Post-resolve Concrete IR validation — pipeline phase P9."""

from __future__ import annotations

from pathlib import Path

from viroc.compiler.pipeline import run_pipeline
from viroc.core import BuildContext, BuildPaths, ValidationThresholds
from viroc.ir import Box, Caption, ConcreteIR, Keyframe, ResolvedObject, SemanticIR
from viroc.validators.layout import (
    VIR_OBJECT_CLIPPING,
    VIR_OBJECT_OVERLAP,
    VIR_UNSAFE_MARGIN,
    validate_layout,
)
from viroc.validators.timing import (
    VIR_BEAT_OVERLAP,
    VIR_CAPTION_UNDERFLOW,
    VIR_IMPOSSIBLE_DURATION,
    validate_timing,
)

_RAG_IR: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {"id": "rag_overview", "title": "How RAG Works"},
    "entities": [
        {"id": "documents", "label": "Documents", "type": "data_source"},
        {"id": "chunks", "label": "Chunks", "type": "intermediate"},
        {"id": "embedder", "label": "Embedding Model", "type": "model"},
        {"id": "vector_db", "label": "Vector DB", "type": "storage"},
    ],
    "scenes": [
        {
            "id": "pipeline",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["documents", "chunks", "embedder", "vector_db"],
            "edges": [
                {"from": "documents", "to": "chunks", "kind": "split"},
                {"from": "chunks", "to": "embedder", "kind": "transform"},
                {"from": "embedder", "to": "vector_db", "kind": "store"},
            ],
            "narration": "Documents flow into the vector database.",
        }
    ],
}


def _semantic(raw: dict[str, object] | None = None) -> SemanticIR:
    return SemanticIR.model_validate(raw if raw is not None else _RAG_IR)


def _ctx(
    *,
    safe_margin_pct: float = 5.0,
    min_text_box_width: float = 1.0,
    min_text_box_height: float = 1.0,
    max_caption_chars_per_second: float = 18.0,
) -> BuildContext:
    return _ctx_for_root(
        Path("/tmp/viroc-validate"),
        safe_margin_pct=safe_margin_pct,
        min_text_box_width=min_text_box_width,
        min_text_box_height=min_text_box_height,
        max_caption_chars_per_second=max_caption_chars_per_second,
    )


def _ctx_for_root(
    root: Path,
    *,
    safe_margin_pct: float = 5.0,
    min_text_box_width: float = 1.0,
    min_text_box_height: float = 1.0,
    max_caption_chars_per_second: float = 18.0,
) -> BuildContext:
    thresholds = ValidationThresholds(
        safe_margin_pct=safe_margin_pct,
        min_text_box_width=min_text_box_width,
        min_text_box_height=min_text_box_height,
        max_caption_chars_per_second=max_caption_chars_per_second,
    )
    return BuildContext(
        paths=BuildPaths(project_root=root, out_dir=root / "dist"),
        validation=thresholds,
    )


def _object(**overrides: object) -> ResolvedObject:
    fields: dict[str, object] = {
        "id": "scene.node",
        "primitive": "rect",
        "box": Box(x=100.0, y=100.0, w=200.0, h=120.0),
        "style_ref": "node.default",
    }
    fields.update(overrides)
    return ResolvedObject.model_validate(fields)


def _keyframe(**overrides: object) -> Keyframe:
    fields: dict[str, object] = {
        "object_id": "scene.node",
        "kind": "fade_in",
        "start_f": 0,
        "end_f": 30,
        "easing": "linear",
    }
    fields.update(overrides)
    return Keyframe.model_validate(fields)


def _caption(**overrides: object) -> Caption:
    fields: dict[str, object] = {"text": "short caption", "start_f": 0, "end_f": 90}
    fields.update(overrides)
    return Caption.model_validate(fields)


def _concrete(
    *,
    objects: list[ResolvedObject] | None = None,
    keyframes: list[Keyframe] | None = None,
    captions: list[Caption] | None = None,
) -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=objects if objects is not None else [_object()],
        keyframes=keyframes if keyframes is not None else [_keyframe()],
        captions=captions if captions is not None else [_caption()],
    )


def test_clean_timing_ir_has_zero_diagnostics() -> None:
    """A feasible Concrete IR emits no timing diagnostics."""
    assert validate_timing(_concrete(), _ctx()) == []


def test_overlapping_beat_windows_emit_vir2xxx() -> None:
    """Same-object animation windows cannot overlap in resolved time."""
    ir = _concrete(
        keyframes=[
            _keyframe(kind="fade_in", start_f=0, end_f=40),
            _keyframe(kind="highlight", start_f=30, end_f=60),
        ]
    )

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_BEAT_OVERLAP]


def test_impossible_or_zero_duration_emits_vir2xxx() -> None:
    """Resolved frame windows must be non-negative and non-empty."""
    ir = _concrete(keyframes=[_keyframe(start_f=10, end_f=10)])

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_IMPOSSIBLE_DURATION]


def test_over_long_caption_emits_underflow_vir2xxx() -> None:
    """Caption text must fit within its authored resolved duration."""
    ir = _concrete(captions=[_caption(text="x" * 40, start_f=0, end_f=30)])

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_CAPTION_UNDERFLOW]


def test_caption_underflow_threshold_is_configurable() -> None:
    """Caption underflow uses BuildContext validation thresholds, not constants."""
    ir = _concrete(captions=[_caption(text="x" * 40, start_f=0, end_f=30)])

    assert validate_timing(ir, _ctx(max_caption_chars_per_second=60.0)) == []


def test_clean_layout_ir_has_zero_diagnostics() -> None:
    """A feasible Concrete IR emits no layout diagnostics."""
    assert validate_layout(_concrete(), _ctx()) == []


def test_overlapping_boxes_emit_vir3xxx() -> None:
    """Resolved object boxes cannot share positive area."""
    ir = _concrete(
        objects=[
            _object(id="scene.a", box=Box(x=100.0, y=100.0, w=200.0, h=120.0)),
            _object(id="scene.b", box=Box(x=250.0, y=160.0, w=200.0, h=120.0)),
        ]
    )

    assert [diag.code for diag in validate_layout(ir, _ctx())] == [VIR_OBJECT_OVERLAP]


def test_overlapping_boxes_in_different_scenes_are_allowed() -> None:
    """Sequential scenes may reuse the same frame positions without VIR3001."""
    ir = _concrete(
        objects=[
            _object(id="scene_a.a", box=Box(x=100.0, y=100.0, w=200.0, h=120.0)),
            _object(id="scene_b.b", box=Box(x=100.0, y=100.0, w=200.0, h=120.0)),
        ]
    )

    assert validate_layout(ir, _ctx()) == []


def test_pipeline_p9_allows_sequential_scenes_to_reuse_layout_positions(
    tmp_path: Path,
) -> None:
    """P9 validates overlap per scene, not across sequential scenes."""
    raw: dict[str, object] = {
        "vidir_version": "0.1",
        "video": {"id": "two_scene", "title": "Two Scene Layout"},
        "entities": [
            {"id": "a", "label": "Alpha", "type": "data_source"},
            {"id": "b", "label": "Beta", "type": "data_source"},
        ],
        "scenes": [
            {"id": "intro", "grammar": "pipeline", "duration": "5s", "nodes": ["a"]},
            {"id": "payoff", "grammar": "pipeline", "duration": "5s", "nodes": ["b"]},
        ],
    }

    state = run_pipeline(_semantic(raw), _ctx_for_root(tmp_path))

    assert state.diagnostics == []
    assert state.exit_code == 0


def test_clipped_text_emits_vir3xxx() -> None:
    """A text-like object below configured bounds is a clipping defect."""
    ir = _concrete(
        objects=[
            _object(
                id="scene.label",
                primitive="text",
                box=Box(x=100.0, y=100.0, w=8.0, h=8.0),
            )
        ]
    )

    assert [
        diag.code for diag in validate_layout(ir, _ctx(min_text_box_width=20.0))
    ] == [VIR_OBJECT_CLIPPING]


def test_unsafe_margin_emits_vir3xxx() -> None:
    """Resolved boxes must stay inside the BuildContext safe frame."""
    ir = _concrete(objects=[_object(box=Box(x=10.0, y=100.0, w=200.0, h=120.0))])

    assert [diag.code for diag in validate_layout(ir, _ctx())] == [VIR_UNSAFE_MARGIN]


def test_safe_margin_threshold_is_configurable() -> None:
    """Layout margin validation uses BuildContext thresholds, not constants."""
    ir = _concrete(objects=[_object(box=Box(x=10.0, y=100.0, w=200.0, h=120.0))])

    assert validate_layout(ir, _ctx(safe_margin_pct=0.0)) == []


def test_clean_rag_pipeline_p9_has_zero_diagnostics(tmp_path: Path) -> None:
    """Clean rag-pipeline passes P9 and remains available for adapter handoff."""
    state = run_pipeline(_semantic(), _ctx_for_root(tmp_path))

    assert state.diagnostics == []
    assert state.exit_code == 0
    assert state.concrete.objects


def test_pipeline_p9_aggregates_timing_diagnostics(tmp_path: Path) -> None:
    """P9 turns overlapping authored beats and over-long captions into VIR2xxx."""
    raw: dict[str, object] = {
        "vidir_version": "0.1",
        "video": {"id": "bad_timing", "title": "Bad Timing"},
        "entities": [{"id": "a", "label": "A", "type": "data_source"}],
        "scenes": [
            {
                "id": "scene",
                "grammar": "pipeline",
                "duration": "10s",
                "nodes": ["a"],
                "beats": [
                    {"id": "intro", "at": "0s", "duration": "4s", "narration": "intro"},
                    {
                        "id": "overlap",
                        "at": "2s",
                        "duration": "1s",
                        "narration": "x" * 80,
                    },
                ],
            }
        ],
    }

    state = run_pipeline(_semantic(raw), _ctx_for_root(tmp_path))

    assert {VIR_BEAT_OVERLAP, VIR_CAPTION_UNDERFLOW} <= {
        diag.code for diag in state.diagnostics
    }
    assert state.exit_code == 1


def test_pipeline_p9_aggregates_layout_diagnostics(tmp_path: Path) -> None:
    """P9 appends layout diagnostics from configured Concrete IR thresholds."""
    state = run_pipeline(_semantic(), _ctx_for_root(tmp_path, safe_margin_pct=49.0))

    assert VIR_UNSAFE_MARGIN in {diag.code for diag in state.diagnostics}
    assert state.exit_code == 1
