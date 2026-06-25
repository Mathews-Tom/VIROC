"""Post-resolve timing validation over Concrete IR (pipeline phase P9)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from viroc.core import BuildContext, Diagnostic, DiagnosticClass, code
from viroc.ir import Caption, ConcreteIR, Keyframe

VIR_BEAT_OVERLAP = code(DiagnosticClass.TIMING, 3)
"""Two resolved timing windows overlap where the IR requires sequencing."""

VIR_IMPOSSIBLE_DURATION = code(DiagnosticClass.TIMING, 4)
"""A resolved timing window has a negative, zero, or otherwise impossible duration."""

VIR_CAPTION_UNDERFLOW = code(DiagnosticClass.TIMING, 5)
"""A caption window is too short for its authored text under the configured threshold."""


@dataclass(frozen=True, slots=True)
class _Window:
    """A named half-open frame interval used by timing checks."""

    kind: str
    name: str
    start_f: int
    end_f: int


def validate_timing(ir: ConcreteIR, ctx: BuildContext) -> list[Diagnostic]:
    """Return all Concrete IR timing diagnostics.

    These are necessary-condition checks only: frame windows must be possible,
    same-object animations and captions must not overlap, and captions need enough
    authored duration for their text. No explanatory-quality judgment is made.
    """
    diagnostics: list[Diagnostic] = []
    if ir.fps <= 0:
        return [
            Diagnostic(
                code=VIR_IMPOSSIBLE_DURATION,
                message=f"Concrete IR fps must be positive, got {ir.fps}",
                help="Resolve the storyboard with a positive frames-per-second value.",
            )
        ]

    animation_windows = [_keyframe_window(keyframe) for keyframe in ir.keyframes]
    caption_windows = [_caption_window(caption, index) for index, caption in enumerate(ir.captions)]

    diagnostics.extend(_duration_diagnostics(animation_windows))
    diagnostics.extend(_duration_diagnostics(caption_windows))
    diagnostics.extend(_overlap_diagnostics(animation_windows))
    diagnostics.extend(_overlap_diagnostics(caption_windows))
    diagnostics.extend(_caption_underflow_diagnostics(ir.captions, ir.fps, ctx))
    return diagnostics


def _keyframe_window(keyframe: Keyframe) -> _Window:
    return _Window(
        kind="keyframe",
        name=keyframe.object_id,
        start_f=keyframe.start_f,
        end_f=keyframe.end_f,
    )


def _caption_window(caption: Caption, index: int) -> _Window:
    return _Window(
        kind="caption",
        name=f"captions[{index}]",
        start_f=caption.start_f,
        end_f=caption.end_f,
    )


def _duration_diagnostics(windows: Iterable[_Window]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for window in windows:
        if window.start_f < 0 or window.end_f <= window.start_f:
            diagnostics.append(
                Diagnostic(
                    code=VIR_IMPOSSIBLE_DURATION,
                    message=(
                        f"{window.kind} {window.name!r} has impossible frame window "
                        f"[{window.start_f}, {window.end_f})"
                    ),
                    help="Resolve timing to non-negative half-open windows with end > start.",
                )
            )
    return diagnostics


def _overlap_key(window: _Window) -> str:
    return window.name if window.kind == "keyframe" else window.kind


def _overlap_diagnostics(windows: Iterable[_Window]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    ordered = sorted(
        windows, key=lambda window: (_overlap_key(window), window.start_f)
    )
    previous_by_key: dict[str, _Window] = {}
    for window in ordered:
        key = _overlap_key(window)
        previous = previous_by_key.get(key)
        if previous is not None and previous.end_f > window.start_f:
            diagnostics.append(
                Diagnostic(
                    code=VIR_BEAT_OVERLAP,
                    message=(
                        f"{window.kind} {window.name!r} overlaps: "
                        f"[{previous.start_f}, {previous.end_f}) and "
                        f"[{window.start_f}, {window.end_f})"
                    ),
                    help=(
                        "Resolve authored beats so each dependent window starts at or "
                        "after the previous end."
                    ),
                )
            )
        if previous is None or window.end_f > previous.end_f:
            previous_by_key[key] = window
    return diagnostics


def _caption_underflow_diagnostics(
    captions: list[Caption], fps: int, ctx: BuildContext
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    max_chars_per_second = ctx.validation.max_caption_chars_per_second
    for index, caption in enumerate(captions):
        duration_f = caption.end_f - caption.start_f
        if duration_f <= 0:
            continue
        duration_s = duration_f / fps
        allowed_chars = duration_s * max_chars_per_second
        actual_chars = len(caption.text.strip())
        if actual_chars > allowed_chars:
            diagnostics.append(
                Diagnostic(
                    code=VIR_CAPTION_UNDERFLOW,
                    message=(
                        f"caption[{index}] has {actual_chars} characters over "
                        f"{duration_s:.2f}s; limit is {allowed_chars:.1f}"
                    ),
                    help=(
                        "Increase the caption duration or raise "
                        "BuildContext.validation.max_caption_chars_per_second."
                    ),
                )
            )
    return diagnostics
