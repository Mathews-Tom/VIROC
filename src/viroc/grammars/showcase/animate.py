"""The ``showcase`` grammar's animation template (design §4, pipeline phase P8).

Animation is the third thing a grammar owns (after expand and layout): the
default *entrance / transform / exit* choreography for the pattern. A showcase
scene is an authored composition rather than a flow, so its choreography reveals
the composition, emphasizes each card, then clears it:

- **entrance** — every object enters, staggered in reading (layout) order across
  the first third of the scene; cards and titles ``fade_in``, connectors ``draw``;
- **transform** — each card ``highlight``s in turn over the middle of the scene,
  a sweep across the composition that draws the eye card by card;
- **exit** — every object ``fade_out``s together over the final stretch.

The four keyframe kinds used — ``fade_in``, ``draw``, ``highlight``, ``fade_out``
— are exactly the animation set every top-three backend (review/HTML/Remotion)
supports, so a showcase scene animates within the common floor and never needs a
``move`` keyframe no backend can render.

Objects are classified by their resolved primitive, not a role tag: a connector
(``arrow``) draws and never highlights; a card (``rect``/``code``/``formula``/
``icon``) highlights; a title (``text``) only fades. Frame windows resolve against
the scene's authored ``duration`` (via :func:`~viroc.compiler.resolve_time.
frames_for_seconds`) and the target ``fps``, so every keyframe lies within
``[0, span_f]`` by construction. All arithmetic is integer, so the keyframe set is
byte-stable across runs and machines.
"""

from __future__ import annotations

from viroc.compiler.resolve_time import frames_for_seconds
from viroc.ir import Keyframe, KeyframeKind, ResolvedObject, Scene

_ARROW = "arrow"
"""Primitive whose entrance is a ``draw`` (the connector traces in)."""
_CARDS = frozenset({"rect", "code", "formula", "icon"})
"""Primitives treated as highlightable cards in the transform sweep."""


def _entrance_kind(primitive: str) -> KeyframeKind:
    """A connector's entrance draws; every other object fades in."""
    return "draw" if primitive == _ARROW else "fade_in"


def animate(objects: list[ResolvedObject], scene: Scene, fps: int) -> list[Keyframe]:
    """Choreograph ``objects`` into entrance/transform/exit keyframes.

    Returns the keyframes in a deterministic order: every object's entrance in
    reading order, then a highlight per card in reading order, then every
    object's exit in reading order. An empty scene or a non-positive span yields
    no keyframes.
    """
    span = frames_for_seconds(scene.duration, fps)
    if not objects or span <= 0:
        return []

    keyframes: list[Keyframe] = []
    enter_win = max(span // 3, 1)
    exit_win = max(span // 6, 1)

    # Entrance: stagger objects across the first third, in reading order.
    step = max(enter_win // len(objects), 1)
    for index, obj in enumerate(objects):
        start = min(index * step, enter_win - 1)
        keyframes.append(
            Keyframe(
                object_id=obj.id,
                kind=_entrance_kind(obj.primitive),
                start_f=start,
                end_f=enter_win,
                easing="ease_in_out",
            )
        )

    # Transform: sweep a highlight across the cards over the middle stretch.
    hold_start = enter_win
    hold_end = span - exit_win
    cards = [obj for obj in objects if obj.primitive in _CARDS]
    if cards and hold_end > hold_start:
        hold_step = max((hold_end - hold_start) // len(cards), 1)
        for index, card in enumerate(cards):
            start = min(hold_start + index * hold_step, hold_end - 1)
            keyframes.append(
                Keyframe(
                    object_id=card.id,
                    kind="highlight",
                    start_f=start,
                    end_f=min(start + hold_step, hold_end),
                    easing="ease_in_out",
                )
            )

    # Exit: every object fades out together over the final stretch.
    exit_start = span - exit_win
    for obj in objects:
        keyframes.append(
            Keyframe(
                object_id=obj.id,
                kind="fade_out",
                start_f=exit_start,
                end_f=span,
                easing="ease_in_out",
            )
        )

    return keyframes
