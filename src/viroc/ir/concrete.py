"""Concrete IR: the renderer-neutral resolved storyboard (design §2.3).

The Concrete IR is the Resolver's output. Where the Semantic IR says *what a
storyboard means*, the Concrete IR says *where every object sits and when every
animation runs*: each :class:`ResolvedObject` carries a resolved :class:`Box`
(logical units, origin top-left) and each :class:`Keyframe` a resolved frame
window. It is still renderer-neutral — no Manim/React types appear — so an
adapter's only remaining job is to draw, never to lay out or to time.

Models are Pydantic v2, composition over inheritance, no behaviour on the data
classes (matching the Semantic IR). ``extra="forbid"`` makes an unexpected field
a hard error rather than silently-dropped data, which keeps the resolver and its
golden hashes honest. The shapes here are populated by later milestones (grammar
expansion, layout/timeline resolve); M5 defines the vocabulary only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Primitive = Literal["text", "rect", "icon", "arrow", "code", "formula"]
"""A drawable kind an adapter must know how to render (design §2.3)."""

KeyframeKind = Literal["fade_in", "draw", "move", "highlight", "fade_out"]
"""The animation a :class:`Keyframe` applies to its object (design §2.3)."""

Easing = Literal["linear", "ease_in_out", "spring"]
"""The interpolation curve a :class:`Keyframe` uses between its endpoints."""


class _Model(BaseModel):
    """Shared strict config for every Concrete IR model.

    ``extra="forbid"`` rejects unknown fields so a malformed resolver output
    surfaces immediately instead of producing a silently-degraded render.
    """

    model_config = ConfigDict(extra="forbid")


class Box(_Model):
    """An axis-aligned rectangle in logical units, origin top-left (design §2.3)."""

    x: float
    y: float
    w: float
    h: float


class ResolvedObject(_Model):
    """A drawable with a resolved position: the unit an adapter lowers to source."""

    id: str
    primitive: Primitive
    box: Box
    z: int = 0
    style_ref: str


class Keyframe(_Model):
    """One animation on one object over a resolved ``[start_f, end_f)`` window."""

    object_id: str
    kind: KeyframeKind
    start_f: int
    end_f: int
    easing: Easing


class Caption(_Model):
    """A timed on-screen caption over a resolved frame window (lowered to SRT).

    Durations are authored, not TTS-derived, so the compile stays a pure function
    (design §10). ``start_f``/``end_f`` are resolved frames, like a keyframe.
    """

    text: str
    start_f: int
    end_f: int


class ConcreteIR(_Model):
    """The fully-resolved, still renderer-neutral storyboard handed to an adapter."""

    fps: int
    resolution: tuple[int, int]
    objects: list[ResolvedObject]
    keyframes: list[Keyframe]
    captions: list[Caption]
