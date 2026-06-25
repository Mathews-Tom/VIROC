"""Pre-validation: schema checks over the Semantic IR (pipeline phase P2).

Runs before any layout work (design §6): cheap structural checks that turn an
authoring mistake into a compiler-grade VIR1xxx diagnostic instead of a Python
traceback. This module covers the *schema* layer — parsing the loaded document
into a :class:`SemanticIR` and translating every Pydantic validation error into a
diagnostic with a source span. Reference and grammar-fit checks build on top of
it in this same package.

Code allocation in the VIR1xxx (schema / references) range (design §5.2):

- ``VIR1001`` — invalid value or type (the catch-all Pydantic error)
- ``VIR1002`` — undefined entity reference (reserved here; emitted by the
  reference check, matching overview §9.2)
- ``VIR1003`` — unknown field
- ``VIR1004`` — missing required field
- ``VIR1005`` — grammar fit (emitted by the grammar-fit check)
"""

from __future__ import annotations

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from viroc.core import Diagnostic, DiagnosticClass, Span, code
from viroc.ir import LoadedDocument, SemanticIR, SourceLocation, nearest_location

VIR_SCHEMA = code(DiagnosticClass.SCHEMA, 1)
VIR_UNKNOWN_REFERENCE = code(DiagnosticClass.SCHEMA, 2)
VIR_UNKNOWN_FIELD = code(DiagnosticClass.SCHEMA, 3)
VIR_MISSING_FIELD = code(DiagnosticClass.SCHEMA, 4)
VIR_GRAMMAR_FIT = code(DiagnosticClass.SCHEMA, 5)


def validate_schema(doc: LoadedDocument) -> tuple[SemanticIR | None, list[Diagnostic]]:
    """Parse ``doc`` into a :class:`SemanticIR`, or return schema diagnostics.

    On success returns ``(ir, [])``. On failure returns ``(None, diagnostics)``
    with one diagnostic per Pydantic error, each carrying a span pointing at (or
    near) the offending value. Parsing is the gate: downstream reference and
    grammar-fit checks only run once the structure is sound.
    """
    try:
        ir = SemanticIR.model_validate(doc.data)
    except ValidationError as error:
        return None, [_diagnostic_for(doc, detail) for detail in error.errors()]
    return ir, []


def span_from_location(location: SourceLocation, label: str | None = None) -> Span:
    """Adapt an IO :class:`SourceLocation` into a diagnostic :class:`Span`."""
    return Span(
        file=location.file,
        line=location.line,
        col=location.col,
        length=location.length,
        source=location.source,
        label=label,
    )


def _diagnostic_for(doc: LoadedDocument, detail: ErrorDetails) -> Diagnostic:
    loc = detail["loc"]
    error_type = detail["type"]
    field = str(loc[-1]) if loc else "<root>"
    path = loc

    if error_type == "extra_forbidden":
        diag_code = VIR_UNKNOWN_FIELD
        message = f'unknown field "{field}"'
        help_text: str | None = f'remove "{field}" or check for a typo'
        label: str | None = "unknown field"
        # The offending token is the key itself; point the caret at it.
        location = doc.key_locations.get(path) or nearest_location(doc, path)
    elif error_type == "missing":
        diag_code = VIR_MISSING_FIELD
        message = f'missing required field "{field}"'
        help_text = f'add the required "{field}" field'
        label = "required here"
        location = nearest_location(doc, path)
    else:
        diag_code = VIR_SCHEMA
        message = str(detail["msg"])
        help_text = None
        label = None
        location = nearest_location(doc, path)

    span = span_from_location(location, label) if location is not None else None
    return Diagnostic(code=diag_code, message=message, span=span, help=help_text)
