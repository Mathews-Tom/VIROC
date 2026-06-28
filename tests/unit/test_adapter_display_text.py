"""Shared emitter display-text derivation (``viroc.adapters._text``).

Resolved objects carry no glyph text, so every backend derives an object's text
from its stable id. This pins that single source of truth, including the
regression that a ``showcase`` card title is the entity name, not the literal
word ``"Title"``.
"""

from __future__ import annotations

from viroc.adapters._text import display_text
from viroc.adapters.html.emit import source_for
from viroc.ir import Box, ConcreteIR, ResolvedObject


def _text_object(object_id: str) -> ResolvedObject:
    return ResolvedObject(
        id=object_id,
        primitive="text",
        box=Box(x=0.0, y=0.0, w=10.0, h=10.0),
        style_ref="showcase.title",
    )


def test_title_role_renders_preceding_entity_segment() -> None:
    assert display_text(_text_object("validation.semantic_ir.title")) == "Semantic Ir"


def test_label_role_renders_preceding_entity_segment() -> None:
    assert display_text(_text_object("rag.vector_db.label")) == "Vector Db"


def test_plain_id_renders_its_final_segment() -> None:
    assert display_text(_text_object("fanout.resolver.panel")) == "Panel"


def test_showcase_title_is_never_the_literal_role_word() -> None:
    assert display_text(_text_object("primitives.input_panel.title")) == "Input Panel"


def test_html_emit_renders_showcase_title_from_node_id() -> None:
    """The defect this fixes: a showcase title used to render ``<span>Title</span>``."""
    ir = ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=[_text_object("validation.semantic_ir.title")],
        keyframes=[],
        captions=[],
    )
    source = source_for(ir)
    assert ">Semantic Ir</span>" in source
    assert ">Title</span>" not in source
