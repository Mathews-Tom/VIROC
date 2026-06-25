"""Cross-cutting compiler primitives: stable IDs, hashing, diagnostics, build context."""

from __future__ import annotations

from viroc.core.context import (
    BuildArtifact,
    BuildContext,
    BuildPaths,
    ValidationThresholds,
    artifact_from_bytes,
    artifact_from_path,
    artifact_from_text,
)
from viroc.core.diagnostics import (
    CLASS_LABELS,
    RESERVED_CLASSES,
    Diagnostic,
    DiagnosticClass,
    Severity,
    Span,
    code,
    render,
    validate_code,
)
from viroc.core.hashing import canonical_json, hash_bytes, hash_data, hash_unordered
from viroc.core.ids import slugify, stable_id
from viroc.core.manifest import (
    VIR_ASSET_HASH_MISMATCH,
    VIR_RENDERER_VERSION_MISMATCH,
    VIR_SOURCE_HASH_MISMATCH,
    BuildManifest,
    RendererManifest,
    build_manifest,
    manifest_json,
    validate_reproducibility,
    write_manifest,
)

__all__ = [
    "CLASS_LABELS",
    "RESERVED_CLASSES",
    "BuildArtifact",
    "BuildContext",
    "BuildPaths",
    "ValidationThresholds",
    "Diagnostic",
    "DiagnosticClass",
    "Severity",
    "Span",
    "BuildManifest",
    "artifact_from_bytes",
    "artifact_from_path",
    "artifact_from_text",
    "canonical_json",
    "code",
    "hash_bytes",
    "hash_data",
    "hash_unordered",
    "render",
    "RendererManifest",
    "VIR_ASSET_HASH_MISMATCH",
    "VIR_RENDERER_VERSION_MISMATCH",
    "VIR_SOURCE_HASH_MISMATCH",
    "slugify",
    "stable_id",
    "validate_code",
    "build_manifest",
    "manifest_json",
    "validate_reproducibility",
    "write_manifest",
]
