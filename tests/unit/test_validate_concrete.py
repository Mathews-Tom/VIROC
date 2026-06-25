"""Post-resolve Concrete IR validation — pipeline phase P9."""

from __future__ import annotations

from pathlib import Path

from viroc.core import BuildContext, BuildPaths, ValidationThresholds
from viroc.ir import Box, Caption, ConcreteIR, Keyframe, ResolvedObject
from viroc.validators.timing import (
    VIR_BEAT_OVERLAP,
    VIR_CAPTION_UNDERFLOW,
    VIR_IMPOSSIBLE_DURATION,
    validate_timing,
)


def _ctx(
    *,
    safe_margin_pct: float = 5.0,
    min_text_box_width: float = 1.0,
    min_text_box_height: float = 1.0,
    max_caption_chars_per_second: float = 18.0,
) -> BuildContext:
    thresholds = ValidationThresholds(
        safe_margin_pct=safe_margin_pct,
        min_text_box_width=min_text_box_width,
        min_text_box_height=min_text_box_height,
        max_caption_chars_per_second=max_caption_chars_per_second,
    )
    return BuildContext(
        paths=BuildPaths(
            project_root=Path("/tmp/viroc-validate"), out_dir=Path("/tmp/out")
        ),
        validation=thresholds,
    )


def _object(**overrides: object) -> ResolvedObject:
    fields: dict[str, object] = {
        "id": "scene.node",
        "primitive": "rect",
        "box": Box(x=100.0, y=100.0, w=200.0, h=120.0),
        "style_ref": "node.default",
    }
    fields.update(overrides)
    return ResolvedObject.model_validate(fields)


def _keyframe(**overrides: object) -> Keyframe:
    fields: dict[str, object] = {
        "object_id": "scene.node",
        "kind": "fade_in",
        "start_f": 0,
        "end_f": 30,
        "easing": "linear",
    }
    fields.update(overrides)
    return Keyframe.model_validate(fields)


def _caption(**overrides: object) -> Caption:
    fields: dict[str, object] = {"text": "short caption", "start_f": 0, "end_f": 90}
    fields.update(overrides)
    return Caption.model_validate(fields)


def _concrete(
    *,
    keyframes: list[Keyframe] | None = None,
    captions: list[Caption] | None = None,
) -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[_object()],
        keyframes=keyframes if keyframes is not None else [_keyframe()],
        captions=captions if captions is not None else [_caption()],
    )


def test_clean_timing_ir_has_zero_diagnostics() -> None:
    """A feasible Concrete IR emits no timing diagnostics."""
    assert validate_timing(_concrete(), _ctx()) == []


def test_overlapping_beat_windows_emit_vir2xxx() -> None:
    """Same-object animation windows cannot overlap in resolved time."""
    ir = _concrete(
        keyframes=[
            _keyframe(kind="fade_in", start_f=0, end_f=40),
            _keyframe(kind="highlight", start_f=30, end_f=60),
        ]
    )

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_BEAT_OVERLAP]


def test_impossible_or_zero_duration_emits_vir2xxx() -> None:
    """Resolved frame windows must be non-negative and non-empty."""
    ir = _concrete(keyframes=[_keyframe(start_f=10, end_f=10)])

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_IMPOSSIBLE_DURATION]


def test_over_long_caption_emits_underflow_vir2xxx() -> None:
    """Caption text must fit within its authored resolved duration."""
    ir = _concrete(captions=[_caption(text="x" * 40, start_f=0, end_f=30)])

    assert [diag.code for diag in validate_timing(ir, _ctx())] == [VIR_CAPTION_UNDERFLOW]


def test_caption_underflow_threshold_is_configurable() -> None:
    """Caption underflow uses BuildContext validation thresholds, not constants."""
    ir = _concrete(captions=[_caption(text="x" * 40, start_f=0, end_f=30)])

    assert validate_timing(ir, _ctx(max_caption_chars_per_second=60.0)) == []
