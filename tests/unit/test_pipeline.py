"""Compiler pipeline P3–P8 wiring (M5 + M6 + M7).

The driver runs normalize (P3), asset resolution (P4), grammar expand + layout
(P5+P6), timeline resolve (P7), and Concrete IR assembly (P8). These tests assert
the phases execute and their outputs and diagnostics land on the returned state:
the normalized IR, hashed assets, resolved boxes, animation keyframes within each
scene's span, captions from authored narration, and aggregated timing diagnostics.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from viroc.compiler.assets import VIR_ASSET_MISSING
from viroc.compiler.normalize import normalize
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.compiler.resolve_time import VIR_UNSUPPORTED_TIME, frames_for_seconds
from viroc.core import BuildContext, BuildPaths
from viroc.grammars import overlaps
from viroc.ir import Caption, ConcreteIR, SemanticIR

_RAW_IR: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {"id": "RAG Overview", "title": "How RAG Works"},
    "entities": [
        {"id": "Doc Source", "label": "Documents", "type": "data_source"},
        {"id": "Vector DB", "label": "Vector DB", "type": "storage"},
    ],
    "scenes": [
        {
            "id": "Main Scene",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["Doc Source", "Vector DB"],
            "edges": [{"from": "Doc Source", "to": "Vector DB", "kind": "store"}],
            "narration": "Documents flow into the vector database.",
        }
    ],
}


def _ir(raw: dict[str, object] | None = None) -> SemanticIR:
    return SemanticIR.model_validate(raw if raw is not None else _RAW_IR)


def _ctx(root: Path) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def test_run_pipeline_normalizes_the_ir(tmp_path: Path) -> None:
    """P3 runs: the state carries the canonical, normalized Semantic IR."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    assert isinstance(state, CompileState)
    assert state.ir == normalize(_ir())
    assert state.ir.video.id == "rag_overview"
    assert normalize(state.ir) == state.ir


def test_run_pipeline_resolves_present_assets(tmp_path: Path) -> None:
    """P4 runs: a present asset is resolved and hashed, with no diagnostics."""
    (tmp_path / "logo.png").write_bytes(b"bytes")
    state = run_pipeline(_ir(), _ctx(tmp_path), asset_refs=["logo.png"])
    assert [asset.ref for asset in state.assets] == ["logo.png"]
    assert state.assets[0].digest.startswith("sha256:")
    assert state.diagnostics == []


def test_run_pipeline_propagates_asset_diagnostics(tmp_path: Path) -> None:
    """A missing asset surfaces as a VIR4001 diagnostic on the state."""
    state = run_pipeline(_ir(), _ctx(tmp_path), asset_refs=["gone.png"])
    assert state.assets == []
    assert [diag.code for diag in state.diagnostics] == [VIR_ASSET_MISSING]


def test_run_pipeline_resolves_scene_layout(tmp_path: Path) -> None:
    """P5+P6 run: the Concrete IR carries overlap-free resolved boxes."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    objects = state.concrete.objects
    # Two nodes -> box + label each, plus one edge -> one arrow.
    assert len(objects) == 5
    assert not any(overlaps(a.box, b.box) for a, b in combinations(objects, 2))


def test_run_pipeline_assembles_concrete_ir(tmp_path: Path) -> None:
    """P8 runs: the state carries a Concrete IR with fps/resolution and keyframes."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    concrete = state.concrete
    assert isinstance(concrete, ConcreteIR)
    assert concrete.fps == 30
    assert concrete.resolution == (1920, 1080)
    # 5 objects -> 5 entrances + 2 node highlights + 5 exits.
    assert len(concrete.keyframes) == 12


def test_run_pipeline_keyframes_lie_within_the_scene_span(tmp_path: Path) -> None:
    """Acceptance: every keyframe window lies within its scene's frame span."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    span = frames_for_seconds("35s", 30)
    assert all(0 <= kf.start_f <= kf.end_f <= span for kf in state.concrete.keyframes)


def test_run_pipeline_caption_from_scene_narration(tmp_path: Path) -> None:
    """A scene with only scene-level narration yields one caption over its span."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    assert state.concrete.captions == [
        Caption(
            text="Documents flow into the vector database.",
            start_f=0,
            end_f=frames_for_seconds("35s", 30),
        )
    ]


def test_run_pipeline_offsets_subsequent_scenes(tmp_path: Path) -> None:
    """Scenes play back-to-back: a second scene's frames are offset by the first."""
    raw: dict[str, object] = {
        "vidir_version": "0.1",
        "video": {"id": "two-scene", "title": "Two Scenes"},
        "entities": [
            {"id": "a", "label": "A", "type": "data_source"},
            {"id": "b", "label": "B", "type": "storage"},
        ],
        "scenes": [
            {
                "id": "one",
                "grammar": "pipeline",
                "duration": "2s",
                "nodes": ["a", "b"],
                "edges": [{"from": "a", "to": "b"}],
                "narration": "first",
            },
            {
                "id": "two",
                "grammar": "pipeline",
                "duration": "3s",
                "nodes": ["a", "b"],
                "edges": [{"from": "a", "to": "b"}],
                "narration": "second",
            },
        ],
    }
    state = run_pipeline(_ir(raw), _ctx(tmp_path))
    span_one = frames_for_seconds("2s", 30)
    total = span_one + frames_for_seconds("3s", 30)
    assert state.concrete.captions == [
        Caption(text="first", start_f=0, end_f=span_one),
        Caption(text="second", start_f=span_one, end_f=total),
    ]
    # Scene two's objects are id-prefixed; their keyframes are all offset past span_one.
    scene_two = [kf for kf in state.concrete.keyframes if kf.object_id.startswith("two.")]
    assert scene_two
    assert all(kf.start_f >= span_one for kf in scene_two)
    assert max(kf.end_f for kf in state.concrete.keyframes) == total


def test_run_pipeline_surfaces_timing_diagnostics(tmp_path: Path) -> None:
    """An out-of-grammar beat time surfaces as a VIR2xxx diagnostic on the state."""
    raw: dict[str, object] = {
        "vidir_version": "0.1",
        "video": {"id": "bad-time", "title": "Bad Time"},
        "entities": [{"id": "a", "label": "A", "type": "data_source"}],
        "scenes": [
            {
                "id": "s",
                "grammar": "pipeline",
                "duration": "10s",
                "nodes": ["a"],
                "beats": [
                    {"id": "intro", "at": "0s", "duration": "4s"},
                    {"id": "bad", "at": "midpoint(intro.end, s.end)", "duration": "4s"},
                ],
            }
        ],
    }
    state = run_pipeline(_ir(raw), _ctx(tmp_path))
    assert VIR_UNSUPPORTED_TIME in {diag.code for diag in state.diagnostics}
