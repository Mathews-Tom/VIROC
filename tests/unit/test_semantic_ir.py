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
    LoadedDocument,
    ProjectConfig,
    SemanticIR,
    load_document,
    load_project_config,
)
from viroc.validators import (
    VIR_MISSING_FIELD,
    VIR_SCHEMA,
    VIR_UNKNOWN_FIELD,
    validate_schema,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
RAG_STORYBOARD = FIXTURES / "rag-overview.vidir.yaml"


def _load_yaml(tmp_path: Path, text: str) -> LoadedDocument:
    """Write ``text`` to a .vidir.yaml under ``tmp_path`` and load it with positions."""
    path = tmp_path / "storyboard.vidir.yaml"
    path.write_text(text, encoding="utf-8")
    return load_document(path)


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


_VALID = """\
vidir_version: "0.1"
video: { id: v, title: t }
entities:
  - { id: documents, label: "Documents", type: data_source }
scenes: []
"""


def test_valid_storyboard_has_no_schema_diagnostics() -> None:
    """The §9.1 storyboard schema-validates into a SemanticIR with no diagnostics."""
    ir, diagnostics = validate_schema(load_document(RAG_STORYBOARD))
    assert diagnostics == []
    assert ir is not None
    assert ir.video.id == "rag-overview"


def test_unknown_field_is_vir1003(tmp_path: Path) -> None:
    """An unknown top-level field yields VIR1003 pointing at the stray key."""
    doc = _load_yaml(tmp_path, _VALID + "bogus: 1\n")
    ir, diagnostics = validate_schema(doc)

    assert ir is None
    codes = [d.code for d in diagnostics]
    assert codes == [VIR_UNKNOWN_FIELD]
    span = diagnostics[0].span
    assert span is not None
    assert span.source is not None
    assert span.source[span.col - 1 : span.col - 1 + span.length] == "bogus"


def test_missing_required_id_is_vir1004(tmp_path: Path) -> None:
    """An entity without an id yields VIR1004."""
    text = (
        'vidir_version: "0.1"\n'
        "video: { id: v, title: t }\n"
        "entities:\n"
        '  - { label: "Documents", type: data_source }\n'
        "scenes: []\n"
    )
    ir, diagnostics = validate_schema(_load_yaml(tmp_path, text))

    assert ir is None
    assert [d.code for d in diagnostics] == [VIR_MISSING_FIELD]


def test_invalid_entity_type_is_vir1001(tmp_path: Path) -> None:
    """A value outside the EntityType literal yields the catch-all VIR1001."""
    text = (
        'vidir_version: "0.1"\n'
        "video: { id: v, title: t }\n"
        "entities:\n"
        '  - { id: x, label: "X", type: banana }\n'
        "scenes: []\n"
    )
    ir, diagnostics = validate_schema(_load_yaml(tmp_path, text))

    assert ir is None
    assert [d.code for d in diagnostics] == [VIR_SCHEMA]


def test_nested_unknown_field_caret_targets_the_key(tmp_path: Path) -> None:
    """A nested unknown field points the caret at the key, on the key's own line."""
    text = (
        'vidir_version: "0.1"\n'
        "video:\n"
        "  id: v\n"
        "  title: t\n"
        "  bogus:\n"
        "    nested: value\n"
        "entities: []\n"
        "scenes: []\n"
    )
    ir, diagnostics = validate_schema(_load_yaml(tmp_path, text))

    assert ir is None
    assert [d.code for d in diagnostics] == [VIR_UNKNOWN_FIELD]
    span = diagnostics[0].span
    assert span is not None
    assert span.source is not None
    assert span.source.strip() == "bogus:"
    assert span.source[span.col - 1 : span.col - 1 + span.length] == "bogus"


def test_beat_scene_parses(tmp_path: Path) -> None:
    """A scene carrying a beats block parses into Beat models."""
    text = (
        'vidir_version: "0.1"\n'
        "video: { id: v, title: t }\n"
        "entities:\n"
        '  - { id: a, label: "A", type: model }\n'
        "scenes:\n"
        "  - id: s1\n"
        "    grammar: pipeline\n"
        "    duration: 10s\n"
        "    nodes: [a]\n"
        "    beats:\n"
        '      - { id: b1, at: "0s", duration: "4s", narration: "intro" }\n'
        '      - { id: b2, at: "after(b1.end)", duration: "6s" }\n'
    )
    ir, diagnostics = validate_schema(_load_yaml(tmp_path, text))

    assert diagnostics == []
    assert ir is not None
    beats = ir.scenes[0].beats
    assert [beat.id for beat in beats] == ["b1", "b2"]
    assert beats[0].at == "0s"
    assert beats[0].narration == "intro"
    assert beats[1].narration is None


def test_beat_missing_duration_is_vir1004(tmp_path: Path) -> None:
    """A beat missing a required field yields VIR1004."""
    text = (
        'vidir_version: "0.1"\n'
        "video: { id: v, title: t }\n"
        "entities:\n"
        '  - { id: a, label: "A", type: model }\n'
        "scenes:\n"
        "  - id: s1\n"
        "    grammar: pipeline\n"
        "    duration: 10s\n"
        "    nodes: [a]\n"
        "    beats:\n"
        '      - { id: b1, at: "0s" }\n'
    )
    ir, diagnostics = validate_schema(_load_yaml(tmp_path, text))

    assert ir is None
    assert [d.code for d in diagnostics] == [VIR_MISSING_FIELD]
