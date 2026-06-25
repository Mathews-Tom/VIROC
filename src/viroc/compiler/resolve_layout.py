"""Layout resolution driver — pipeline phase P6 (design §3).

The Resolver's layout phase: for one scene, select its declared grammar from the
registry, expand the scene into abstract objects (P5), and lay them out into
resolved boxes (P6). This is the seam between the compiler and the grammar
plugins — the compiler owns ordering and orchestration, the grammar owns the
template.

Pre-validation (grammar-fit, VIR1005) has already confirmed the scene's grammar
is registered, so an unknown grammar here is a programmer error, not an authoring
one: :func:`~viroc.grammars.get` raises rather than degrading. Built-in grammars
are registered on demand so a caller need not import the grammar package itself.
"""

from __future__ import annotations

from viroc.core import BuildContext
from viroc.grammars import get, register_builtins
from viroc.ir import ResolvedObject, Scene, SemanticIR


def resolve_layout(scene: Scene, ir: SemanticIR, ctx: BuildContext) -> list[ResolvedObject]:
    """Expand and lay out ``scene`` with its declared grammar.

    Returns the scene's resolved objects (boxes) — deterministic, overlap-free,
    within the safe frame. ``ir`` supplies entity labels/types and the target
    resolution; ``ctx`` threads build configuration to the grammar.
    """
    register_builtins()
    grammar = get(scene.grammar)
    objects = grammar.expand(scene, ir)
    resolution = (ir.video.resolution.width, ir.video.resolution.height)
    return grammar.layout(objects, resolution, ctx)
