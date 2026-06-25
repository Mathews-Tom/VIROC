"""The v1 ``pipeline`` grammar object: binds expand + layout into a plugin.

:class:`PipelineGrammar` is the single grammar v1 ships (ADR-0003): a left-to-right
pipeline flow. It satisfies the :class:`~viroc.grammars.LayoutGrammar` surface by
delegating to the module-level :func:`~viroc.grammars.pipeline.expand.expand` and
:func:`~viroc.grammars.pipeline.layout.layout`; animation (the full
:class:`~viroc.grammars.Grammar` contract) lands with the timeline resolver in M7.

``version`` is the grammar's own version, bumped whenever its expansion or layout
changes so a layout change is visible in the reproducibility key. The module-level
:data:`pipeline_grammar` instance is what
:func:`~viroc.grammars.register_builtins` registers.
"""

from __future__ import annotations

from viroc.core import BuildContext
from viroc.grammars import AbstractObject
from viroc.grammars.pipeline.expand import expand
from viroc.grammars.pipeline.layout import layout
from viroc.ir import ResolvedObject, Scene, SemanticIR


class PipelineGrammar:
    """The ``pipeline`` grammar: node/edge expansion + single-row template layout."""

    id = "pipeline"
    version = "1.0.0"

    def expand(self, scene: Scene, ir: SemanticIR) -> list[AbstractObject]:
        """Expand ``scene`` into node-boxes, labels, and arrows (phase P5)."""
        return expand(scene, ir)

    def layout(
        self,
        objects: list[AbstractObject],
        resolution: tuple[int, int],
        ctx: BuildContext,
    ) -> list[ResolvedObject]:
        """Place ``objects`` into overlap-free resolved boxes (phase P6)."""
        return layout(objects, resolution, ctx)


pipeline_grammar = PipelineGrammar()
"""The registered ``pipeline`` grammar instance (see ``register_builtins``)."""
