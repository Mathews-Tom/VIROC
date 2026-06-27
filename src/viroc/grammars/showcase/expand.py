"""The ``showcase`` grammar's expansion step (design §4, pipeline phase P5).

Expansion turns an authored explainer scene into the renderer-neutral abstract
objects :func:`~viroc.grammars.showcase.layout.layout` will place. Unlike the
``pipeline`` grammar — which emits one row of node-boxes joined by drawn arrows —
``showcase`` emits, per scene node, a *primary* composition box plus its *title*
label, where the box's primitive is chosen by the entity's composition kind
(panel/callout -> ``rect``, code card -> ``code``, evidence block -> ``formula``;
see :data:`~viroc.grammars.showcase.COMPOSITION_KINDS`).

Edges expand into ``arrow`` abstract objects that carry connectivity only: they
are the channel the layout phase reads to pick a non-row template (a ``compare``
edge selects the comparison layout; a node sourcing two or more edges selects the
fan-out layout) and to assign columns. The layout phase decides which, if any, of
those connectors it draws — the showcase relationship is carried by placement,
not only by glyphs.

Object ids derive from :func:`~viroc.core.stable_id`, so they are deterministic
and stable across runs. Expansion expects a normalized Semantic IR, reads entity
labels/types by id, and never mutates its input. It is pure and byte-stable.
"""

from __future__ import annotations

from viroc.core import stable_id
from viroc.grammars import AbstractObject
from viroc.grammars.showcase import (
    COMPOSITION_KINDS,
    KIND_PRIMITIVES,
    TITLE_STYLE_REF,
)
from viroc.ir import Scene, SemanticIR


def expand(scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
    """Expand ``scene`` into composition primaries, title labels, and connectors.

    The returned order is deterministic: each node's primary box then its title
    label, in ``scene.nodes`` order, followed by one connector per edge in
    ``scene.edges`` order. A node names an entity declared in ``ir.entities``; its
    composition kind, label, and lowered primitive come from that entity's type.
    """
    entities = {entity.id: entity for entity in ir.entities}

    objects: list[AbstractObject] = []
    for node_id in scene.nodes:
        entity = entities[node_id]
        kind = COMPOSITION_KINDS[entity.type]
        primary_id = stable_id(scene.id, node_id, kind)
        objects.append(
            AbstractObject(
                id=primary_id,
                role="node",
                primitive=KIND_PRIMITIVES[kind],
                style_ref=f"{kind}.{entity.type}",
            )
        )
        objects.append(
            AbstractObject(
                id=stable_id(scene.id, node_id, "title"),
                role="label",
                primitive="text",
                style_ref=TITLE_STYLE_REF,
                text=entity.label,
                owner=primary_id,
            )
        )

    for edge in scene.edges:
        source_entity = entities[edge.from_]
        target_entity = entities[edge.to]
        objects.append(
            AbstractObject(
                id=stable_id(scene.id, edge.from_, edge.to, "link"),
                role="arrow",
                primitive="arrow",
                style_ref=f"edge.{edge.kind}",
                source=stable_id(scene.id, edge.from_, COMPOSITION_KINDS[source_entity.type]),
                target=stable_id(scene.id, edge.to, COMPOSITION_KINDS[target_entity.type]),
            )
        )

    return objects
