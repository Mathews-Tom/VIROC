"""The ``pipeline`` grammar's expansion step (design §4, pipeline phase P5).

Expansion turns a semantic scene into a flat set of *abstract objects* — the
renderer-neutral, position-free drawables :func:`~viroc.grammars.pipeline.layout`
will place (design §4: "a ``pipeline`` becomes node-boxes + connecting arrows +
labels"). For each scene node it emits a node-box (``rect``) and the entity's
label (``text``) anchored to that box; for each edge it emits an arrow whose
``source``/``target`` name the connected node-box ids.

Object ids are derived with :func:`~viroc.core.stable_id`, so they are
deterministic and stable across runs (``pipeline.documents.box``,
``pipeline.documents.chunks.arrow``). Style references encode taste an adapter
can theme: a node-box by entity type (``node.storage``), a label uniformly
(``label``), an arrow by edge kind (``edge.store``).

Expansion expects a normalized Semantic IR (ids already slug form, references
rewritten — pipeline phase P3): it reads entity labels/types by id and never
mutates its input. It is pure and byte-stable.
"""

from __future__ import annotations

from viroc.core import stable_id
from viroc.grammars import AbstractObject
from viroc.ir import Scene, SemanticIR


def expand(scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
    """Expand ``scene`` into node-boxes, node-labels, and connecting arrows.

    The returned order is deterministic: each node's box then its label, in
    ``scene.nodes`` order, followed by one arrow per edge in ``scene.edges``
    order. A node names an entity declared in ``ir.entities``; its label and type
    come from that entity.
    """
    entities = {entity.id: entity for entity in ir.entities}

    objects: list[AbstractObject] = []
    for node_id in scene.nodes:
        entity = entities[node_id]
        box_id = stable_id(scene.id, node_id, "box")
        objects.append(
            AbstractObject(
                id=box_id,
                role="node",
                primitive="rect",
                style_ref=f"node.{entity.type}",
            )
        )
        objects.append(
            AbstractObject(
                id=stable_id(scene.id, node_id, "label"),
                role="label",
                primitive="text",
                style_ref="label",
                text=entity.label,
                owner=box_id,
            )
        )

    for edge in scene.edges:
        objects.append(
            AbstractObject(
                id=stable_id(scene.id, edge.from_, edge.to, "arrow"),
                role="arrow",
                primitive="arrow",
                style_ref=f"edge.{edge.kind}",
                source=stable_id(scene.id, edge.from_, "box"),
                target=stable_id(scene.id, edge.to, "box"),
            )
        )

    return objects
