"""Intermediate representations: Semantic IR (VidIR), Concrete IR, and their IO."""

from __future__ import annotations

from viroc.ir.io import (
    DataPath,
    LoadedDocument,
    ProjectConfig,
    SourceLocation,
    load_document,
    load_project_config,
    nearest_location,
)
from viroc.ir.semantic import (
    Beat,
    Edge,
    EdgeKind,
    Entity,
    EntityType,
    Resolution,
    Scene,
    SemanticIR,
    ValidationSpec,
    VideoMeta,
)

__all__ = [
    "Beat",
    "DataPath",
    "Edge",
    "EdgeKind",
    "Entity",
    "EntityType",
    "LoadedDocument",
    "ProjectConfig",
    "Resolution",
    "Scene",
    "SemanticIR",
    "SourceLocation",
    "ValidationSpec",
    "VideoMeta",
    "load_document",
    "load_project_config",
    "nearest_location",
]
