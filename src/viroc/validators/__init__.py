"""Validation passes: schema/reference pre-validate and post-resolve layout/timing checks."""

from __future__ import annotations

from viroc.validators.schema import (
    VIR_GRAMMAR_FIT,
    VIR_MISSING_FIELD,
    VIR_SCHEMA,
    VIR_UNKNOWN_FIELD,
    VIR_UNKNOWN_REFERENCE,
    pre_validate,
    span_from_location,
    validate_grammar_fit,
    validate_references,
    validate_schema,
)
from viroc.validators.timing import (
    VIR_BEAT_OVERLAP,
    VIR_CAPTION_UNDERFLOW,
    VIR_IMPOSSIBLE_DURATION,
    validate_timing,
)

__all__ = [
    "VIR_GRAMMAR_FIT",
    "VIR_MISSING_FIELD",
    "VIR_SCHEMA",
    "VIR_UNKNOWN_FIELD",
    "VIR_UNKNOWN_REFERENCE",
    "VIR_BEAT_OVERLAP",
    "VIR_CAPTION_UNDERFLOW",
    "VIR_IMPOSSIBLE_DURATION",
    "pre_validate",
    "span_from_location",
    "validate_grammar_fit",
    "validate_references",
    "validate_schema",
    "validate_timing",
]
