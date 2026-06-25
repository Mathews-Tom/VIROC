"""Normalize step + unit/color primitives (M5).

Covers the design §3 P3 contract: the duration parser and colour normalizer
reject ambiguous input (no silent coercion), and :func:`normalize` is a stable,
idempotent, deterministic canonicalization of the Semantic IR.
"""

from __future__ import annotations

import pytest

from viroc.compiler.normalize import normalize, normalize_color, parse_duration
from viroc.core import hash_data
from viroc.ir import SemanticIR

_RAW_IR: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {
        "id": "RAG Overview",
        "title": "How RAG Works",
        "fps": 30,
        "resolution": {"width": 1920, "height": 1080},
    },
    "entities": [
        {"id": "Vector DB", "label": "Vector DB", "type": "storage"},
        {"id": "Doc Source", "label": "Documents", "type": "data_source"},
    ],
    "scenes": [
        {
            "id": "Main Scene",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["Vector DB", "Doc Source"],
            "edges": [{"from": "Doc Source", "to": "Vector DB", "kind": "store"}],
            "beats": [{"id": "Beat One", "at": "after(prev.end)", "duration": "4s"}],
        }
    ],
    "validation": {"required_entities": ["Vector DB"], "checks": ["schema"]},
}


def _ir() -> SemanticIR:
    return SemanticIR.model_validate(_RAW_IR)


def test_parse_duration_reads_seconds() -> None:
    """A number with an explicit ``s`` suffix parses to seconds."""
    assert parse_duration("4s") == 4.0
    assert parse_duration("35s") == 35.0
    assert parse_duration("0.5s") == 0.5
    assert parse_duration("0s") == 0.0


@pytest.mark.parametrize("text", ["4", "4ms", "4sec", "4 s", "-5s", "", "fast", "s"])
def test_parse_duration_rejects_ambiguous(text: str) -> None:
    """Anything without an unambiguous ``Ns`` shape raises rather than coercing."""
    with pytest.raises(ValueError, match="ambiguous duration"):
        parse_duration(text)


def test_normalize_color_expands_and_lowercases() -> None:
    """Hex colours canonicalize to lowercase ``#rrggbb``; shorthand expands."""
    assert normalize_color("#FFF") == "#ffffff"
    assert normalize_color("#AABBCC") == "#aabbcc"
    assert normalize_color("1a2b3c") == "#1a2b3c"
    assert normalize_color("abc") == "#aabbcc"


def test_normalize_color_is_idempotent() -> None:
    """Normalizing an already-canonical colour is a no-op."""
    once = normalize_color("#FFF")
    assert normalize_color(once) == once


@pytest.mark.parametrize("text", ["red", "#12", "#1234", "#xyz", "12345", ""])
def test_normalize_color_rejects_non_hex(text: str) -> None:
    """Non-hex colours raise rather than being guessed at."""
    with pytest.raises(ValueError, match="unrecognized colour"):
        normalize_color(text)


def test_normalize_slugifies_ids_and_rewrites_references() -> None:
    """Author ids become stable slugs and every reference is rewritten to match."""
    norm = normalize(_ir())

    assert norm.video.id == "rag_overview"
    assert [entity.id for entity in norm.entities] == ["vector_db", "doc_source"]

    scene = norm.scenes[0]
    assert scene.id == "main_scene"
    assert scene.nodes == ["vector_db", "doc_source"]
    assert (scene.edges[0].from_, scene.edges[0].to) == ("doc_source", "vector_db")
    assert scene.edges[0].kind == "store"
    assert scene.beats[0].id == "beat_one"

    assert norm.validation is not None
    assert norm.validation.required_entities == ["vector_db"]


def test_normalize_keeps_durations_and_time_expressions_verbatim() -> None:
    """Units are not coerced into the Semantic IR; time strings survive intact."""
    scene = normalize(_ir()).scenes[0]
    assert scene.duration == "35s"
    assert scene.beats[0].at == "after(prev.end)"
    assert scene.beats[0].duration == "4s"


def test_normalize_materializes_defaults() -> None:
    """An edge without an explicit kind carries the default in the canonical output."""
    raw = {
        "vidir_version": "0.1",
        "video": {"id": "v", "title": "t"},
        "entities": [
            {"id": "a", "label": "A", "type": "data_source"},
            {"id": "b", "label": "B", "type": "storage"},
        ],
        "scenes": [
            {
                "id": "s",
                "grammar": "pipeline",
                "duration": "5s",
                "nodes": ["a", "b"],
                "edges": [{"from": "a", "to": "b"}],
            }
        ],
    }
    norm = normalize(SemanticIR.model_validate(raw))
    assert norm.scenes[0].edges[0].kind == "flow"


def test_normalize_is_idempotent() -> None:
    """``normalize(normalize(x)) == normalize(x)``."""
    once = normalize(_ir())
    assert normalize(once) == once


def test_normalize_is_deterministic() -> None:
    """Two independent normalizations produce a byte-identical canonical digest."""
    first = hash_data(normalize(_ir()).model_dump(by_alias=True))
    second = hash_data(normalize(_ir()).model_dump(by_alias=True))
    assert first == second
