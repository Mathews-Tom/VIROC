"""Pipeline animation template — phase P8 (M7, PR-2).

The pipeline grammar's default choreography: every object enters (arrows draw,
the rest fade in), each node-box highlights in a left-to-right sweep, and every
object fades out at the end. The behavioural guarantees the assembly and golden
phases lean on: every keyframe window lies within the scene's frame span,
windows are well-formed (start <= end), and the keyframe set is deterministic.
"""

from __future__ import annotations

from viroc.grammars.pipeline.animate import animate
from viroc.ir import Box, Primitive, ResolvedObject, Scene

_FPS = 30


def _obj(obj_id: str, primitive: Primitive) -> ResolvedObject:
    return ResolvedObject(
        id=obj_id, primitive=primitive, box=Box(x=0, y=0, w=10, h=10), style_ref="s"
    )

def _objects() -> list[ResolvedObject]:
    """A two-node pipeline: box, label, box, label, connecting arrow."""
    return [
        _obj("n1", "rect"),
        _obj("n1.label", "text"),
        _obj("n2", "rect"),
        _obj("n2.label", "text"),
        _obj("n1.n2.arrow", "arrow"),
    ]


def _scene(duration: str = "10s") -> Scene:
    return Scene(id="s", grammar="pipeline", duration=duration)


def test_empty_objects_yields_no_keyframes() -> None:
    """Nothing to animate -> no keyframes."""
    assert animate([], _scene(), _FPS) == []


def test_zero_span_yields_no_keyframes() -> None:
    """A zero-length scene span produces no keyframes (no negative windows)."""
    assert animate(_objects(), _scene("0s"), _FPS) == []


def test_emits_entrance_transform_and_exit() -> None:
    """Five objects -> 5 entrances + 2 node highlights + 5 exits."""
    keyframes = animate(_objects(), _scene(), _FPS)
    kinds = [kf.kind for kf in keyframes]
    assert kinds.count("highlight") == 2
    assert kinds.count("fade_out") == 5
    assert kinds.count("fade_in") + kinds.count("draw") == 5
    assert len(keyframes) == 12


def test_entrance_kind_follows_primitive() -> None:
    """Arrows draw on entrance; node-boxes and labels fade in."""
    entrances = animate(_objects(), _scene(), _FPS)[:5]
    by_id = {kf.object_id: kf.kind for kf in entrances}
    assert by_id["n1.n2.arrow"] == "draw"
    assert by_id["n1"] == "fade_in"
    assert by_id["n1.label"] == "fade_in"


def test_highlight_sweep_targets_only_node_boxes() -> None:
    """The transform sweep highlights the rect node-boxes, not labels or arrows."""
    keyframes = animate(_objects(), _scene(), _FPS)
    highlighted = {kf.object_id for kf in keyframes if kf.kind == "highlight"}
    assert highlighted == {"n1", "n2"}


def test_every_window_lies_within_the_scene_span() -> None:
    """Acceptance: every keyframe window is within [0, span] and well-formed."""
    span = 300  # frames_for_seconds("10s", 30)
    keyframes = animate(_objects(), _scene(), _FPS)
    assert all(0 <= kf.start_f <= kf.end_f <= span for kf in keyframes)


def test_exit_keyframes_end_at_the_span() -> None:
    """Every exit fades out ending exactly on the scene span boundary."""
    span = 300
    exits = [kf for kf in animate(_objects(), _scene(), _FPS) if kf.kind == "fade_out"]
    assert {kf.object_id for kf in exits} == {"n1", "n1.label", "n2", "n2.label", "n1.n2.arrow"}
    assert all(kf.end_f == span for kf in exits)


def test_animation_is_deterministic() -> None:
    """Animating the same scene twice yields the identical keyframes."""
    assert animate(_objects(), _scene(), _FPS) == animate(_objects(), _scene(), _FPS)
