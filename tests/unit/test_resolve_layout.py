"""Layout resolution driver and the registered pipeline grammar (M6, PR-4).

Covers the P6 driver (`resolve_layout`) that selects a scene's grammar from the
registry and runs expand + layout, the `register_builtins` registration of the v1
`pipeline` grammar, and the grammar object that binds the two free functions.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

from viroc.compiler.resolve_layout import resolve_layout
from viroc.core import BuildContext, BuildPaths
from viroc.grammars import is_registered, overlaps, register_builtins, registered_ids
from viroc.grammars.pipeline.expand import expand
from viroc.grammars.pipeline.grammar import pipeline_grammar
from viroc.grammars.pipeline.layout import layout
from viroc.ir import SemanticIR

_RAG: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {
        "id": "rag_overview",
        "title": "How RAG Works",
        "resolution": {"width": 1920, "height": 1080},
    },
    "entities": [
        {"id": "documents", "label": "Documents", "type": "data_source"},
        {"id": "chunks", "label": "Chunks", "type": "intermediate"},
        {"id": "embedder", "label": "Embedding Model", "type": "model"},
        {"id": "vector_db", "label": "Vector DB", "type": "storage"},
    ],
    "scenes": [
        {
            "id": "pipeline",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["documents", "chunks", "embedder", "vector_db"],
            "edges": [
                {"from": "documents", "to": "chunks", "kind": "split"},
                {"from": "chunks", "to": "embedder", "kind": "transform"},
                {"from": "embedder", "to": "vector_db", "kind": "store"},
            ],
        }
    ],
}


def _ir() -> SemanticIR:
    return SemanticIR.model_validate(_RAG)


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-resolve-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def test_register_builtins_registers_pipeline() -> None:
    """The v1 pipeline grammar is registered (idempotently) by register_builtins."""
    register_builtins()
    register_builtins()  # idempotent: a second call must not raise
    assert is_registered("pipeline")
    assert "pipeline" in registered_ids()


def test_pipeline_grammar_identity_and_delegation() -> None:
    """The grammar object exposes its id/version and delegates to expand+layout."""
    assert pipeline_grammar.id == "pipeline"
    assert pipeline_grammar.version == "1.0.0"
    ir = _ir()
    scene = ir.scenes[0]
    objects = pipeline_grammar.expand(scene, ir)
    assert objects == expand(scene, ir)
    assert pipeline_grammar.layout(objects, (1920, 1080), _ctx()) == layout(
        objects, (1920, 1080), _ctx()
    )


def test_resolve_layout_runs_expand_then_layout() -> None:
    """The driver produces the grammar's expand+layout result for the scene."""
    ir = _ir()
    scene = ir.scenes[0]
    resolved = resolve_layout(scene, ir, _ctx())
    expected = layout(expand(scene, ir), (1920, 1080), _ctx())
    assert resolved == expected


def test_resolve_layout_is_overlap_free() -> None:
    """The resolved boxes the driver returns have zero pairwise overlap."""
    resolved = resolve_layout(_ir().scenes[0], _ir(), _ctx())
    assert not any(overlaps(a.box, b.box) for a, b in combinations(resolved, 2))
