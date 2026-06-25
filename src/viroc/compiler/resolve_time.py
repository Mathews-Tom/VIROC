"""Timeline resolve — pipeline phase P7 (design §3, §10).

The timeline resolver turns authored time expressions into absolute frame
positions, the form the Concrete IR (:class:`~viroc.ir.Keyframe`,
:class:`~viroc.ir.Caption`) and every downstream renderer speak.

v1 deliberately supports only the *simple-relative* time grammar the de-risking
gate validated (overview §5 Risk #7, design §10 open question), held to exactly
two shapes:

- **absolute** — an ``"Ns"`` duration (``"4s"``, ``"1.5s"``) → ``round(N * fps)``
  frames.
- **simple relative** — ``after(<id>.end)`` anchored on a prior beat's end, with
  an optional fixed ``+Ns`` / ``-Ns`` offset (``"after(intro.end) + 2s"``). The
  reserved anchor ``prev`` names the immediately-preceding beat.

Anything else — a bare number, ``before(...)``, multiple anchors, arithmetic
between anchors, anything that would need a constraint solver — is *rejected*,
not half-solved: it yields a :data:`VIR_UNSUPPORTED_TIME` (``VIR2001``)
diagnostic. A well-formed ``after(<id>.end)`` whose anchor is not a prior beat
yields :data:`VIR_UNKNOWN_ANCHOR` (``VIR2002``). Hard-rejecting keeps phase P7 a
pure, total function with no hidden solver (design §10).

Everything here is integer arithmetic over a fixed ``fps``, so the resolved
frames are byte-stable across runs and machines — the determinism the golden
Concrete IR depends on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from viroc.compiler.normalize import parse_duration
from viroc.core import Diagnostic, DiagnosticClass, code
from viroc.ir import Beat

VIR_UNSUPPORTED_TIME = code(DiagnosticClass.TIMING, 1)
"""A time expression is outside the v1 absolute + simple-relative grammar."""

VIR_UNKNOWN_ANCHOR = code(DiagnosticClass.TIMING, 2)
"""An ``after(<id>.end)`` anchor names no prior beat (and is not ``prev``)."""

_PREV = "prev"
"""The reserved anchor naming the immediately-preceding beat."""

# A well-formed simple-relative expression: after(<anchor>.end) with an optional
# fixed +Ns / -Ns offset. <anchor> is a slug id (matching normalized beat ids).
_AFTER_RE = re.compile(
    r"^after\(\s*(?P<anchor>[a-z0-9_]+)\.end\s*\)"
    r"(?:\s*(?P<sign>[+-])\s*(?P<offset>\d+(?:\.\d+)?s))?$"
)


@dataclass(frozen=True, slots=True)
class ResolvedBeat:
    """A beat resolved to an absolute ``[start_f, end_f)`` frame window.

    ``narration`` is carried through verbatim so the assembly phase can lower a
    narrated beat to a :class:`~viroc.ir.Caption` over the same window without
    re-resolving anything. ``end_f`` is ``start_f`` plus the beat's authored
    duration in frames.
    """

    id: str
    start_f: int
    end_f: int
    narration: str | None


def frames_for_seconds(text: str, fps: int) -> int:
    """Resolve an absolute ``"Ns"`` duration to a frame count.

    ``round(seconds * fps)`` — deterministic for a fixed ``fps``. Raises
    :class:`ValueError` on anything that is not an ``"Ns"`` duration, so a
    malformed *trusted* duration (a scene span) fails loudly rather than
    silently coercing. Authored beat fields route through the diagnostic-bearing
    helpers below instead of raising.
    """
    return round(parse_duration(text) * fps)


def _absolute_frames(text: str, fps: int) -> int | None:
    """Resolve an absolute ``"Ns"`` duration, or ``None`` if it is not one."""
    try:
        return frames_for_seconds(text, fps)
    except ValueError:
        return None


def resolve_at(
    expr: str,
    fps: int,
    *,
    ends: dict[str, int],
    prev_end: int | None,
) -> int | Diagnostic:
    """Resolve a beat ``at`` time-point expression to an absolute start frame.

    Accepts an absolute ``"Ns"`` time or a simple-relative ``after(<id>.end)``
    with an optional fixed offset; ``ends`` maps already-resolved beat ids to
    their end frame and ``prev_end`` is the previous beat's end (for the reserved
    ``prev`` anchor). Returns the absolute start frame, or a :class:`Diagnostic`
    for an out-of-grammar expression (``VIR2001``) or an unknown anchor
    (``VIR2002``).
    """
    text = expr.strip()

    absolute = _absolute_frames(text, fps)
    if absolute is not None:
        return absolute

    match = _AFTER_RE.fullmatch(text)
    if match is None:
        return Diagnostic(
            code=VIR_UNSUPPORTED_TIME,
            message=f"unsupported time expression {expr!r}",
            help=(
                'v1 supports only an absolute "Ns" time or a relative '
                '"after(<id>.end)" with an optional fixed "+Ns"/"-Ns" offset'
            ),
        )

    anchor = match.group("anchor")
    base = prev_end if anchor == _PREV else ends.get(anchor)
    if base is None:
        return Diagnostic(
            code=VIR_UNKNOWN_ANCHOR,
            message=f'unknown time anchor "{anchor}" in {expr!r}',
            help="after(<id>.end) must reference an earlier beat in this scene",
        )

    offset_text = match.group("offset")
    if offset_text is None:
        return base
    offset = frames_for_seconds(offset_text, fps)
    return base - offset if match.group("sign") == "-" else base + offset


def resolve_beats(
    beats: list[Beat], fps: int
) -> tuple[list[ResolvedBeat], list[Diagnostic]]:
    """Resolve a scene's beats to absolute frame windows, in authored order.

    Each beat's ``at`` is resolved against the windows of the beats before it
    (so ``after(prev.end)`` and ``after(<earlier-id>.end)`` work), and its end is
    ``start`` plus the authored ``duration`` in frames. A beat whose ``at`` or
    ``duration`` is out of grammar is skipped with a ``VIR2xxx`` diagnostic; the
    remaining beats still resolve, so a single bad beat produces one diagnostic
    rather than aborting the scene.
    """
    resolved: list[ResolvedBeat] = []
    diagnostics: list[Diagnostic] = []
    ends: dict[str, int] = {}
    prev_end: int | None = None

    for beat in beats:
        start = resolve_at(beat.at, fps, ends=ends, prev_end=prev_end)
        if isinstance(start, Diagnostic):
            diagnostics.append(start)
            continue
        duration = _absolute_frames(beat.duration, fps)
        if duration is None:
            diagnostics.append(
                Diagnostic(
                    code=VIR_UNSUPPORTED_TIME,
                    message=f'beat "{beat.id}" has an unparseable duration {beat.duration!r}',
                    help='a beat duration must be an absolute "Ns" value, e.g. "4s"',
                )
            )
            continue
        end = start + duration
        resolved.append(
            ResolvedBeat(id=beat.id, start_f=start, end_f=end, narration=beat.narration)
        )
        ends[beat.id] = end
        prev_end = end

    return resolved, diagnostics
