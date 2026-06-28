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
    """Return the human-readable text for ``obj``.

    When the resolver threaded the authored label onto the object
    (:attr:`~viroc.ir.ResolvedObject.text`), that label is the source of truth so
    a node reads exactly as the author wrote it (``"Vector store"``), identically
    across backends. Older objects that carry no text fall back to deriving it
    from the stable id: a trailing label-like role (:data:`_LABEL_ROLES`) defers
    to the preceding entity segment, otherwise the final segment is used, with
    underscores becoming spaces and the result title-cased.
    """
    if obj.text is not None:
        return obj.text
    parts = obj.id.split(".")
    source = parts[-2] if len(parts) >= 2 and parts[-1] in _LABEL_ROLES else parts[-1]
    return source.replace("_", " ").title()


__all__ = ["display_text"]
