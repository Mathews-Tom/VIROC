"""Cross-cutting compiler primitives: stable IDs, hashing, diagnostics, build context."""

from __future__ import annotations

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

__all__ = [
    "CLASS_LABELS",
    "RESERVED_CLASSES",
    "Diagnostic",
    "DiagnosticClass",
    "Severity",
    "Span",
    "canonical_json",
    "code",
    "hash_bytes",
    "hash_data",
    "hash_unordered",
    "render",
    "slugify",
    "stable_id",
    "validate_code",
]
