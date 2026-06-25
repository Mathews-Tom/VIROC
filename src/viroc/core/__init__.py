"""Cross-cutting compiler primitives: stable IDs, hashing, diagnostics, build context."""

from __future__ import annotations

from viroc.core.ids import slugify, stable_id

__all__ = ["slugify", "stable_id"]
