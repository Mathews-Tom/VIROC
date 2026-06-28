"""The ``pipeline`` grammar's template layout (M6, PR-3).

Asserts the row template's structural guarantees on the §9.1 RAG scene: a uniform
node-box sized to the widest label, labels centered beneath their boxes, arrows in
the inter-box gaps, and — the milestone acceptance — zero pairwise overlap, every
box within the safe frame, and run-to-run determinism. The committed golden digest
is a later slice; here the properties are checked directly.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pytest

from viroc.core import BuildContext, BuildPaths
from viroc.grammars import AbstractObject, contains, overlaps
from viroc.grammars.pipeline.expand import expand
from viroc.grammars.pipeline.layout import GAP, PAD_X, layout, measure_text, safe_frame
from viroc.ir import ResolvedObject, SemanticIR

_RES = (1920, 1080)

_RAG: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {"id": "rag_overview", "title": "How RAG Works"},
    "entities": [
        {"id": "documents", "label": "Documents", "type": "data_source"},
        {"id": "chunks", "label": "Chunks", "type": "intermediate"},
        {"id": "embedder", "label": "Embedding Model", "type": "model"},
        {"id": "vector_db", "label": "Vector DB", "type": "storage"},
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


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-layout-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _objects() -> list[AbstractObject]:
    ir = SemanticIR.model_validate(_RAG)
    return expand(ir.scenes[0], ir)


def _layout() -> list[ResolvedObject]:
    return layout(_objects(), _RES, _ctx())


def _by_id(resolved: list[ResolvedObject]) -> dict[str, ResolvedObject]:
    return {obj.id: obj for obj in resolved}


def _nested(a: ResolvedObject, b: ResolvedObject) -> bool:
    """A text object fully contained in the other box is legitimate nesting."""
    if (a.primitive == "text") == (b.primitive == "text"):
        return False
    text, container = (a, b) if a.primitive == "text" else (b, a)
    return contains(container.box, text.box)


def test_measure_text_is_fixed_advance() -> None:
    """Measurement is a deterministic fixed-advance metric, font-independent."""
    assert measure_text("abcd")[0] == measure_text("wxyz")[0]
    assert measure_text("ab")[0] < measure_text("abcd")[0]


def test_layout_emits_one_box_per_abstract_object() -> None:
    """Every abstract object is placed: 4 nodes + 4 labels + 3 arrows = 11."""
    resolved = _layout()
    assert len(resolved) == len(_objects()) == 11
    assert {obj.id for obj in resolved} == {obj.id for obj in _objects()}


def test_node_boxes_are_uniform_and_fit_widest_label() -> None:
    """A node-box is sized to the widest label plus padding, applied uniformly."""
    by_id = _by_id(_layout())
    widest = measure_text("Embedding Model")[0]
    expected_w = widest + 2 * PAD_X
    node_ids = ["documents", "chunks", "embedder", "vector_db"]
    for node in node_ids:
        assert by_id[f"pipeline.{node}.box"].box.w == expected_w


def test_labels_sit_centered_inside_their_box() -> None:
    """Each label is placed inside its node-box and horizontally centered in it."""
    by_id = _by_id(_layout())
    box = by_id["pipeline.documents.box"].box
    label = by_id["pipeline.documents.label"].box
    assert box.y <= label.y and label.y + label.h <= box.y + box.h  # inside the box
    box_center = box.x + box.w / 2
    label_center = label.x + label.w / 2
    assert box_center == label_center  # centered in the box


def test_arrows_occupy_the_inter_box_gap() -> None:
    """An arrow spans exactly the gap between its endpoint boxes (width GAP)."""
    by_id = _by_id(_layout())
    arrow = by_id["pipeline.documents.chunks.arrow"].box
    src = by_id["pipeline.documents.box"].box
    tgt = by_id["pipeline.chunks.box"].box
    assert arrow.x == src.x + src.w
    assert arrow.x + arrow.w == tgt.x
    assert arrow.w == GAP


def test_layout_has_zero_pairwise_overlap() -> None:
    """No two resolved boxes overlap, except a label nested inside its node-box."""
    resolved = _layout()
    collisions = [
        (a.id, b.id)
        for a, b in combinations(resolved, 2)
        if overlaps(a.box, b.box) and not _nested(a, b)
    ]
    assert collisions == []


def test_layout_stays_within_safe_frame() -> None:
    """Every resolved box lies within the safe frame inset from the resolution."""
    frame = safe_frame(_RES)
    assert all(contains(frame, obj.box) for obj in _layout())


def test_layout_is_deterministic() -> None:
    """The same objects lay out to the identical resolved set across runs."""
    assert _layout() == _layout()


def test_layout_rejects_arrow_to_unplaced_node() -> None:
    """An arrow whose endpoint is not a laid-out node fails with a clear error."""
    objects = [
        AbstractObject(id="s.box", role="node", primitive="rect", style_ref="node.x"),
        AbstractObject(
            id="a.arrow",
            role="arrow",
            primitive="arrow",
            style_ref="edge.flow",
            source="s.box",
            target="ghost.box",
        ),
    ]
    with pytest.raises(ValueError, match="ghost.box"):
        layout(objects, _RES, _ctx())
