"""Renderer adapter registration and backend lookup diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

from viroc.adapters import RendererAdapter
from viroc.core import Diagnostic, DiagnosticClass, code

VIR_UNKNOWN_BACKEND = code(DiagnosticClass.RENDERER, 11)
VIR_DUPLICATE_BACKEND = code(DiagnosticClass.RENDERER, 12)


class AdapterRegistryError(RuntimeError):
    """Base class for registry failures that carry a compiler diagnostic."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class UnknownBackendError(AdapterRegistryError):
    """Raised when a caller requests an adapter id that is not registered."""


class DuplicateBackendError(AdapterRegistryError):
    """Raised when an adapter id is registered more than once."""


class AdapterRegistry:
    """In-memory registry keyed by adapter id."""

    def __init__(self, adapters: Iterable[RendererAdapter] = ()) -> None:
        self._adapters: dict[str, RendererAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: RendererAdapter) -> None:
        """Register one adapter id exactly once."""
        existing = self._adapters.get(adapter.id)
        if existing is not None:
            raise DuplicateBackendError(
                duplicate_backend_diagnostic(
                    adapter.id,
                    registered=existing,
                    duplicate=adapter,
                )
            )
        self._adapters[adapter.id] = adapter

    def get(self, adapter_id: str) -> RendererAdapter | None:
        """Return the adapter for ``adapter_id`` when registered."""
        return self._adapters.get(adapter_id)

    def require(self, adapter_id: str) -> RendererAdapter:
        """Return the registered adapter or raise a diagnostic-backed error."""
        adapter = self.get(adapter_id)
        if adapter is None:
            raise UnknownBackendError(unknown_backend_diagnostic(adapter_id, self.ids()))
        return adapter

    def ids(self) -> tuple[str, ...]:
        """Return registered adapter ids in stable order."""
        return tuple(sorted(self._adapters))


def builtin_registry() -> AdapterRegistry:
    """Return the built-in in-repo adapters keyed by backend id."""
    import viroc.adapters.html as html
    import viroc.adapters.manim as manim
    import viroc.adapters.remotion as remotion

    return AdapterRegistry([manim, html, remotion])


def unknown_backend_diagnostic(adapter_id: str, available: Iterable[str]) -> Diagnostic:
    """Build the user-facing diagnostic for an unknown backend id."""
    available_ids = tuple(sorted(set(available)))
    if available_ids:
        help_text = "available backends: " + ", ".join(f'\"{item}\"' for item in available_ids)
    else:
        help_text = "no backends are registered"
    return Diagnostic(
        code=VIR_UNKNOWN_BACKEND,
        message=f'renderer backend "{adapter_id}" is not registered',
        help=help_text,
    )


def duplicate_backend_diagnostic(
    adapter_id: str,
    *,
    registered: RendererAdapter,
    duplicate: RendererAdapter,
) -> Diagnostic:
    """Build the user-facing diagnostic for duplicate adapter registration."""
    return Diagnostic(
        code=VIR_DUPLICATE_BACKEND,
        message=f'renderer backend "{adapter_id}" is already registered',
        help=(
            f"existing adapter: {_adapter_ref(registered)}; "
            f"duplicate adapter: {_adapter_ref(duplicate)}"
        ),
    )


def _adapter_ref(adapter: RendererAdapter) -> str:
    name = getattr(adapter, "__name__", None)
    if isinstance(name, str):
        return name
    adapter_type = type(adapter)
    return f"{adapter_type.__module__}.{adapter_type.__qualname__}"


__all__ = [
    "AdapterRegistry",
    "AdapterRegistryError",
    "DuplicateBackendError",
    "UnknownBackendError",
    "VIR_DUPLICATE_BACKEND",
    "VIR_UNKNOWN_BACKEND",
    "builtin_registry",
    "duplicate_backend_diagnostic",
    "unknown_backend_diagnostic",
]
