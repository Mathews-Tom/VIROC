"""The ``pipeline`` grammar's expansion (M6, PR-2).

Asserts the design §9.1 RAG scene expands into the expected abstract object set —
a node-box and a label per node (in node order), then one arrow per edge — with
deterministic ids, entity-driven labels/styles, and arrow endpoints wired to the
node-box ids. Layout (placing these into boxes) is a later slice.
"""

from __future__ import annotations

from viroc.grammars import AbstractObject
from viroc.grammars.pipeline.expand import expand
from viroc.ir import SemanticIR

# The §9.1 RAG scene, already in normalized (slug) id form.
_RAG: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {"id": "rag_overview", "title": "How RAG Works"},
    "entities": [
        {"id": "documents", "label": "Documents", "type": "data_source"},
        {"id": "chunks", "label": "Chunks", "type": "intermediate"},
        {"id": "embedder", "label": "Embedding Model", "type": "model"},
        {"id": "vector_db", "label": "Vector DB", "type": "storage"},
        {"id": "llm", "label": "LLM", "type": "model"},
    ],
    "scenes": [
        {
            "id": "pipeline",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["documents", "chunks", "embedder", "vector_db"],
            "edges": [
                {"from": "documents", "to": "chunks", "kind": "split"},
                {"from": "chunks", "to": "embedder", "kind": "transform"},
                {"from": "embedder", "to": "vector_db", "kind": "store"},
            ],
        }
    ],
}


def _expand() -> list[AbstractObject]:
    ir = SemanticIR.model_validate(_RAG)
    return expand(ir.scenes[0], ir)


def _by_id(objects: list[AbstractObject]) -> dict[str, AbstractObject]:
    return {obj.id: obj for obj in objects}


def test_expands_to_box_label_per_node_then_arrow_per_edge() -> None:
    """Four nodes (box + label each) and three edges (an arrow each): 11 objects."""
    objects = _expand()
    assert len(objects) == 11
    roles = [obj.role for obj in objects]
    # box, label per node in node order, then all arrows.
    assert roles == ["node", "label"] * 4 + ["arrow"] * 3


def test_object_ids_are_stable_and_namespaced() -> None:
    """Ids are scene-namespaced and derived deterministically from the parts."""
    by_id = _by_id(_expand())
    assert "pipeline.documents.box" in by_id
    assert "pipeline.vector_db.label" in by_id
    assert "pipeline.embedder.vector_db.arrow" in by_id


def test_node_box_carries_entity_type_style() -> None:
    """A node-box is a rect styled by its entity's type, no text of its own."""
    box = _by_id(_expand())["pipeline.vector_db.box"]
    assert (box.role, box.primitive, box.style_ref) == ("node", "rect", "node.storage")
    assert box.text is None


def test_label_uses_entity_label_and_owns_its_box() -> None:
    """A label is text carrying the entity label, anchored to its node-box."""
    label = _by_id(_expand())["pipeline.embedder.label"]
    assert (label.role, label.primitive) == ("label", "text")
    assert label.text == "Embedding Model"  # the entity label, not the id
    assert label.owner == "pipeline.embedder.box"


def test_arrow_wires_box_endpoints_and_edge_kind() -> None:
    """An arrow connects the source/target node-boxes and styles by edge kind."""
    arrow = _by_id(_expand())["pipeline.documents.chunks.arrow"]
    assert (arrow.role, arrow.primitive, arrow.style_ref) == ("arrow", "arrow", "edge.split")
    assert arrow.source == "pipeline.documents.box"
    assert arrow.target == "pipeline.chunks.box"


def test_expansion_is_deterministic() -> None:
    """The same scene expands to the identical object list across runs."""
    assert _expand() == _expand()
