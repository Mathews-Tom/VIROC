"""Semantic IR parsing and pre-validation (M4).

Grows across the M4 stack: PR-1 covers the models (the ``from`` alias
round-trip); later PRs add IO/fixture parsing and the VIR1xxx pre-validation
cases.
"""

from __future__ import annotations

import json
from pathlib import Path

from viroc.ir import (
    Edge,
    ProjectConfig,
    SemanticIR,
    load_document,
    load_project_config,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
RAG_STORYBOARD = FIXTURES / "rag-overview.vidir.yaml"


def test_edge_from_alias_round_trips() -> None:
    """``from`` (a keyword) is authored as the alias and survives a round-trip."""
    edge = Edge.model_validate({"from": "documents", "to": "chunks", "kind": "split"})
    assert edge.from_ == "documents"
    assert edge.to == "chunks"

    dumped = edge.model_dump(by_alias=True)
    assert dumped["from"] == "documents"
    assert "from_" not in dumped

    assert Edge.model_validate(dumped) == edge


def test_edge_populates_by_field_name() -> None:
    """``populate_by_name`` accepts the Python field name as well as the alias."""
    by_name = Edge.model_validate({"from_": "a", "to": "b"})
    by_alias = Edge.model_validate({"from": "a", "to": "b"})
    assert by_name == by_alias
    assert by_name.kind == "flow"


def test_rag_storyboard_parses() -> None:
    """The overview §9.1 RAG storyboard parses into a SemanticIR."""
    ir = SemanticIR.model_validate(load_document(RAG_STORYBOARD).data)

    assert ir.vidir_version == "0.1"
    assert ir.video.id == "rag-overview"
    assert ir.video.fps == 30
    assert (ir.video.resolution.width, ir.video.resolution.height) == (1920, 1080)
    assert [entity.id for entity in ir.entities] == [
        "documents",
        "chunks",
        "embedder",
        "vector_db",
        "llm",
    ]

    scene = ir.scenes[0]
    assert scene.grammar == "pipeline"
    assert scene.duration == "35s"
    assert scene.edges[0].from_ == "documents"
    assert scene.edges[0].to == "chunks"
    assert scene.edges[0].kind == "split"
    assert ir.validation is not None
    assert "llm" in ir.validation.required_entities


def test_loader_records_value_positions() -> None:
    """The loader pins each value to its 1-based source span."""
    doc = load_document(RAG_STORYBOARD)
    loc = doc.locations[("scenes", 0, "edges", 0, "from")]

    assert loc.source is not None
    assert loc.source[loc.col - 1 : loc.col - 1 + loc.length] == "documents"


def test_loader_reads_json_without_positions(tmp_path: Path) -> None:
    """JSON documents load data but carry no source positions (YAML-only)."""
    payload: dict[str, object] = {"vidir_version": "0.1", "scenes": []}
    json_path = tmp_path / "doc.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    doc = load_document(json_path)
    assert doc.data == payload
    assert doc.locations == {}


def test_project_config_loads_with_defaults(tmp_path: Path) -> None:
    """A minimal viroc.yaml validates; default_backend falls back to manim."""
    full = load_project_config(FIXTURES / "viroc.yaml")
    assert full.project == "rag-overview"
    assert full.default_backend == "manim"
    assert full.paths["out"] == "build"

    minimal_path = tmp_path / "viroc.yaml"
    minimal_path.write_text("project: solo\n", encoding="utf-8")
    minimal = ProjectConfig.model_validate(load_document(minimal_path).data)
    assert minimal.default_backend == "manim"
    assert minimal.paths == {}
