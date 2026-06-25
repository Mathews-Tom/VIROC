"""Stable identifier helpers.

The compiler derives object identifiers from author-supplied labels (e.g. when
normalizing a Semantic IR into resolved objects). Those identifiers must be
deterministic — identical input always yields the identical id — so that golden
hashes and diffs stay stable across runs and machines.

Two helpers cover the need:

- :func:`slugify` turns arbitrary text into a single lowercase identifier token.
- :func:`stable_id` joins slugified parts into a dot-namespaced compound id.

Both are pure, deterministic, and reject input that cannot yield a usable id
rather than silently producing an empty or ambiguous value.
"""

from __future__ import annotations

import re

_SEP = "_"
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Normalize ``text`` into a stable, lowercase identifier slug.

    Letters are lowercased; every run of non-alphanumeric characters collapses
    to a single underscore; leading and trailing underscores are stripped. The
    result matches the snake_case identifier style used throughout the IR
    (``"Vector DB"`` -> ``"vector_db"``).

    The transform is idempotent: ``slugify(slugify(x)) == slugify(x)``. Text
    with no alphanumeric characters has no representable id and raises
    :class:`ValueError` rather than returning an empty string.
    """
    slug = _NON_SLUG.sub(_SEP, text.lower()).strip(_SEP)
    if not slug:
        raise ValueError(f"text {text!r} contains no slug-able characters")
    return slug


def stable_id(*parts: str) -> str:
    """Join ``parts`` into a deterministic, dot-namespaced identifier.

    Each part is independently slugified, so ``stable_id("pipeline", "Vector DB",
    "box")`` yields ``"pipeline.vector_db.box"``. Order is significant and
    preserved. Slugifying first guarantees parts never contain the ``.``
    separator, keeping the namespacing unambiguous. At least one part is
    required; an empty or unslug-able part raises :class:`ValueError`.
    """
    if not parts:
        raise ValueError("stable_id requires at least one part")
    return ".".join(slugify(part) for part in parts)
