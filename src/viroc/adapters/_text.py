"""Shared deterministic display-text derivation for renderer emitters.

The Concrete IR stores geometry and timing, never glyph text: a
:class:`~viroc.ir.ResolvedObject` carries no display string. Every emitter
therefore derives an object's on-screen text from its stable id, and they must
all derive the *same* text from the same id so a storyboard reads identically
across backends. That derivation lives here, once, instead of being copied into
each adapter.

The convention follows the stable-id namespacing (``scene.entity.role``): a
trailing *role* segment that names a label-like object (``label`` or ``title``)
carries no words of its own, so the entity segment before it supplies them. Any
other trailing segment is itself the text source. The chosen segment's
underscores become spaces and it is title-cased — matching how the ``pipeline``
grammar's node labels have always rendered.
"""

from __future__ import annotations

from viroc.ir import ResolvedObject

_LABEL_ROLES = frozenset({"label", "title"})
"""Trailing id roles that defer their text to the preceding entity segment."""


def display_text(obj: ResolvedObject) -> str:
    """Return the human-readable text for ``obj`` derived from its stable id.

    Ids are dot-namespaced. When the final segment is a label-like role
    (:data:`_LABEL_ROLES`) the entity segment before it is the source; otherwise
    the final segment is. The source's underscores become spaces and it is
    title-cased, so ``"scene.vector_db.title"`` and ``"scene.vector_db.label"``
    both render ``"Vector Db"``.
    """
    parts = obj.id.split(".")
    source = parts[-2] if len(parts) >= 2 and parts[-1] in _LABEL_ROLES else parts[-1]
    return source.replace("_", " ").title()


__all__ = ["display_text"]
