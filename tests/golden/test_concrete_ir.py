"""Golden Concrete IR for the rag-pipeline storyboard (M7, PR-4).

The milestone's acceptance, pinned against a committed golden: the §9.1 RAG
storyboard compiles (P1→P8) to the expected fully-resolved Concrete IR — objects,
keyframes, and captions — that the compile is byte-stable across runs (a digest
recomputed in the same run matches the golden), that every keyframe window lies
within its scene's frame span, and that an unsupported relative-time expression
is hard-rejected as a VIR2xxx diagnostic.

The golden file ``rag_pipeline_concrete.json`` is the canonical resolved storyboard;
a change to layout, animation, or timeline resolve must update it deliberately —
the review signal a golden buys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.compiler.resolve_time import VIR_UNSUPPORTED_TIME, frames_for_seconds
from viroc.core import BuildContext, BuildPaths, hash_data
from viroc.ir import load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURES = _HERE.parent / "fixtures"
_FIXTURE = _FIXTURES / "rag-overview.vidir.yaml"
_BAD_TIME = _FIXTURES / "bad-time.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_concrete.json"


def _compile(fixture: Path) -> CompileState:
    """Load a storyboard and run the full P1→P8 compile to a CompileState."""
    ir, diagnostics = validate_schema(load_document(fixture))
    assert ir is not None
    assert diagnostics == []
    root = Path("/tmp/viroc-golden-concrete-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    return run_pipeline(ir, ctx)


def _golden() -> dict[str, Any]:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


def _scene_windows(state: CompileState) -> dict[str, tuple[int, int]]:
    """Map each scene id to its absolute ``(start_f, end_f)`` on the timeline."""
    windows: dict[str, tuple[int, int]] = {}
    start = 0
    for scene in state.ir.scenes:
        span = frames_for_seconds(scene.duration, state.concrete.fps)
        windows[scene.id] = (start, start + span)
        start += span
    return windows


def test_concrete_ir_matches_golden() -> None:
    """The compiled Concrete IR equals the committed golden, field for field."""
    concrete = _compile(_FIXTURE).concrete
    assert concrete.model_dump(mode="json") == _golden()


def test_concrete_ir_digest_is_byte_stable() -> None:
    """Compiling twice yields the identical digest (the determinism guarantee)."""
    first = hash_data(_compile(_FIXTURE).concrete.model_dump(mode="json"))
    second = hash_data(_compile(_FIXTURE).concrete.model_dump(mode="json"))
    assert first == second
    assert first == hash_data(_golden())


def test_every_keyframe_lies_within_its_scene_span() -> None:
    """Acceptance: each keyframe window is within its own scene's frame span."""
    state = _compile(_FIXTURE)
    windows = _scene_windows(state)
    for keyframe in state.concrete.keyframes:
        scene_id = keyframe.object_id.split(".", 1)[0]
        start, end = windows[scene_id]
        assert start <= keyframe.start_f <= keyframe.end_f <= end


def test_unsupported_relative_time_is_rejected() -> None:
    """A solver-requiring beat time is hard-rejected as VIR2xxx, not half-solved."""
    state = _compile(_BAD_TIME)
    codes = {diag.code for diag in state.diagnostics}
    assert VIR_UNSUPPORTED_TIME in codes
    assert all(code.startswith("VIR2") for code in codes)
