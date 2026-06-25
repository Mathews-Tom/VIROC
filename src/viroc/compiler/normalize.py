"""Normalize: the stable, pure canonicalization step (pipeline phase P3).

Normalization runs on the Semantic IR after pre-validation and before grammar
expansion (design §3). It is a pure function: identical input always yields an
identical, canonical Semantic IR, so golden hashes and diffs stay stable across
runs and machines.

This module owns the four normalization capabilities design §3 P3 names —
*stable IDs · defaults · units · colors* — but applies only what the Semantic IR
actually carries today:

- :func:`normalize` canonicalizes every author-supplied id into the stable slug
  form and rewrites the references that point at it (scene nodes, edge
  endpoints, ``required_entities``) so the graph stays consistent. Re-validating
  the transformed document materializes defaults. It is idempotent and
  deterministic.
- :func:`parse_duration` and :func:`normalize_color` are the strict unit/color
  primitives. The Semantic IR holds durations verbatim (resolved to frames in
  M7) and carries no colours yet (styles arrive with the grammar in M6), so
  these are consumed downstream rather than applied here. Both reject ambiguous
  input rather than silently coercing it (no guessed units, no unknown colours).
"""

from __future__ import annotations

import re

from viroc.core import slugify
from viroc.ir import SemanticIR

_DURATION_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)s")
_HEX_RE = re.compile(r"#?(?P<hex>[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def parse_duration(text: str) -> float:
    """Parse an ``"Ns"`` duration into seconds, rejecting ambiguous input.

    Accepts a non-negative number with an explicit ``s`` (seconds) suffix:
    ``"4s"`` -> ``4.0``, ``"0.5s"`` -> ``0.5``. There is no silent coercion — a
    bare number (``"4"``), an unknown unit (``"4ms"``, ``"4sec"``), or any other
    shape raises :class:`ValueError`. Zero (``"0s"``) parses; whether a
    zero-length duration is *valid* is a timing concern decided downstream (M8).
    """
    match = _DURATION_RE.fullmatch(text.strip())
    if match is None:
        raise ValueError(
            f"ambiguous duration {text!r}: expected a number with an 's' suffix, e.g. '4s'"
        )
    return float(match.group("value"))


def normalize_color(text: str) -> str:
    """Normalize a hex colour into canonical lowercase ``#rrggbb`` form.

    Accepts 3- or 6-digit hex with or without a leading ``#``; 3-digit shorthand
    is expanded (``"#FFF"`` -> ``"#ffffff"``). The transform is idempotent.
    Anything that is not hex raises :class:`ValueError` rather than guessing — no
    named-colour table is assumed in v1.
    """
    match = _HEX_RE.fullmatch(text.strip())
    if match is None:
        raise ValueError(
            f"unrecognized colour {text!r}: expected 3- or 6-digit hex, e.g. '#1a2b3c'"
        )
    digits = match.group("hex").lower()
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits}"


def normalize(ir: SemanticIR) -> SemanticIR:
    """Canonicalize ``ir`` into a stable, deterministic Semantic IR.

    Every author-supplied id (video, entities, scenes, beats) is slugified into
    the snake_case stable form, and every reference to an entity (scene
    ``nodes``, edge ``from``/``to``, ``required_entities``) is rewritten through
    the same map so the graph stays consistent. Re-validating the transformed
    document materializes field defaults.

    The function is pure: ``normalize(normalize(x)) == normalize(x)`` (slugify is
    idempotent) and the output is byte-stable across runs.
    """
    data = ir.model_dump(by_alias=True)

    entity_id_map = {entity["id"]: slugify(entity["id"]) for entity in data["entities"]}

    def resolve(reference: str) -> str:
        return entity_id_map.get(reference, slugify(reference))

    data["video"]["id"] = slugify(data["video"]["id"])

    for entity in data["entities"]:
        entity["id"] = slugify(entity["id"])

    for scene in data["scenes"]:
        scene["id"] = slugify(scene["id"])
        scene["nodes"] = [resolve(node) for node in scene["nodes"]]
        for edge in scene["edges"]:
            edge["from"] = resolve(edge["from"])
            edge["to"] = resolve(edge["to"])
        for beat in scene["beats"]:
            beat["id"] = slugify(beat["id"])

    if data.get("validation") is not None:
        data["validation"]["required_entities"] = [
            resolve(name) for name in data["validation"]["required_entities"]
        ]

    return SemanticIR.model_validate(data)
