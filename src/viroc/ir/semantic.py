"""Semantic IR (VidIR): the typed storyboard humans and agents author.

These Pydantic v2 models are the *only* layer a human or agent writes (design
§2.2, overview §3.1). They are renderer-neutral and carry meaning — entities,
relations, beats, narration — never pixel positions or backend calls; layout and
timing are resolved downstream into the Concrete IR.

Design constraints (design §2.2, cross-cutting §5): composition over
inheritance and *no behaviour on the data classes* — the models hold data only;
parsing lives in :mod:`viroc.ir.io` and checks in :mod:`viroc.validators`. Every
model forbids unknown fields so that authoring typos surface as schema
diagnostics (VIR1xxx) rather than being silently dropped.

Two deviations from the design §2.2 sketch, in service of parsing the authored
form in overview §9.1:

- ``VideoMeta.resolution`` is a :class:`Resolution` mapping (``{width, height}``),
  matching the YAML authors actually write, not the sketch's positional tuple.
- ``SemanticIR.validation`` carries the optional ``validation`` block shown in
  §9.1; without it that block would trip the unknown-field check.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal[
    "data_source", "intermediate", "model", "storage", "service", "user"
]
"""The kind of thing an :class:`Entity` represents (design §2.2)."""

EdgeKind = Literal["flow", "split", "transform", "store", "merge", "compare"]
"""The relationship an :class:`Edge` expresses between two entities (design §2.2)."""


class _Model(BaseModel):
    """Shared strict config for every Semantic IR model.

    ``extra="forbid"`` turns unknown fields into validation errors (so the schema
    validator can report them as VIR1xxx); ``populate_by_name`` lets aliased
    fields — notably :attr:`Edge.from_` — be constructed by either the alias
    (``from``) or the Python field name, which the round-trip relies on.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Resolution(_Model):
    """Frame size in pixels, authored as ``{width, height}`` (overview §9.1)."""

    width: int
    height: int


class VideoMeta(_Model):
    """Top-level video metadata: identity, frame rate, frame size, target length."""

    id: str
    title: str
    fps: int = 30
    resolution: Resolution = Field(
        default_factory=lambda: Resolution(width=1920, height=1080)
    )
    duration_target: int | None = None


class Entity(_Model):
    """A named thing in the diagram (a data source, model, store, …)."""

    id: str
    label: str
    type: EntityType


class Edge(_Model):
    """A directed relationship between two entities.

    The source field is authored as ``from`` (a Python keyword), so it is exposed
    as :attr:`from_` with ``Field(alias="from")``; both the alias and the field
    name construct it (``populate_by_name``).
    """

    from_: str = Field(alias="from")
    to: str
    kind: EdgeKind = "flow"


class Beat(_Model):
    """A timed narration unit. ``at``/``duration`` stay as authored strings here.

    Time expressions (absolute ``"4s"`` or relative ``"after(prev.end)"``) are
    resolved to frames downstream (M7); the Semantic IR keeps them verbatim.
    """

    id: str
    at: str
    duration: str
    narration: str | None = None


class Scene(_Model):
    """One scene: a grammar plus the entities, edges, and beats it lays out."""

    id: str
    grammar: str
    duration: str
    nodes: list[str] = []
    edges: list[Edge] = []
    beats: list[Beat] = []
    narration: str | None = None


class ValidationSpec(_Model):
    """The optional ``validation`` block authors may declare (overview §9.1).

    Advisory metadata only in v1 — recorded but not enforced by the M4
    pre-validation passes.
    """

    required_entities: list[str] = []
    checks: list[str] = []


class SemanticIR(_Model):
    """A complete storyboard: version, video metadata, entities, and scenes."""

    vidir_version: str
    video: VideoMeta
    entities: list[Entity]
    scenes: list[Scene]
    validation: ValidationSpec | None = None
