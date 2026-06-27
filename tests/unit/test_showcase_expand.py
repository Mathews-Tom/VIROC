"""Unit coverage for the showcase grammar's expansion step (M19, PR-1)."""

from __future__ import annotations

from viroc.grammars.showcase import COMPOSITION_KINDS, TITLE_STYLE_REF
from viroc.grammars.showcase.expand import expand
from viroc.ir import Edge, Entity, Scene, SemanticIR, VideoMeta


def _ir() -> SemanticIR:
    """A small storyboard exercising every composition kind and an edge."""
    return SemanticIR(
        vidir_version="0.1",
        video=VideoMeta(id="v", title="t"),
        entities=[
            Entity(id="sources", label="Sources", type="data_source"),
            Entity(id="ir_blob", label="Semantic IR", type="intermediate"),
            Entity(id="author", label="Author", type="user"),
            Entity(id="proof", label="Source hashes", type="storage"),
        ],
        scenes=[
            Scene(
                id="composition",
                grammar="showcase",
                duration="6s",
                nodes=["sources", "ir_blob", "author", "proof"],
                edges=[
                    Edge.model_validate(
                        {"from": "sources", "to": "ir_blob", "kind": "compare"}
                    )
                ],
            )
        ],
    )


def test_expand_emits_primary_then_title_per_node_in_order() -> None:
    """Each node yields a primary box then its title label, in node order."""
    ir = _ir()
    objects = expand(ir.scenes[0], ir)

    nodes = [obj for obj in objects if obj.role == "node"]
    assert [obj.id for obj in nodes] == [
        "composition.sources.panel",
        "composition.ir_blob.code_card",
        "composition.author.callout",
        "composition.proof.evidence",
    ]
    assert all(node.role == "node" for node in nodes)


def test_expand_lowers_kind_to_concrete_primitive() -> None:
    """Composition kind drives the lowered primitive: rect/code/formula."""
    ir = _ir()
    by_id = {obj.id: obj for obj in expand(ir.scenes[0], ir)}

    assert by_id["composition.sources.panel"].primitive == "rect"
    assert by_id["composition.ir_blob.code_card"].primitive == "code"
    assert by_id["composition.author.callout"].primitive == "rect"
    assert by_id["composition.proof.evidence"].primitive == "formula"


def test_expand_titles_own_their_primary_and_carry_label_text() -> None:
    """Every node carries a text title label owned by its primary box."""
    ir = _ir()
    objects = expand(ir.scenes[0], ir)

    titles = [obj for obj in objects if obj.role == "label"]
    assert [obj.id for obj in titles] == [
        "composition.sources.title",
        "composition.ir_blob.title",
        "composition.author.title",
        "composition.proof.title",
    ]
    sources_title = next(obj for obj in titles if obj.id == "composition.sources.title")
    assert sources_title.primitive == "text"
    assert sources_title.style_ref == TITLE_STYLE_REF
    assert sources_title.text == "Sources"
    assert sources_title.owner == "composition.sources.panel"


def test_expand_styles_primary_by_kind_and_entity_type() -> None:
    """A primary's style ref names its composition kind and the entity type."""
    ir = _ir()
    by_id = {obj.id: obj for obj in expand(ir.scenes[0], ir)}

    assert by_id["composition.sources.panel"].style_ref == "panel.data_source"
    assert by_id["composition.ir_blob.code_card"].style_ref == "code_card.intermediate"
    assert by_id["composition.proof.evidence"].style_ref == "evidence.storage"


def test_expand_emits_one_connector_per_edge_with_endpoints() -> None:
    """Edges become arrow connectors naming the primary ids they link."""
    ir = _ir()
    objects = expand(ir.scenes[0], ir)

    arrows = [obj for obj in objects if obj.role == "arrow"]
    assert len(arrows) == 1
    arrow = arrows[0]
    assert arrow.id == "composition.sources.ir_blob.link"
    assert arrow.primitive == "arrow"
    assert arrow.style_ref == "edge.compare"
    assert arrow.source == "composition.sources.panel"
    assert arrow.target == "composition.ir_blob.code_card"


def test_expand_is_deterministic() -> None:
    """Expanding the same scene twice yields identical objects."""
    ir = _ir()
    first = [obj.model_dump() for obj in expand(ir.scenes[0], ir)]
    second = [obj.model_dump() for obj in expand(ir.scenes[0], ir)]
    assert first == second


def test_composition_kinds_cover_every_entity_type() -> None:
    """The kind map is total over the EntityType set the IR admits."""
    entity_types = {
        "data_source",
        "intermediate",
        "model",
        "storage",
        "service",
        "user",
    }
    assert set(COMPOSITION_KINDS) == entity_types
