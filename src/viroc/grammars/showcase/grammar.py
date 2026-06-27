"""The v1 ``showcase`` grammar object: binds expand + layout + animate.

:class:`ShowcaseGrammar` is the second grammar v1 ships (M19): authored explainer
composition. It satisfies the full :class:`~viroc.grammars.Grammar` surface by
delegating to the module-level :func:`~viroc.grammars.showcase.expand.expand`,
:func:`~viroc.grammars.showcase.layout.layout`, and
:func:`~viroc.grammars.showcase.animate.animate`.

``version`` is the grammar's own version, bumped whenever its expansion, layout,
or animation changes so a change is visible in the reproducibility key. The
module-level :data:`showcase_grammar` instance is what
:func:`~viroc.grammars.register_builtins` registers alongside ``pipeline``.
"""

from __future__ import annotations

from viroc.core import BuildContext
from viroc.grammars import AbstractObject
from viroc.grammars.showcase import GRAMMAR_ID, GRAMMAR_VERSION
from viroc.grammars.showcase.animate import animate
from viroc.grammars.showcase.expand import expand
from viroc.grammars.showcase.layout import layout
from viroc.ir import Keyframe, ResolvedObject, Scene, SemanticIR


class ShowcaseGrammar:
    """The ``showcase`` grammar: composition expansion + template layout + reveal."""

    id = GRAMMAR_ID
    version = GRAMMAR_VERSION

    def expand(self, scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
        """Expand ``scene`` into composition primaries, titles, and links (P5)."""
        return expand(scene, ir)

    def layout(
        self,
        objects: list[AbstractObject],
        resolution: tuple[int, int],
        ctx: BuildContext,
    ) -> list[ResolvedObject]:
        """Place ``objects`` into a non-row template's resolved boxes (phase P6)."""
        return layout(objects, resolution, ctx)

    def animate(
        self, objects: list[ResolvedObject], scene: Scene, fps: int
    ) -> list[Keyframe]:
        """Choreograph entrance/transform/exit keyframes for ``objects`` (phase P8)."""
        return animate(objects, scene, fps)


showcase_grammar = ShowcaseGrammar()
"""The registered ``showcase`` grammar instance (see ``register_builtins``)."""
