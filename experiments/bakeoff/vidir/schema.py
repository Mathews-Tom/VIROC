"""Throwaway mocked VidIR schema for the M1 de-risking bake-off.

This is NOT the compiler. It is a hand-mocked Semantic IR (design.md §2.2),
used only to demonstrate that the VidIR intermediate is *mechanically
validatable* — schema + reference + grammar-fit checks that framework code
(raw Manim / React) structurally cannot offer.

Scope guard: nothing under ``src/viroc`` may import this module. The real,
specified Semantic IR is built in milestone M4; this mock is discarded once the
bake-off gate is recorded (overview.md §7, DEVELOPMENT_PLAN.md §4 M1).
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal[
    "data_source", "intermediate", "model", "storage", "service", "user"
]
EdgeKind = Literal["flow", "split", "transform", "store", "merge", "compare"]

REGISTERED_GRAMMARS: frozenset[str] = frozenset({"pipeline"})


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: EntityType


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    kind: EdgeKind = "flow"


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    grammar: str
    duration: str
    nodes: list[str] = []
    edges: list[Edge] = []
    narration: str | None = None


class VideoMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    fps: int = 30
    resolution: tuple[int, int] = (1920, 1080)
    duration_target: int | None = None


class SemanticIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vidir_version: str
    video: VideoMeta
    entities: list[Entity]
    scenes: list[Scene]


class VidirError(ValueError):
    """A VidIR reference / grammar-fit defect (mirrors the VIR1xxx range)."""


def _unknown_reference(ref: str, declared: set[str], scene_id: str, where: str) -> str:
    suggestion = difflib.get_close_matches(ref, sorted(declared), n=1)
    hint = f"; did you mean {suggestion[0]!r}?" if suggestion else ""
    return (
        f"VIR1002: unknown entity reference {ref!r} "
        f"({where} in scene {scene_id!r}){hint}"
    )


def validate_references(ir: SemanticIR) -> None:
    """Reference + grammar-fit checks. Raises ``VidirError`` on the first defect.

    Demonstrates the "validate" axis: every scene must use a registered grammar,
    every node / edge endpoint must resolve to a declared entity, and every edge
    endpoint must participate in the scene's node set. This is the
    class of check raw Manim and React cannot express.
    """
    declared = {entity.id for entity in ir.entities}
    for scene in ir.scenes:
        if scene.grammar not in REGISTERED_GRAMMARS:
            raise VidirError(
                f"VIR1003: scene {scene.id!r} uses unregistered grammar "
                f"{scene.grammar!r} (registered: {sorted(REGISTERED_GRAMMARS)})"
            )
        for node in scene.nodes:
            if node not in declared:
                raise VidirError(
                    _unknown_reference(node, declared, scene.id, "node")
                )
        scene_nodes = set(scene.nodes)
        for edge in scene.edges:
            for ref, where in ((edge.from_, "edge.from"), (edge.to, "edge.to")):
                if ref not in declared:
                    raise VidirError(
                        _unknown_reference(ref, declared, scene.id, where)
                    )
                if ref not in scene_nodes:
                    raise VidirError(
                        f"VIR1004: {where} {ref!r} in scene {scene.id!r} is not "
                        f"among the scene's nodes {sorted(scene_nodes)}"
                    )


def load(path: str | Path) -> SemanticIR:
    """Parse, schema-validate, and reference-validate a ``*.vidir.yaml`` file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ir = SemanticIR.model_validate(data)
    validate_references(ir)
    return ir
