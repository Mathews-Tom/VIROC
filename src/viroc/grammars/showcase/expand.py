"""The ``showcase`` grammar's expansion step (design §4, pipeline phase P5).

Expansion turns an authored explainer scene into the renderer-neutral abstract
objects :func:`~viroc.grammars.showcase.layout.layout` will place. Unlike the
``pipeline`` grammar — which emits one row of node-boxes joined by drawn arrows —
``showcase`` emits, per *box* scene node, a *primary* composition box plus the
content it carries:

- a *title* label (the entity ``label``) rendered inside the box;
- one *body* label per ``entity.body`` line, stacked inside the box under the
  title (real code lines for a code card, evidence/hash lines for an evidence
  block, descriptive body for a panel);
- an optional *detail* label (``entity.detail``) rendered beneath the box.

A node whose entity type lowers to the ``text`` primitive (``heading`` /
``statement``) carries no box: its primary *is* the text, so a title card or a
centered claim is standalone typography with no label/body/detail of its own.

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
    DETAIL_STYLE_REF,
    KIND_PRIMITIVES,
    TEXT_KIND_STYLE_REFS,
    TITLE_STYLE_REF,
    body_style_ref,
)
from viroc.ir import Scene, SemanticIR


def expand(scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
    """Expand ``scene`` into composition primaries, their content, and connectors.

    The returned order is deterministic: per ``scene.nodes`` entry, the primary
    box then its title, body lines, and detail (the content it owns), followed by
    one connector per edge in ``scene.edges`` order. A node names an entity
    declared in ``ir.entities``; its composition kind, label, body, detail, and
    lowered primitive come from that entity. A text-primary node (``heading`` /
    ``statement``) emits a single standalone text object.
    """
    entities = {entity.id: entity for entity in ir.entities}

    objects: list[AbstractObject] = []
    for node_id in scene.nodes:
        entity = entities[node_id]
        kind = COMPOSITION_KINDS[entity.type]
        primitive = KIND_PRIMITIVES[kind]
        primary_id = stable_id(scene.id, node_id, kind)

        if primitive == "text":
            objects.append(
                AbstractObject(
                    id=primary_id,
                    role="node",
                    primitive="text",
                    style_ref=TEXT_KIND_STYLE_REFS[kind],
                    text=entity.label,
                )
            )
            continue

        objects.append(
            AbstractObject(
                id=primary_id,
                role="node",
                primitive=primitive,
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
        for index, line in enumerate(entity.body):
            objects.append(
                AbstractObject(
                    id=stable_id(scene.id, node_id, "body", str(index)),
                    role="label",
                    primitive="text",
                    style_ref=body_style_ref(kind),
                    text=line,
                    owner=primary_id,
                )
            )
        if entity.detail is not None:
            objects.append(
                AbstractObject(
                    id=stable_id(scene.id, node_id, "detail"),
                    role="label",
                    primitive="text",
                    style_ref=DETAIL_STYLE_REF,
                    text=entity.detail,
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
