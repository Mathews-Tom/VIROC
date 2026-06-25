"""Intermediate representations: Semantic IR (VidIR), Concrete IR, and their IO."""

from __future__ import annotations

from viroc.ir.concrete import (
    Box,
    Caption,
    ConcreteIR,
    Easing,
    Keyframe,
    KeyframeKind,
    Primitive,
    ResolvedObject,
)
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
    "Box",
    "Caption",
    "ConcreteIR",
    "DataPath",
    "Easing",
    "Edge",
    "EdgeKind",
    "Entity",
    "EntityType",
    "Keyframe",
    "KeyframeKind",
    "LoadedDocument",
    "Primitive",
    "ProjectConfig",
    "Resolution",
    "ResolvedObject",
    "Scene",
    "SemanticIR",
    "SourceLocation",
    "ValidationSpec",
    "VideoMeta",
    "load_document",
    "load_project_config",
    "nearest_location",
]
