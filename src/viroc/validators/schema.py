"""Pre-validation: schema checks over the Semantic IR (pipeline phase P2).

Runs before any layout work (design §6): cheap structural checks that turn an
authoring mistake into a compiler-grade VIR1xxx diagnostic instead of a Python
traceback. This module covers the *schema* layer — parsing the loaded document
into a :class:`SemanticIR` and translating every Pydantic validation error into a
diagnostic with a source span. Reference and grammar-fit checks (below) build on
the parsed IR, and :func:`pre_validate` runs all three as the single P2 entry point.

Code allocation in the VIR1xxx (schema / references) range (design §5.2):

- ``VIR1001`` — invalid value or type (the catch-all Pydantic error)
- ``VIR1002`` — undefined entity reference (reserved here; emitted by the
  reference check, matching overview §9.2)
- ``VIR1003`` — unknown field
- ``VIR1004`` — missing required field
- ``VIR1005`` — grammar fit (emitted by the grammar-fit check)
"""

from __future__ import annotations

import difflib

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from viroc.core import Diagnostic, DiagnosticClass, Span, code
from viroc.grammars import is_registered, register_builtins, registered_ids
from viroc.ir import DataPath, LoadedDocument, SemanticIR, SourceLocation, nearest_location

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


def validate_references(ir: SemanticIR, doc: LoadedDocument) -> list[Diagnostic]:
    """Flag scene nodes and edge endpoints that name an undeclared entity.

    Each offending reference becomes a ``VIR1002`` with a span at the bad token
    and a ``did you mean`` suggestion drawn from the declared entity ids
    (overview §9.2).
    """
    declared = {entity.id for entity in ir.entities}
    candidates = sorted(declared)
    diagnostics: list[Diagnostic] = []
    for scene_index, scene in enumerate(ir.scenes):
        for node_index, node in enumerate(scene.nodes):
            if node not in declared:
                path = ("scenes", scene_index, "nodes", node_index)
                diagnostics.append(_reference_diagnostic(doc, path, node, candidates))
        for edge_index, edge in enumerate(scene.edges):
            base = ("scenes", scene_index, "edges", edge_index)
            if edge.from_ not in declared:
                diagnostics.append(
                    _reference_diagnostic(doc, (*base, "from"), edge.from_, candidates)
                )
            if edge.to not in declared:
                diagnostics.append(
                    _reference_diagnostic(doc, (*base, "to"), edge.to, candidates)
                )
    return diagnostics


def validate_grammar_fit(ir: SemanticIR, doc: LoadedDocument) -> list[Diagnostic]:
    """Check each scene's grammar is registered and minimally satisfiable.

    An unregistered grammar or a scene with no nodes is a ``VIR1005`` grammar-fit
    error: the scene cannot be laid out as declared. Both v1 grammars
    (``pipeline`` and ``showcase``) lay out nodes, so an empty scene fails
    regardless of grammar. The grammar registry is the single source of truth for
    what "registered" means.
    """
    register_builtins()
    diagnostics: list[Diagnostic] = []
    for scene_index, scene in enumerate(ir.scenes):
        if not is_registered(scene.grammar):
            location = nearest_location(doc, ("scenes", scene_index, "grammar"))
            span = (
                span_from_location(location, "unknown grammar")
                if location is not None
                else None
            )
            known = ", ".join(sorted(registered_ids()))
            diagnostics.append(
                Diagnostic(
                    code=VIR_GRAMMAR_FIT,
                    message=f'unknown grammar "{scene.grammar}"',
                    span=span,
                    help=f"register the grammar or use one of: {known}",
                )
            )
            continue
        if not scene.nodes:
            location = nearest_location(doc, ("scenes", scene_index))
            span = (
                span_from_location(location, f"{scene.grammar} needs at least one node")
                if location is not None
                else None
            )
            diagnostics.append(
                Diagnostic(
                    code=VIR_GRAMMAR_FIT,
                    message=f'{scene.grammar} scene "{scene.id}" has no nodes',
                    span=span,
                    help="add at least one node to the scene",
                )
            )
    return diagnostics


def pre_validate(doc: LoadedDocument) -> tuple[SemanticIR | None, list[Diagnostic]]:
    """Run the full P2 pre-validation: schema, then references and grammar fit.

    Schema is the gate — if parsing fails, its diagnostics are returned and the
    reference/grammar-fit checks are skipped (they need a parsed IR). Otherwise
    the aggregated reference and grammar-fit diagnostics are returned alongside
    the parsed IR so the caller can fail with every authoring error at once.
    """
    ir, diagnostics = validate_schema(doc)
    if ir is None:
        return None, diagnostics
    return ir, [*validate_references(ir, doc), *validate_grammar_fit(ir, doc)]


def _reference_diagnostic(
    doc: LoadedDocument, path: DataPath, name: str, candidates: list[str]
) -> Diagnostic:
    location = nearest_location(doc, path)
    span = (
        span_from_location(location, "not declared in entities")
        if location is not None
        else None
    )
    suggestion = difflib.get_close_matches(name, candidates, n=1)
    help_text = f'did you mean "{suggestion[0]}"?' if suggestion else None
    return Diagnostic(
        code=VIR_UNKNOWN_REFERENCE,
        message=f'unknown entity reference "{name}"',
        span=span,
        help=help_text,
    )
