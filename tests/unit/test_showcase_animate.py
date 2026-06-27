"""Unit coverage for the showcase grammar's animation step (M19, PR-3)."""

from __future__ import annotations

from viroc.compiler.resolve_time import frames_for_seconds
from viroc.grammars.showcase.animate import animate
from viroc.ir import Box, ResolvedObject, Scene


def _scene(duration: str = "6s") -> Scene:
    return Scene(id="reveal", grammar="showcase", duration=duration, nodes=["a"])


def _objects() -> list[ResolvedObject]:
    box = Box(x=0, y=0, w=10, h=10)
    return [
        ResolvedObject(id="reveal.a.panel", primitive="rect", box=box, style_ref="panel.x"),
        ResolvedObject(id="reveal.a.title", primitive="text", box=box, style_ref="t"),
        ResolvedObject(id="reveal.b.code_card", primitive="code", box=box, style_ref="code_card.x"),
        ResolvedObject(id="reveal.a.b.link", primitive="arrow", box=box, style_ref="edge.split"),
    ]


def test_animate_entrance_kind_by_primitive() -> None:
    """Connectors draw on entrance; cards and titles fade in."""
    keyframes = animate(_objects(), _scene(), fps=30)
    entrance = {kf.object_id: kf.kind for kf in keyframes if kf.end_f <= _enter_win()}
    assert entrance["reveal.a.panel"] == "fade_in"
    assert entrance["reveal.a.title"] == "fade_in"
    assert entrance["reveal.b.code_card"] == "fade_in"
    assert entrance["reveal.a.b.link"] == "draw"


def test_animate_highlights_only_cards() -> None:
    """The transform sweep highlights cards (rect/code), never titles or arrows."""
    highlights = [kf for kf in animate(_objects(), _scene(), fps=30) if kf.kind == "highlight"]
    assert {kf.object_id for kf in highlights} == {"reveal.a.panel", "reveal.b.code_card"}


def test_animate_every_object_exits() -> None:
    """Every object fades out together over the final stretch."""
    keyframes = animate(_objects(), _scene(), fps=30)
    exits = [kf for kf in keyframes if kf.kind == "fade_out"]
    assert {kf.object_id for kf in exits} == {obj.id for obj in _objects()}
    assert all(kf.end_f == frames_for_seconds("6s", 30) for kf in exits)


def test_animate_windows_lie_within_the_scene_span() -> None:
    """No keyframe escapes the scene's frame span by construction."""
    span = frames_for_seconds("6s", 30)
    for kf in animate(_objects(), _scene(), fps=30):
        assert 0 <= kf.start_f <= kf.end_f <= span


def test_animate_uses_only_top_three_supported_kinds() -> None:
    """Showcase animates within the common-floor animation set (no move)."""
    kinds = {kf.kind for kf in animate(_objects(), _scene(), fps=30)}
    assert kinds <= {"fade_in", "draw", "highlight", "fade_out"}


def test_animate_is_deterministic() -> None:
    """Animating the same objects twice yields identical keyframes."""
    first = [kf.model_dump() for kf in animate(_objects(), _scene(), fps=30)]
    second = [kf.model_dump() for kf in animate(_objects(), _scene(), fps=30)]
    assert first == second


def test_animate_empty_or_zero_span_yields_nothing() -> None:
    """An empty object set or a non-positive span produces no keyframes."""
    assert animate([], _scene(), fps=30) == []
    assert animate(_objects(), _scene(duration="0s"), fps=30) == []


def _enter_win() -> int:
    """The entrance window end used to bucket entrance keyframes in tests."""
    return max(frames_for_seconds("6s", 30) // 3, 1)
