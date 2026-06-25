"""Storyboard and project-config loading with source positions.

Pipeline phase P1 (design §3): read ``*.vidir.yaml`` / ``viroc.yaml`` (and JSON)
into plain Python data, *and* remember where each value came from so that
pre-validation can point a caret at the exact offending token (overview §9.2).

The loader returns a :class:`LoadedDocument` — the parsed data plus a map from
data path (the same shape Pydantic uses in error ``loc`` tuples) to a
:class:`SourceLocation`. YAML carries full positions; JSON is parsed for data
only (the canonical authored form is YAML, and JSON has no cheap position
source), so JSON documents have an empty location map.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

PathKey = str | int
DataPath = tuple[PathKey, ...]


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Where a value sits in its source file (1-based line/col).

    ``length`` is the number of characters the value spans on ``line`` and
    ``source`` is that physical line's text (when available), so a renderer can
    draw the framed caret. Mirrors what :class:`viroc.core.Span` needs.
    """

    file: str
    line: int
    col: int
    length: int
    source: str | None


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    """Parsed document data with per-value and per-key source positions.

    ``locations`` maps a data path to the position of its *value* (what a
    value-pointing diagnostic underlines). ``key_locations`` maps the same path
    to the position of the mapping *key* that introduced it, so a key-pointing
    diagnostic (an unknown field, say) can underline the offending key rather
    than its value.
    """

    path: Path
    data: Any
    locations: dict[DataPath, SourceLocation]
    key_locations: dict[DataPath, SourceLocation]


class ProjectConfig(BaseModel):
    """Minimal ``viroc.yaml`` project configuration.

    Names the project, the default renderer backend, and any path overrides.
    Unknown keys are rejected so config typos surface rather than being ignored.
    """

    model_config = ConfigDict(extra="forbid")

    project: str
    default_backend: str = "manim"
    paths: dict[str, str] = {}


def load_document(path: Path) -> LoadedDocument:
    """Load ``path`` (``.yaml``/``.yml``/``.json``) into a :class:`LoadedDocument`.

    YAML is parsed with full source positions; JSON yields data with an empty
    location map. Any other suffix raises :class:`ValueError` rather than
    guessing a format.
    """
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return _load_yaml(path, text)
    if suffix == ".json":
        return LoadedDocument(
            path=path, data=json.loads(text), locations={}, key_locations={}
        )
    raise ValueError(
        f"unsupported document type {path.suffix!r}: expected .yaml, .yml, or .json"
    )


def load_project_config(path: Path) -> ProjectConfig:
    """Load and schema-validate a ``viroc.yaml`` into a :class:`ProjectConfig`."""
    return ProjectConfig.model_validate(load_document(path).data)


def nearest_location(doc: LoadedDocument, path: DataPath) -> SourceLocation | None:
    """Return the location for ``path``, falling back to its nearest ancestor.

    Pydantic error paths can point at a value that has no node of its own (a
    missing required field, say); walking up to the closest recorded ancestor
    still frames the right region instead of dropping the span entirely.
    """
    current = tuple(path)
    while True:
        location = doc.locations.get(current)
        if location is not None:
            return location
        if not current:
            return None
        current = current[:-1]


def _load_yaml(path: Path, text: str) -> LoadedDocument:
    # Parse twice on purpose: safe_load gives typed data, get_single_node gives
    # the node graph for positions. The single-pass alternatives in PyYAML
    # (construct_document, compose, dispose) are untyped in the stubs and would
    # break the strict type gate; storyboards are small hand-authored files, so
    # the second pass is negligible and the loader is a local over an in-memory
    # string (no resource to dispose).
    data = yaml.safe_load(text)
    node = yaml.SafeLoader(text).get_single_node()
    if node is None:
        return LoadedDocument(path=path, data=data, locations={}, key_locations={})
    lines = text.splitlines()
    locations: dict[DataPath, SourceLocation] = {}
    key_locations: dict[DataPath, SourceLocation] = {}
    _index(node, (), str(path), lines, locations, key_locations)
    return LoadedDocument(
        path=path, data=data, locations=locations, key_locations=key_locations
    )


def _index(
    node: Node,
    path: DataPath,
    file: str,
    lines: list[str],
    locations: dict[DataPath, SourceLocation],
    key_locations: dict[DataPath, SourceLocation],
) -> None:
    """Record ``node``'s position, then recurse into mapping values / sequence items.

    The traversal mirrors how :func:`yaml.safe_load` builds ``data``, so a path
    here indexes the same value Pydantic names in its error ``loc`` tuples. For
    mappings, each key node's own position is recorded under the child path too,
    so a key-pointing diagnostic can underline the key rather than its value.
    """
    locations[path] = _location_of(node, file, lines)
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            child = (*path, str(key_node.value))
            key_locations[child] = _location_of(key_node, file, lines)
            _index(value_node, child, file, lines, locations, key_locations)
    elif isinstance(node, SequenceNode):
        for index, item in enumerate(node.value):
            _index(item, (*path, index), file, lines, locations, key_locations)


def _location_of(node: Node, file: str, lines: list[str]) -> SourceLocation:
    mark = node.start_mark
    length = len(node.value) if isinstance(node, ScalarNode) else 1
    source = lines[mark.line] if 0 <= mark.line < len(lines) else None
    return SourceLocation(
        file=file,
        line=mark.line + 1,
        col=mark.column + 1,
        length=max(length, 1),
        source=source,
    )
