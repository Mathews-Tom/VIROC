"""Renderer capability manifests and shared compatibility diagnostics.

Every top-three backend (Manim, HTML, Remotion) renders a *common floor* of
primitives and animations natively (:data:`COMMON_FLOOR_PRIMITIVES`,
:data:`COMMON_FLOOR_ANIMATIONS`). The richer ``showcase`` grammar also emits
*above-floor* primitives (``code``, ``formula``); a backend that cannot render
one either declares an explicit **deterministic degradation** to a floor
primitive — kept and surfaced as a non-blocking :data:`VIR_DEGRADED_PRIMITIVE`
note — or rejects it with a blocking :data:`VIR_UNSUPPORTED_PRIMITIVE` error.
The parity policy is therefore explicit per backend: true support, declared
degradation, or hard failure — never a silent omission.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from viroc.core import Diagnostic, DiagnosticClass, Severity, code
from viroc.ir import ConcreteIR

VIR_UNSUPPORTED_PRIMITIVE = code(DiagnosticClass.RENDERER, 31)
VIR_UNSUPPORTED_ANIMATION = code(DiagnosticClass.RENDERER, 32)
VIR_DEGRADED_PRIMITIVE = code(DiagnosticClass.RENDERER, 33)

COMMON_FLOOR_PRIMITIVES = frozenset({"arrow", "rect", "text"})
"""Primitives every top-three backend renders natively (the portable floor)."""

COMMON_FLOOR_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
"""Keyframe kinds every top-three backend renders natively (the portable floor)."""

_EMPTY_DEGRADATIONS: Mapping[str, str] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Declared backend support for Concrete IR primitives and animations.

    ``degradations`` maps an above-floor primitive the backend cannot render to
    the floor primitive it deterministically renders instead. A degraded
    primitive is *supported via degradation*, not unsupported: it produces a
    non-blocking note, never a blocking error.
    """

    primitives: frozenset[str]
    animations: frozenset[str]
    degradations: Mapping[str, str] = _EMPTY_DEGRADATIONS

    def __post_init__(self) -> None:
        object.__setattr__(self, "primitives", frozenset(self.primitives))
        object.__setattr__(self, "animations", frozenset(self.animations))
        object.__setattr__(self, "degradations", MappingProxyType(dict(self.degradations)))

    def degraded_to(self, primitive: str) -> str | None:
        """Return the floor primitive ``primitive`` degrades to, or ``None``."""
        return self.degradations.get(primitive)


def support_diagnostics(
    adapter_id: str,
    manifest: CapabilityManifest,
    ir: ConcreteIR,
    *,
    primitive_fallback_backend: str | None = None,
    primitive_fallback_backends: tuple[str, ...] = (),
) -> list[Diagnostic]:
    """Return renderer diagnostics for unsupported or degraded Concrete IR content.

    A primitive the backend lists is silent; one it declares a degradation for
    yields a non-blocking :data:`VIR_DEGRADED_PRIMITIVE` note; anything else
    yields a blocking :data:`VIR_UNSUPPORTED_PRIMITIVE` error. Animations have no
    degradation path — an unsupported keyframe kind is always a blocking error.
    """
    fallback_backends = _fallback_backends(
        primitive_fallback_backend,
        primitive_fallback_backends,
    )
    diagnostics: list[Diagnostic] = []
    for obj in ir.objects:
        if obj.primitive in manifest.primitives:
            continue
        degraded = manifest.degraded_to(obj.primitive)
        if degraded is not None:
            diagnostics.append(
                degraded_primitive_diagnostic(
                    adapter_id,
                    obj.primitive,
                    degraded,
                    object_id=obj.id,
                )
            )
            continue
        diagnostics.append(
            unsupported_primitive_diagnostic(
                adapter_id,
                obj.primitive,
                object_id=obj.id,
                fallback_backends=fallback_backends,
            )
        )
    for keyframe in ir.keyframes:
        if keyframe.kind not in manifest.animations:
            diagnostics.append(
                unsupported_animation_diagnostic(
                    adapter_id,
                    keyframe.kind,
                    object_id=keyframe.object_id,
                )
            )
    return diagnostics


def unsupported_primitive_diagnostic(
    adapter_id: str,
    primitive: str,
    *,
    object_id: str,
    fallback_backends: tuple[str, ...] = (),
) -> Diagnostic:
    """Build the diagnostic for an unsupported object primitive."""
    if not fallback_backends:
        help_text = f'provide a fallback image asset for object "{object_id}"'
    else:
        help_text = (
            f"{_fallback_help(fallback_backends)}, or provide a fallback image asset "
            f'for object "{object_id}"'
        )
    return Diagnostic(
        code=VIR_UNSUPPORTED_PRIMITIVE,
        message=f'renderer "{adapter_id}" does not support primitive "{primitive}"',
        help=help_text,
    )


def degraded_primitive_diagnostic(
    adapter_id: str,
    primitive: str,
    target: str,
    *,
    object_id: str,
) -> Diagnostic:
    """Build the non-blocking note for a deterministically degraded primitive."""
    return Diagnostic(
        code=VIR_DEGRADED_PRIMITIVE,
        severity=Severity.NOTE,
        message=(
            f'renderer "{adapter_id}" renders primitive "{primitive}" '
            f'as "{target}" (deterministic degradation)'
        ),
        help=(
            f'object "{object_id}" keeps its placement and title; render on a '
            f'backend with native "{primitive}" support for full fidelity'
        ),
    )


def _fallback_backends(
    fallback_backend: str | None,
    fallback_backends: tuple[str, ...],
) -> tuple[str, ...]:
    ordered: list[str] = []
    if fallback_backend is not None:
        ordered.append(fallback_backend)
    for backend in fallback_backends:
        if backend not in ordered:
            ordered.append(backend)
    return tuple(ordered)


def _fallback_help(backends: tuple[str, ...]) -> str:
    if len(backends) == 1:
        return f'use renderer "{backends[0]}"'
    quoted = ", ".join(f'"{backend}"' for backend in backends[:-1])
    return f"use renderer {quoted}, or \"{backends[-1]}\""


def unsupported_animation_diagnostic(
    adapter_id: str,
    animation: str,
    *,
    object_id: str,
) -> Diagnostic:
    """Build the diagnostic for an unsupported keyframe kind."""
    return Diagnostic(
        code=VIR_UNSUPPORTED_ANIMATION,
        message=f'renderer "{adapter_id}" does not support animation "{animation}"',
        help=(
            f'lower object "{object_id}" to a supported animation '
            'or select a backend that supports this keyframe kind'
        ),
    )


__all__ = [
    "COMMON_FLOOR_ANIMATIONS",
    "COMMON_FLOOR_PRIMITIVES",
    "CapabilityManifest",
    "VIR_DEGRADED_PRIMITIVE",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "degraded_primitive_diagnostic",
    "support_diagnostics",
    "unsupported_animation_diagnostic",
    "unsupported_primitive_diagnostic",
]
