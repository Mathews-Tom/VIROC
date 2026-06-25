"""Compiler pipeline driver — phases P3 through P8 (design §3).

The full pipeline runs P1..P13; this module wires the pure post-parse phases that
produce the Concrete IR:

- **P3 normalize** — canonicalize the Semantic IR (stable ids, defaults).
- **P4 resolve + hash assets** — resolve every referenced asset and hash it,
  collecting VIR4xxx diagnostics for any that are missing or unreadable.
- **P5 grammar expansion + P6 layout resolve** — for each scene, expand it with
  its grammar and lay the abstract objects out into resolved boxes.
- **P7 timeline resolve** — resolve each scene's frame span and its beats to
  absolute frame windows, collecting VIR2xxx diagnostics for out-of-grammar
  time expressions.
- **P8 build Concrete IR** — animate each scene into keyframes and lower its
  narration to captions, offsetting per-scene frames onto the global timeline,
  then assemble the renderer-neutral :class:`~viroc.ir.ConcreteIR`.

Ordering is the contract: normalize first, then assets, then per-scene layout,
timeline, and animation over the normalized IR. Scenes play back-to-back, so each
scene's keyframes and captions are offset by the cumulative span of the scenes
before it, keeping every keyframe window within its own scene's frame span.

The result is a pure function of the Semantic IR, config, and grammar versions:
identical input yields a byte-identical Concrete IR (the golden guarantee).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from viroc.compiler.assets import ResolvedAsset, resolve_assets
from viroc.compiler.normalize import normalize
from viroc.compiler.resolve_layout import resolve_layout
from viroc.compiler.resolve_time import ResolvedBeat, frames_for_seconds, resolve_beats
from viroc.core import BuildContext, Diagnostic
from viroc.grammars import Grammar, LayoutGrammar, get, register_builtins
from viroc.ir import (
    Caption,
    ConcreteIR,
    Keyframe,
    ResolvedObject,
    Scene,
    SemanticIR,
)


@dataclass(frozen=True, slots=True)
class CompileState:
    """The assembled result of the pure pipeline phases (P3–P8).

    ``ir`` is the normalized Semantic IR (P3); ``concrete`` is the fully-resolved
    Concrete IR (P8), whose ``objects``/``keyframes``/``captions`` are the layout,
    animation, and narration outputs of every scene on a single timeline;
    ``assets`` are the resolved, hashed assets (P4); ``diagnostics`` aggregates
    every diagnostic emitted by the phases (asset VIR4xxx, timing VIR2xxx).
    """

    ir: SemanticIR
    concrete: ConcreteIR
    assets: list[ResolvedAsset] = field(default_factory=list[ResolvedAsset])
    diagnostics: list[Diagnostic] = field(default_factory=list[Diagnostic])


def _animate(
    grammar: LayoutGrammar, objects: list[ResolvedObject], scene: Scene, fps: int
) -> list[Keyframe]:
    """Animate ``scene`` if its grammar supports it; raise otherwise.

    Pre-validation guarantees the scene's grammar is registered; a registered
    grammar that is layout-only (no ``animate``) cannot be assembled into a
    Concrete IR, so it is a programmer error here, surfaced loudly rather than
    silently producing a keyframe-less render.
    """
    if not isinstance(grammar, Grammar):
        raise TypeError(f"grammar {scene.grammar!r} does not support animation")
    return grammar.animate(objects, scene, fps)


def _offset_keyframes(keyframes: list[Keyframe], offset: int) -> list[Keyframe]:
    """Shift every keyframe window onto the global timeline by ``offset`` frames."""
    if offset == 0:
        return keyframes
    return [
        kf.model_copy(update={"start_f": kf.start_f + offset, "end_f": kf.end_f + offset})
        for kf in keyframes
    ]


def _scene_captions(
    scene: Scene, beats: list[ResolvedBeat], span: int, offset: int
) -> list[Caption]:
    """Lower a scene's authored narration to captions on the global timeline.

    A scene with beats yields one caption per narrated beat over that beat's
    resolved window; a scene with only scene-level narration yields a single
    caption spanning the whole scene. Durations are authored, never TTS-derived,
    so the compile stays pure (design §10).
    """
    if scene.beats:
        return [
            Caption(
                text=beat.narration,
                start_f=offset + beat.start_f,
                end_f=offset + beat.end_f,
            )
            for beat in beats
            if beat.narration is not None
        ]
    if scene.narration is not None:
        return [Caption(text=scene.narration, start_f=offset, end_f=offset + span)]
    return []


def run_pipeline(
    ir: SemanticIR, ctx: BuildContext, *, asset_refs: Iterable[str] = ()
) -> CompileState:
    """Run phases P3–P8, producing a fully-resolved Concrete IR.

    Normalizes the IR (P3), resolves and hashes assets (P4), then for each scene
    expands + lays out its objects (P5+P6), resolves its frame span and beats
    (P7), and animates it into keyframes and captions (P8). Scenes are placed
    back-to-back: each scene's keyframes and captions are offset by the spans of
    the scenes before it. Returns a :class:`CompileState` carrying the normalized
    IR, the assembled Concrete IR, the resolved assets, and every diagnostic.
    """
    normalized = normalize(ir)
    resolved_assets, diagnostics = resolve_assets(asset_refs, ctx)
    fps = normalized.video.fps
    resolution = (normalized.video.resolution.width, normalized.video.resolution.height)

    objects: list[ResolvedObject] = []
    keyframes: list[Keyframe] = []
    captions: list[Caption] = []

    register_builtins()
    scene_start = 0
    for scene in normalized.scenes:
        grammar = get(scene.grammar)
        scene_objects = resolve_layout(scene, normalized, ctx)
        objects.extend(scene_objects)

        span = frames_for_seconds(scene.duration, fps)
        keyframes.extend(
            _offset_keyframes(_animate(grammar, scene_objects, scene, fps), scene_start)
        )

        beats, beat_diagnostics = resolve_beats(scene.beats, fps)
        diagnostics.extend(beat_diagnostics)
        captions.extend(_scene_captions(scene, beats, span, scene_start))

        scene_start += span

    concrete = ConcreteIR(
        fps=fps,
        resolution=resolution,
        objects=objects,
        keyframes=keyframes,
        captions=captions,
    )
    return CompileState(
        ir=normalized, concrete=concrete, assets=resolved_assets, diagnostics=diagnostics
    )
