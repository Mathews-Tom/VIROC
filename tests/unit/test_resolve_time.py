"""Timeline resolve — phase P7 (M7, PR-1).

Covers the v1 time grammar: absolute ``"Ns"`` → frames, simple-relative
``after(<id>.end)`` with optional fixed offset, and the hard-reject of anything
out of that grammar (``VIR2001``) or anchored on an unknown beat (``VIR2002``).
The whole-scene :func:`resolve_beats` driver is checked for sequential chaining,
per-beat diagnostics, and determinism.
"""

from __future__ import annotations

import pytest

from viroc.compiler.resolve_time import (
    VIR_UNKNOWN_ANCHOR,
    VIR_UNSUPPORTED_TIME,
    ResolvedBeat,
    frames_for_seconds,
    resolve_at,
    resolve_beats,
)
from viroc.core import Diagnostic
from viroc.ir import Beat

_FPS = 30


def test_frames_for_seconds_rounds_to_frames() -> None:
    """An absolute "Ns" duration converts to round(seconds * fps) frames."""
    assert frames_for_seconds("4s", _FPS) == 120
    assert frames_for_seconds("35s", _FPS) == 1050
    assert frames_for_seconds("1.5s", _FPS) == 45


def test_frames_for_seconds_rejects_malformed() -> None:
    """A non-"Ns" duration raises rather than silently coercing."""
    with pytest.raises(ValueError, match="ambiguous duration"):
        frames_for_seconds("4", _FPS)


def test_resolve_at_absolute() -> None:
    """A bare "Ns" time resolves with no anchors."""
    assert resolve_at("4s", _FPS, ends={}, prev_end=None) == 120


def test_resolve_at_after_named_anchor() -> None:
    """after(<id>.end) resolves to that beat's recorded end frame."""
    assert resolve_at("after(intro.end)", _FPS, ends={"intro": 120}, prev_end=120) == 120


def test_resolve_at_after_prev_keyword() -> None:
    """The reserved ``prev`` anchor resolves to the previous beat's end."""
    assert resolve_at("after(prev.end)", _FPS, ends={}, prev_end=90) == 90


def test_resolve_at_positive_offset() -> None:
    """A "+Ns" offset adds frames onto the anchor end."""
    assert resolve_at("after(prev.end) + 2s", _FPS, ends={}, prev_end=120) == 180


def test_resolve_at_negative_offset() -> None:
    """A "-Ns" offset subtracts frames from the anchor end."""
    assert resolve_at("after(intro.end) - 1s", _FPS, ends={"intro": 120}, prev_end=120) == 90


@pytest.mark.parametrize(
    "expr",
    ["4", "before(intro.end)", "between(a.end, b.end)", "after(intro.start)", "after(a.end) + 2"],
)
def test_resolve_at_rejects_out_of_grammar(expr: str) -> None:
    """Anything outside absolute/simple-relative is VIR2001, not half-solved."""
    result = resolve_at(expr, _FPS, ends={"intro": 120, "a": 60}, prev_end=120)
    assert isinstance(result, Diagnostic)
    assert result.code == VIR_UNSUPPORTED_TIME


def test_resolve_at_unknown_anchor() -> None:
    """A well-formed after() on a non-existent beat is VIR2002."""
    result = resolve_at("after(ghost.end)", _FPS, ends={"intro": 120}, prev_end=120)
    assert isinstance(result, Diagnostic)
    assert result.code == VIR_UNKNOWN_ANCHOR


def test_resolve_beats_chains_sequentially() -> None:
    """Beats resolve in order; a later beat anchors on an earlier one's end."""
    beats = [
        Beat(id="intro", at="0s", duration="4s", narration="hello"),
        Beat(id="body", at="after(intro.end)", duration="6s"),
        Beat(id="outro", at="after(prev.end) + 1s", duration="2s"),
    ]
    resolved, diagnostics = resolve_beats(beats, _FPS)
    assert diagnostics == []
    assert resolved == [
        ResolvedBeat(id="intro", start_f=0, end_f=120, narration="hello"),
        ResolvedBeat(id="body", start_f=120, end_f=300, narration=None),
        ResolvedBeat(id="outro", start_f=330, end_f=390, narration=None),
    ]


def test_resolve_beats_skips_a_bad_beat() -> None:
    """One out-of-grammar beat yields one diagnostic; the rest still resolve."""
    beats = [
        Beat(id="intro", at="0s", duration="4s"),
        Beat(id="bad", at="between(intro.end, outro.end)", duration="4s"),
        Beat(id="tail", at="after(intro.end)", duration="2s"),
    ]
    resolved, diagnostics = resolve_beats(beats, _FPS)
    assert [diag.code for diag in diagnostics] == [VIR_UNSUPPORTED_TIME]
    assert [rb.id for rb in resolved] == ["intro", "tail"]


def test_resolve_beats_flags_a_bad_duration() -> None:
    """A non-"Ns" beat duration is VIR2001, not a crash."""
    resolved, diagnostics = resolve_beats([Beat(id="b", at="0s", duration="4")], _FPS)
    assert resolved == []
    assert [diag.code for diag in diagnostics] == [VIR_UNSUPPORTED_TIME]


def test_resolve_beats_is_deterministic() -> None:
    """Resolving the same beats twice yields the identical windows."""
    beats = [
        Beat(id="intro", at="0s", duration="4s"),
        Beat(id="body", at="after(prev.end)", duration="6s"),
    ]
    assert resolve_beats(beats, _FPS) == resolve_beats(beats, _FPS)
