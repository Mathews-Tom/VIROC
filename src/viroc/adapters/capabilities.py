"""Renderer capability manifests and shared compatibility diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from viroc.core import Diagnostic, DiagnosticClass, code
from viroc.ir import ConcreteIR

VIR_UNSUPPORTED_PRIMITIVE = code(DiagnosticClass.RENDERER, 31)
VIR_UNSUPPORTED_ANIMATION = code(DiagnosticClass.RENDERER, 32)


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Declared backend support for Concrete IR primitives and animations."""

    primitives: frozenset[str]
    animations: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "primitives", frozenset(self.primitives))
        object.__setattr__(self, "animations", frozenset(self.animations))


def support_diagnostics(
    adapter_id: str,
    manifest: CapabilityManifest,
    ir: ConcreteIR,
    *,
    primitive_fallback_backend: str | None = None,
    primitive_fallback_backends: tuple[str, ...] = (),
) -> list[Diagnostic]:
    """Return renderer diagnostics for unsupported Concrete IR content."""
    fallback_backends = _fallback_backends(
        primitive_fallback_backend,
        primitive_fallback_backends,
    )
    diagnostics: list[Diagnostic] = []
    for obj in ir.objects:
        if obj.primitive not in manifest.primitives:
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
    "CapabilityManifest",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "support_diagnostics",
    "unsupported_animation_diagnostic",
    "unsupported_primitive_diagnostic",
]
