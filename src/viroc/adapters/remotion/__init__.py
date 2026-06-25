"""Remotion source emitter: deterministic React/TypeScript project generation."""

from __future__ import annotations

from viroc.adapters.remotion.emit import (
    emit,
    materialize_source,
    project_tree,
    source_for,
    source_tree,
)

id = "remotion"
version = "0.1"
source_filename = "project.json"

__all__ = [
    "emit",
    "id",
    "materialize_source",
    "project_tree",
    "source_filename",
    "source_for",
    "source_tree",
    "version",
]
