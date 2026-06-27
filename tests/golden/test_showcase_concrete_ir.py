"""Golden Concrete IR for the showcase composition fixture (M19, PR-5).

The milestone's acceptance, pinned against a committed golden: the showcase
fixture compiles (P1->P8) to the expected fully-resolved Concrete IR — objects,
keyframes, and captions — that the compile is byte-stable across runs (a digest
recomputed in the same run matches the golden), that every keyframe window lies
within its scene's frame span, and that the choreography uses only the
common-floor animation set the top-three backends support.

The golden file ``showcase_composition_concrete.json`` is the canonical resolved
storyboard; a change to expansion, layout, animation, or timeline resolve must
update it deliberately — the review signal a golden buys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.compiler.resolve_time import frames_for_seconds
from viroc.core import BuildContext, BuildPaths, hash_data
from viroc.ir import load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "showcase-composition.vidir.yaml"
_GOLDEN = _HERE / "showcase_composition_concrete.json"
_SUPPORTED_ANIMATIONS = {"fade_in", "draw", "highlight", "fade_out"}


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-showcase-concrete-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _compile() -> CompileState:
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    return run_pipeline(ir, _ctx())


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
    concrete = _compile().concrete
    assert concrete.model_dump(mode="json") == _golden()


def test_concrete_ir_digest_is_byte_stable() -> None:
    """Compiling twice yields the identical digest (the determinism guarantee)."""
    first = hash_data(_compile().concrete.model_dump(mode="json"))
    second = hash_data(_compile().concrete.model_dump(mode="json"))
    assert first == second
    assert first == hash_data(_golden())


def test_every_keyframe_lies_within_its_scene_span() -> None:
    """Acceptance: each keyframe window is within its own scene's frame span."""
    state = _compile()
    windows = _scene_windows(state)
    for keyframe in state.concrete.keyframes:
        scene_id = keyframe.object_id.split(".", 1)[0]
        start, end = windows[scene_id]
        assert start <= keyframe.start_f <= keyframe.end_f <= end


def test_choreography_uses_only_supported_animations() -> None:
    """The keyframe set stays within the top-three common animation floor."""
    kinds = {keyframe.kind for keyframe in _compile().concrete.keyframes}
    assert kinds
    assert kinds <= _SUPPORTED_ANIMATIONS
