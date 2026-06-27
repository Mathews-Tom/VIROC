"""The ``showcase`` grammar: authored explainer composition (design §4).

Where :mod:`viroc.grammars.pipeline` is the boring left-to-right flow grammar,
``showcase`` is the second v1 grammar for *authored explainer scenes*: panels,
code cards, callouts, and evidence blocks arranged in non-row compositions
(grids, fan-outs, comparisons) rather than a single row (design §4,
``.docs/2026-06-26-showcase-redesign-design.md`` §5). It exists so VIROC can
express showcase-grade variety without overloading ``pipeline`` — ``pipeline``
stays linear; richer composition lives here.

The grammar is template-based and bounded, never a general solver: a fixed set
of *composition kinds* (:data:`COMPOSITION_KINDS`) maps each authored entity to a
drawable primitive, and a fixed set of *layout templates* (grid / fan-out /
comparison) places them deterministically. It reuses the renderer-neutral
Concrete IR primitive set (``rect``/``code``/``formula``/``text``) so every
adapter that supports those primitives can render it; backends that cannot (e.g.
Manim, which lacks ``code``/``formula``) fail with explicit ``VIR5xxx`` renderer
diagnostics rather than degrading silently.

The package mirrors ``pipeline``'s split — :mod:`expand`, :mod:`layout`,
:mod:`animate`, bound by :mod:`grammar` — so the same plugin contract
(:class:`viroc.grammars.Grammar`) drives both.
"""

from typing import Literal

from viroc.ir import Primitive

GRAMMAR_ID = "showcase"
"""The id a scene's ``grammar`` field selects to use this grammar."""

GRAMMAR_VERSION = "1.0.0"
"""Grammar version, bumped whenever expansion, layout, or animation changes."""

CompositionKind = Literal["panel", "code_card", "callout", "evidence"]
"""The composition role a :data:`COMPOSITION_KINDS` entry assigns an entity."""

COMPOSITION_KINDS: dict[str, CompositionKind] = {
    "data_source": "panel",
    "service": "panel",
    "user": "callout",
    "intermediate": "code_card",
    "model": "code_card",
    "storage": "evidence",
}
"""Map each :class:`~viroc.ir.EntityType` to a showcase composition kind.

Panels and callouts are container ``rect`` boxes; code cards lower to the
``code`` primitive; evidence blocks lower to the ``formula`` primitive. The two
non-``rect`` kinds are exactly what makes a backend's primitive support
observable — a renderer without ``code``/``formula`` rejects a showcase scene
through the shared capability diagnostics rather than dropping content.
"""

KIND_PRIMITIVES: dict[CompositionKind, Primitive] = {
    "panel": "rect",
    "callout": "rect",
    "code_card": "code",
    "evidence": "formula",
}
"""The Concrete IR primitive each composition kind lowers its primary box to."""

TITLE_STYLE_REF = "showcase.title"
"""Style reference for the title label every composition object carries."""

__all__ = [
    "COMPOSITION_KINDS",
    "GRAMMAR_ID",
    "GRAMMAR_VERSION",
    "KIND_PRIMITIVES",
    "TITLE_STYLE_REF",
    "CompositionKind",
]
