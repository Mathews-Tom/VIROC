"""Concrete IR model validation (M5).

The Concrete IR (design §2.3) is renderer-neutral resolved data: boxes in logical
units and keyframes/captions in resolved frames. These tests pin the shapes and
the strict ``extra="forbid"`` config — the constrained vocabulary an adapter
lowers — without asserting any layout or timing behaviour (that lands in M6–M8).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from viroc.ir import (
    Box,
    Caption,
    ConcreteIR,
    Keyframe,
    ResolvedObject,
)


def _object(**overrides: object) -> ResolvedObject:
    """A minimal valid resolved object, overridable per test."""
    fields: dict[str, object] = {
        "id": "node.documents",
        "primitive": "rect",
        "box": Box(x=0.0, y=0.0, w=10.0, h=4.0),
        "style_ref": "node.default",
    }
    fields.update(overrides)
    return ResolvedObject.model_validate(fields)


def test_resolved_object_defaults_z_to_zero() -> None:
    """``z`` is optional and defaults to the back layer."""
    assert _object().z == 0


def test_box_coerces_int_coordinates_to_float() -> None:
    """Logical-unit coordinates are floats even when authored as ints."""
    box = Box.model_validate({"x": 1, "y": 2, "w": 3, "h": 4})
    assert (box.x, box.y, box.w, box.h) == (1.0, 2.0, 3.0, 4.0)
    assert all(isinstance(v, float) for v in (box.x, box.y, box.w, box.h))


def test_concrete_ir_round_trips() -> None:
    """A full Concrete IR survives a dump/validate round-trip unchanged."""
    ir = ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[_object()],
        keyframes=[
            Keyframe(
                object_id="node.documents",
                kind="fade_in",
                start_f=0,
                end_f=15,
                easing="ease_in_out",
            )
        ],
        captions=[Caption(text="Documents are chunked.", start_f=0, end_f=90)],
    )
    assert ConcreteIR.model_validate(ir.model_dump()) == ir


def test_resolution_validates_as_int_pair() -> None:
    """``resolution`` is a two-int tuple even when authored as a list."""
    ir = ConcreteIR.model_validate(
        {
            "fps": 30,
            "resolution": [1280, 720],
            "objects": [],
            "keyframes": [],
            "captions": [],
        }
    )
    assert ir.resolution == (1280, 720)


def test_invalid_primitive_is_rejected() -> None:
    """A primitive outside the design §2.3 literal set fails validation."""
    with pytest.raises(ValidationError):
        _object(primitive="video")


def test_invalid_keyframe_kind_is_rejected() -> None:
    """A keyframe kind outside the literal set fails validation."""
    with pytest.raises(ValidationError):
        Keyframe.model_validate(
            {
                "object_id": "node.documents",
                "kind": "zoom",
                "start_f": 0,
                "end_f": 1,
                "easing": "linear",
            }
        )


def test_invalid_easing_is_rejected() -> None:
    """An easing curve outside the literal set fails validation."""
    with pytest.raises(ValidationError):
        Keyframe.model_validate(
            {
                "object_id": "node.documents",
                "kind": "move",
                "start_f": 0,
                "end_f": 1,
                "easing": "bounce",
            }
        )


def test_missing_required_field_is_rejected() -> None:
    """A resolved object without its required ``style_ref`` fails validation."""
    with pytest.raises(ValidationError):
        ResolvedObject.model_validate(
            {
                "id": "node.documents",
                "primitive": "rect",
                "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            }
        )


def test_extra_field_is_forbidden() -> None:
    """An unexpected field is a hard error, never silently dropped."""
    with pytest.raises(ValidationError):
        Box.model_validate({"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "rotation": 90.0})
