"""Grammar plugin contract and registry (M6, PR-1).

These cover the grammar-agnostic contract module: the registry's register/get
lifecycle and duplicate/missing errors, the :class:`AbstractObject` vocabulary's
strict validation, and the :class:`~viroc.ir.Box` geometry kernel that defines
"non-overlapping" and "within the safe frame". The ``pipeline`` grammar itself is
exercised in later slices.

The registry is process-global, so every test uses a unique grammar id and
asserts membership (never the full registry set) to stay independent of other
grammars registered elsewhere in the session.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from viroc.core import BuildContext
from viroc.grammars import (
    AbstractObject,
    LayoutGrammar,
    contains,
    get,
    is_registered,
    overlaps,
    register,
    registered_ids,
)
from viroc.ir import Box, ResolvedObject, Scene, SemanticIR


class _StubGrammar:
    """A minimal :class:`LayoutGrammar` for registry tests (no real layout)."""

    def __init__(self, grammar_id: str) -> None:
        self.id = grammar_id
        self.version = "0.0.0"

    def expand(self, scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
        return []

    def layout(
        self,
        objects: list[AbstractObject],
        resolution: tuple[int, int],
        ctx: BuildContext,
    ) -> list[ResolvedObject]:
        return []


def test_register_and_get_round_trip() -> None:
    """A registered grammar is retrievable by id and reported as registered."""
    grammar = _StubGrammar("reg_round_trip")
    register(grammar)
    assert get("reg_round_trip") is grammar
    assert is_registered("reg_round_trip")
    assert "reg_round_trip" in registered_ids()


def test_register_rejects_duplicate_id() -> None:
    """Registering a second grammar under a live id is a hard error."""
    register(_StubGrammar("reg_duplicate"))
    with pytest.raises(ValueError, match="already registered"):
        register(_StubGrammar("reg_duplicate"))


def test_get_unknown_grammar_raises() -> None:
    """Resolving an unregistered id raises rather than returning a default."""
    assert not is_registered("reg_never")
    with pytest.raises(KeyError, match="reg_never"):
        get("reg_never")


def test_stub_satisfies_layout_grammar_protocol() -> None:
    """The expand-to-layout surface is structural: a stub matches by shape."""
    assert isinstance(_StubGrammar("reg_protocol"), LayoutGrammar)


def test_abstract_object_forbids_unknown_fields() -> None:
    """The abstract-object vocabulary is closed (``extra='forbid'``)."""
    with pytest.raises(ValidationError):
        AbstractObject.model_validate(
            {"id": "x", "role": "node", "primitive": "rect", "style_ref": "s", "bogus": 1}
        )


def test_abstract_object_role_specific_fields_optional() -> None:
    """Role fields default to ``None`` so one flat set carries every role."""
    arrow = AbstractObject(
        id="a", role="arrow", primitive="arrow", style_ref="edge.flow", source="n1", target="n2"
    )
    assert arrow.text is None and arrow.owner is None
    assert (arrow.source, arrow.target) == ("n1", "n2")


def test_overlaps_detects_positive_area_only() -> None:
    """Overlap requires shared positive area; touching edges do not count."""
    a = Box(x=0, y=0, w=10, h=10)
    assert overlaps(a, Box(x=5, y=5, w=10, h=10))  # genuine overlap
    assert not overlaps(a, Box(x=10, y=0, w=10, h=10))  # edge-adjacent in x
    assert not overlaps(a, Box(x=0, y=10, w=10, h=10))  # edge-adjacent in y
    assert not overlaps(a, Box(x=20, y=20, w=5, h=5))  # disjoint


def test_contains_requires_full_containment() -> None:
    """Containment allows touching edges but rejects any protrusion."""
    frame = Box(x=0, y=0, w=100, h=100)
    assert contains(frame, Box(x=10, y=10, w=20, h=20))
    assert contains(frame, Box(x=0, y=0, w=100, h=100))  # flush with the frame
    assert not contains(frame, Box(x=90, y=90, w=20, h=20))  # spills past the edge
