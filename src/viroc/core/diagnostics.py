"""Compiler-grade diagnostics: the single error surface for the whole compiler.

Every problem the compiler reports — schema, timing, layout, asset, renderer, or
reproducibility — is a ``Diagnostic`` carrying a stable ``VIRxxxx`` code, a
severity, a human message, an optional source span, and an optional ``help:``
hint, rendered as the compiler-style block shown in overview §9.2.

The ``VIRxxxx`` code space is partitioned into classes (design §5.2). Codes may
only be minted inside an *active*, registered range; the semantic-consistency
(VIR6) and output-validation (VIR8) classes are reserved for a later version and
raise if used. The specific codes are emitted by the checks that own them in
later milestones — this module only defines and guards the space.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum, StrEnum


class Severity(StrEnum):
    """Diagnostic severity; renders as the leading keyword (``error[VIR...]``)."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


class DiagnosticClass(IntEnum):
    """The leading digit of a ``VIRxxxx`` code — its class (design §5.2)."""

    SCHEMA = 1
    TIMING = 2
    LAYOUT = 3
    ASSET = 4
    RENDERER = 5
    SEMANTIC = 6  # reserved in v1
    REPRODUCIBILITY = 7
    OUTPUT = 8  # reserved in v1


# Human labels for each class: the single source of truth for the §5.2 registry,
# reused in the errors raised here and by tooling that lists the code space.
CLASS_LABELS: dict[DiagnosticClass, str] = {
    DiagnosticClass.SCHEMA: "schema / references",
    DiagnosticClass.TIMING: "timing",
    DiagnosticClass.LAYOUT: "layout",
    DiagnosticClass.ASSET: "assets",
    DiagnosticClass.RENDERER: "renderer compatibility",
    DiagnosticClass.SEMANTIC: "semantic consistency",
    DiagnosticClass.REPRODUCIBILITY: "reproducibility",
    DiagnosticClass.OUTPUT: "output validation",
}

# Classes that exist in the registry but are unimplemented in v1.
RESERVED_CLASSES: frozenset[DiagnosticClass] = frozenset(
    {DiagnosticClass.SEMANTIC, DiagnosticClass.OUTPUT}
)

_CODE_RE = re.compile(r"^VIR([1-8])(\d{3})$")
_MAX_NUMBER = 999


def code(cls: DiagnosticClass, number: int) -> str:
    """Allocate a ``VIRxxxx`` code in the active, registered range ``cls``.

    ``number`` is the intra-class number (0-999), zero-padded to three digits, so
    ``code(DiagnosticClass.SCHEMA, 2)`` is ``"VIR1002"``. Reserved classes
    (VIR6/VIR8) and out-of-range numbers raise :class:`ValueError`: a code may
    only be minted inside an active range.
    """
    if cls in RESERVED_CLASSES:
        raise ValueError(
            f"diagnostic class VIR{int(cls)}xxx ({CLASS_LABELS[cls]}) is reserved in v1"
        )
    if not 0 <= number <= _MAX_NUMBER:
        raise ValueError(f"diagnostic number {number} out of range 0-{_MAX_NUMBER}")
    return f"VIR{int(cls)}{number:03d}"


def validate_code(value: str) -> None:
    """Raise :class:`ValueError` unless ``value`` is a code in an active range.

    Enforces the registry on an already-formed code string: the ``VIRxxxx``
    shape, a known class digit, and that the class is not reserved. Used by
    :class:`Diagnostic` so no diagnostic can carry an unregistered code.
    """
    match = _CODE_RE.match(value)
    if match is None:
        raise ValueError(f"diagnostic code {value!r} is not a VIRxxxx code")
    cls = DiagnosticClass(int(match.group(1)))
    if cls in RESERVED_CLASSES:
        raise ValueError(
            f"diagnostic code {value!r} is in reserved class VIR{int(cls)}xxx "
            f"({CLASS_LABELS[cls]}) in v1"
        )

@dataclass(frozen=True, slots=True)
class Span:
    """A source location to underline, with the text to frame and an annotation.

    ``line``/``col`` are 1-based and ``length`` is the number of caret
    characters. ``source`` is the raw text of ``line`` (when available) so the
    renderer can draw the caret frame; ``label`` is the note printed after the
    carets.
    """

    file: str
    line: int
    col: int
    length: int = 1
    source: str | None = None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One compiler diagnostic: a registered code, severity, message, span, help.

    The code is validated against the registry on construction, so a diagnostic
    can never carry an out-of-range or reserved code.
    """

    code: str
    message: str
    severity: Severity = Severity.ERROR
    span: Span | None = None
    help: str | None = None

    def __post_init__(self) -> None:
        validate_code(self.code)
