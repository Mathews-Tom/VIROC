"""Shared deterministic color palette for renderer emitters.

Every adapter renders the same storyboard, so the fill/stroke/edge/label colors
and the type-to-color mapping live here once instead of drifting per backend.
Emitters resolve a Concrete IR ``style_ref`` to concrete colors at emit time and
bake the literal hex into their generated source, so the generated artifact stays
self-contained and byte-deterministic.

Style refs the grammars emit and this module resolves:

- boxes: ``node.<type>``, ``panel.<type>``, ``callout.<type>`` (colored by entity
  type), ``code_card.<type>`` and ``evidence.<type>`` (distinct code/formula card
  colors so an above-floor card reads as a card even when a backend degrades it
  to ``rect``);
- edges: ``edge.<kind>``;
- text: ``label`` and ``showcase.title``.
"""

from __future__ import annotations

BACKGROUND = "#0B1020"
LABEL_COLOR = "#F8FAFC"
CAPTION_COLOR = "#E2E8F0"
CAPTION_PANEL = "#0F172A"
NEUTRAL_FILL = "#1E293B"
NEUTRAL_STROKE = "#64748B"

# Per entity-type (fill, stroke). One palette for every box-shaped node, so a
# `data_source` is the same blue whether the pipeline grammar drew it as a node
# or the showcase grammar drew it as a panel.
TYPE_FILL: dict[str, tuple[str, str]] = {
    "data_source": ("#1D4ED8", "#60A5FA"),
    "intermediate": ("#7C3AED", "#C4B5FD"),
    "model": ("#BE123C", "#FDA4AF"),
    "storage": ("#047857", "#6EE7B7"),
    "service": ("#0891B2", "#67E8F9"),
    "user": ("#B45309", "#FBBF24"),
}

# Above-floor composition kinds get a distinct card look so they remain legible
# as a code/evidence card even when Manim degrades them to a plain rect.
CODE_CARD: tuple[str, str] = ("#1E293B", "#38BDF8")
EVIDENCE_CARD: tuple[str, str] = ("#312E81", "#818CF8")

EDGE_COLOR: dict[str, str] = {
    "flow": "#94A3B8",
    "default": "#94A3B8",
    "split": "#38BDF8",
    "lookup": "#38BDF8",
    "store": "#22C55E",
    "transform": "#A78BFA",
    "merge": "#F59E0B",
    "compare": "#E879F9",
}


def box_style(style_ref: str) -> tuple[str, str]:
    """Return ``(fill, stroke)`` hex for a box-shaped object's style ref."""
    if style_ref.startswith("code_card."):
        return CODE_CARD
    if style_ref.startswith("evidence."):
        return EVIDENCE_CARD
    entity_type = style_ref.split(".")[-1]
    return TYPE_FILL.get(entity_type, (NEUTRAL_FILL, NEUTRAL_STROKE))


def edge_color(style_ref: str) -> str:
    """Return the stroke hex for an ``edge.<kind>`` style ref."""
    kind = style_ref.split(".", 1)[1] if "." in style_ref else "default"
    return EDGE_COLOR.get(kind, EDGE_COLOR["default"])


def is_card(style_ref: str) -> bool:
    """Return whether a style ref denotes an above-floor code/evidence card."""
    return style_ref.startswith(("code_card.", "evidence."))


__all__ = [
    "BACKGROUND",
    "CAPTION_COLOR",
    "CAPTION_PANEL",
    "CODE_CARD",
    "EDGE_COLOR",
    "EVIDENCE_CARD",
    "LABEL_COLOR",
    "NEUTRAL_FILL",
    "NEUTRAL_STROKE",
    "TYPE_FILL",
    "box_style",
    "edge_color",
    "is_card",
]
