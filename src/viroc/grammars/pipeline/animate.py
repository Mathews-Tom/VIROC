"""The ``pipeline`` grammar's animation template (design §4, pipeline phase P8).

Animation is the third thing a grammar owns (after expand and layout): the
default *entrance / transform / exit* choreography for the pattern (design §4).
For a left-to-right pipeline the choreography reads the flow:

- **entrance** — every object enters, staggered left-to-right across the first
  third of the scene; node-boxes and labels ``fade_in``, arrows ``draw`` (the
  line traces in).
- **transform** — each node-box ``highlight``s in turn over the middle of the
  scene, a left-to-right sweep that emphasizes the flow through the pipeline.
- **exit** — every object ``fade_out``s together over the final stretch.

Frame windows resolve against the scene's authored ``duration`` (via the P7
:func:`~viroc.compiler.resolve_time.frames_for_seconds`) and the target ``fps``,
so every keyframe lies within ``[0, span_f]`` — the scene's frame span — by
construction. All arithmetic is integer, so the keyframe set is byte-stable
across runs and machines, the determinism the golden Concrete IR depends on.

Objects are classified by their resolved primitive, not a role tag: an ``arrow``
draws, a ``rect`` is a highlightable node-box, everything else fades. This keeps
``animate`` decoupled from how :func:`~viroc.grammars.pipeline.expand.expand`
labelled roles — it animates whatever the layout placed.
"""

from __future__ import annotations

from viroc.compiler.resolve_time import frames_for_seconds
from viroc.ir import Keyframe, KeyframeKind, ResolvedObject, Scene

_ARROW = "arrow"
"""Primitive whose entrance is a ``draw`` (the connecting line traces in)."""
_NODE = "rect"
"""Primitive treated as a highlightable node-box in the transform sweep."""


def _entrance_kind(primitive: str) -> KeyframeKind:
    """An arrow's entrance draws; everything else fades in."""
    return "draw" if primitive == _ARROW else "fade_in"


def animate(objects: list[ResolvedObject], scene: Scene, fps: int) -> list[Keyframe]:
    """Choreograph ``objects`` into entrance/transform/exit keyframes.

    Returns keyframes in a deterministic order — every entrance (layout order),
    then the node highlight sweep, then every exit — with frame windows resolved
    against the scene span and ``fps``. The scene span is ``frames_for_seconds``
    of the authored ``scene.duration``; every window lies within ``[0, span]``.
    An empty scene or a zero-length span yields no keyframes.
    """
    span = frames_for_seconds(scene.duration, fps)
    if not objects or span <= 0:
        return []

    keyframes: list[Keyframe] = []
    enter_win = max(span // 3, 1)
    exit_win = max(span // 6, 1)

    # Entrance: stagger objects across the first third, left-to-right.
    step = max(enter_win // len(objects), 1)
    for index, obj in enumerate(objects):
        start = min(index * step, enter_win - 1)
        end = min(start + step, enter_win)
        keyframes.append(
            Keyframe(
                object_id=obj.id,
                kind=_entrance_kind(obj.primitive),
                start_f=start,
                end_f=end,
                easing="ease_in_out",
            )
        )

    # Transform: sweep a highlight across the node-boxes over the middle stretch.
    hold_start = enter_win
    hold_end = span - exit_win
    nodes = [obj for obj in objects if obj.primitive == _NODE]
    if nodes and hold_end > hold_start:
        hold_step = max((hold_end - hold_start) // len(nodes), 1)
        for index, node in enumerate(nodes):
            start = min(hold_start + index * hold_step, hold_end - 1)
            end = min(start + hold_step, hold_end)
            keyframes.append(
                Keyframe(
                    object_id=node.id,
                    kind="highlight",
                    start_f=start,
                    end_f=end,
                    easing="linear",
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
