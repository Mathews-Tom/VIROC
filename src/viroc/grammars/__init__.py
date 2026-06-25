"""Grammar plugin contract and registry (design §4).

A *grammar* owns three things for one semantic pattern (design §4,
``docs/grammar-authoring.md``):

1. **expand** — semantic nodes/edges into a set of abstract objects (a
   ``pipeline`` becomes node-boxes + connecting arrows + labels);
2. **layout** — place those abstract objects, template-driven (not a general
   solver), into resolved boxes with no overlap and safe margins. Text/LaTeX
   measurement, if any, lives *here* in the Resolver — never in an adapter's
   ``emit()`` (design §10, ADR-0002);
3. **animate** — default entrance/transform/exit choreography (frame windows),
   delivered with the timeline resolver in M7.

This module is renderer-neutral and grammar-agnostic. It declares the plugin
contract (:class:`LayoutGrammar`, :class:`Grammar`), the abstract-object
vocabulary (:class:`AbstractObject`) the expand-to-layout handoff speaks, a small
:class:`~viroc.ir.Box` geometry kernel (:func:`overlaps`, :func:`contains`) that
defines what "non-overlapping" and "within the safe frame" mean, and the
registry a scene's ``grammar`` field selects from. The one v1 grammar,
``pipeline``, lives under :mod:`viroc.grammars.pipeline`.

The contract is split so M6 can ship and register a grammar that owns *layout*
(expand + layout) before *animation* exists: :class:`LayoutGrammar` is the
expand-to-layout surface the Resolver drives at P5–P6, and :class:`Grammar` is the
full contract that adds :meth:`Grammar.animate` (M7). The registry stores the
narrower surface, so it accepts both layout-only grammars now and full grammars
later.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from viroc.core import BuildContext
from viroc.ir import Box, Keyframe, Primitive, ResolvedObject, Scene, SemanticIR

AbstractRole = Literal["node", "arrow", "label"]
"""The role an :class:`AbstractObject` plays in a grammar's expansion."""


class AbstractObject(BaseModel):
    """A pre-layout drawable a grammar's ``expand`` emits (design §4).

    The renderer-neutral handoff between ``expand`` and ``layout``: it names a
    drawable and its graph role but carries *no* position — ``layout`` assigns the
    :class:`~viroc.ir.Box`. ``extra="forbid"`` keeps the vocabulary closed so a
    malformed expansion fails loudly rather than smuggling unknown fields past
    the resolver.

    Role-specific fields stay optional because one flat object set carries every
    role: ``text`` is the label/measurable string (labels and texty nodes);
    ``source``/``target`` name the connected node-object ids (arrows); ``owner``
    names the node-object id a label annotates (so ``layout`` can place a label
    relative to its node).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    role: AbstractRole
    primitive: Primitive
    style_ref: str
    text: str | None = None
    source: str | None = None
    target: str | None = None
    owner: str | None = None
    z: int = 0


@runtime_checkable
class LayoutGrammar(Protocol):
    """The expand-to-layout surface the Resolver drives (pipeline phases P5–P6).

    A grammar exposes a stable ``id`` — a scene's ``grammar`` field selects it —
    and a ``version`` bumped whenever its expansion or layout changes, so a layout
    change becomes visible in the reproducibility key. ``expand`` turns a scene
    into abstract objects; ``layout`` places them into resolved boxes against the
    target ``resolution``. Both are pure and byte-stable: the same scene yields
    the same objects and the same boxes across runs and machines.
    """

    id: str
    version: str

    def expand(self, scene: Scene, ir: SemanticIR) -> list[AbstractObject]: ...

    def layout(
        self,
        objects: list[AbstractObject],
        resolution: tuple[int, int],
        ctx: BuildContext,
    ) -> list[ResolvedObject]: ...


@runtime_checkable
class Grammar(LayoutGrammar, Protocol):
    """The full grammar plugin contract: :class:`LayoutGrammar` plus animation.

    ``animate`` produces the default entrance/transform/exit keyframes for the
    pattern, with frame windows resolved against the scene and ``fps``. The
    timeline resolver (phase P8) selects this surface for grammars that animate,
    narrowing a registered grammar with ``isinstance`` against this
    runtime-checkable protocol.
    """

    def animate(
        self, objects: list[ResolvedObject], scene: Scene, fps: int
    ) -> list[Keyframe]: ...


_GRAMMARS: dict[str, LayoutGrammar] = {}


def register(grammar: LayoutGrammar) -> None:
    """Register ``grammar`` under its ``id``.

    A second registration of the same ``id`` is a hard error rather than a silent
    overwrite, so a typo or a double-import surfaces immediately instead of
    shadowing a grammar.
    """
    if grammar.id in _GRAMMARS:
        raise ValueError(f"grammar {grammar.id!r} is already registered")
    _GRAMMARS[grammar.id] = grammar


def get(grammar_id: str) -> LayoutGrammar:
    """Return the grammar registered under ``grammar_id``.

    Raises :class:`KeyError` when nothing is registered — pre-validation
    (grammar-fit, VIR1005) is expected to have caught an unknown grammar before
    the resolver reaches here, so an unregistered id this late is a programmer
    error, not an authoring error.
    """
    try:
        return _GRAMMARS[grammar_id]
    except KeyError:
        raise KeyError(f"no grammar registered under {grammar_id!r}") from None


def is_registered(grammar_id: str) -> bool:
    """Report whether a grammar is registered under ``grammar_id``."""
    return grammar_id in _GRAMMARS


def registered_ids() -> frozenset[str]:
    """Return the ids of every registered grammar (the grammar-fit allow-list)."""
    return frozenset(_GRAMMARS)


def register_builtins() -> None:
    """Register the built-in v1 grammars; idempotent and safe to call repeatedly.

    The contract module stays free of grammar imports, so the import is local;
    callers (the layout driver, grammar-fit pre-validation) invoke this before
    consulting the registry so the built-ins are present without importing the
    grammar package directly. An already-registered grammar is skipped.
    """
    from viroc.grammars.pipeline.grammar import pipeline_grammar

    if not is_registered(pipeline_grammar.id):
        register(pipeline_grammar)


def overlaps(a: Box, b: Box) -> bool:
    """Report whether two boxes share positive area.

    Touching edges do not count as overlap: the intersection must have positive
    width *and* positive height. This is the predicate post-resolve layout
    validation enforces (no two resolved boxes may overlap, VIR3xxx).
    """
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def contains(outer: Box, inner: Box) -> bool:
    """Report whether ``inner`` lies fully within ``outer`` (edges may touch).

    Used to assert every resolved box stays inside the safe frame.
    """
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and inner.x + inner.w <= outer.x + outer.w
        and inner.y + inner.h <= outer.y + outer.h
    )


__all__ = [
    "AbstractObject",
    "AbstractRole",
    "Grammar",
    "LayoutGrammar",
    "contains",
    "get",
    "is_registered",
    "overlaps",
    "register",
    "register_builtins",
    "registered_ids",
]
