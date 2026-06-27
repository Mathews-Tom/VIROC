"""Typed authoring artifacts that sit before editable VidIR.

These models define the pre-VidIR authoring surface introduced in M17:
request/brief intake, a human-readable script view, and a structured scene plan
that can be lowered into a starter storyboard. VidIR remains the only compiler
input; these are authoring aids and planning intermediates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from viroc.ir import Edge, EdgeKind, Entity, SemanticIR, ValidationSpec, VideoMeta

SourceKind = Literal["topic", "repo", "documents"]
ContextItemKind = Literal["note", "document", "repo_file"]


class _Model(BaseModel):
    """Shared strict config for every authoring model."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectRequest(_Model):
    """Project location and defaults for an ingest request."""

    path: str
    id: str | None = None
    title: str | None = None
    duration_target: int = 30
    default_backend: str = "manim"


class SourceRequest(_Model):
    """User-authored concept input before context files are materialized."""

    kind: SourceKind
    title: str
    prompt: str
    audience: str
    objective: str


class ContextFileRequest(_Model):
    """One file to ingest into the authoring brief."""

    path: str
    label: str | None = None


class RepoContextRequest(_Model):
    """A repo root plus the specific files to capture into the brief."""

    root: str
    files: list[str]


class ContextRequest(_Model):
    """Optional document/repo context for an ingest request."""

    documents: list[ContextFileRequest] = []
    repo: RepoContextRequest | None = None
    notes: list[str] = []


class SceneSeed(_Model):
    """A lightweight authoring outline before the full scene plan exists."""

    title: str
    goal: str
    narration: str
    nodes: list[str]
    duration: str = "6s"
    grammar: str = "pipeline"
    edges: list[Edge] = []
    edge_kind: EdgeKind = "flow"
    id: str | None = None


class IngestRequest(_Model):
    """Typed request file consumed by ``viroc ingest``."""

    request_version: str = "0.1"
    project: ProjectRequest
    source: SourceRequest
    entities: list[Entity]
    scene_seeds: list[SceneSeed]
    context: ContextRequest | None = None


class BriefProject(_Model):
    """Project metadata recorded into a stable authoring brief."""

    id: str
    title: str
    duration_target: int
    default_backend: str


class ContextItem(_Model):
    """Materialized context item with deterministic digest + excerpt."""

    kind: ContextItemKind
    label: str
    excerpt: str
    path: str | None = None
    digest: str | None = None


class AuthoringBrief(_Model):
    """Normalized concept input written by ``viroc ingest``."""

    brief_version: str = "0.1"
    project: BriefProject
    source: SourceRequest
    entities: list[Entity]
    scene_seeds: list[SceneSeed]
    context_items: list[ContextItem] = []
    notes: list[str] = []


class ScriptScene(_Model):
    """Human-reviewable script slice for one planned scene."""

    scene_id: str
    title: str
    goal: str
    duration: str
    narration: str


class ScriptDocument(_Model):
    """The reviewable script emitted beside the scene plan and VidIR."""

    script_version: str = "0.1"
    title: str
    audience: str
    objective: str
    scenes: list[ScriptScene]


class PlannedScene(_Model):
    """Structured scene plan entry used to derive starter VidIR."""

    id: str
    title: str
    goal: str
    grammar: str = "pipeline"
    duration: str
    nodes: list[str] = []
    edges: list[Edge] = []
    narration: str


class ScenePlan(_Model):
    """Authoring-time scene plan, richer than VidIR but still renderer-neutral."""

    scene_plan_version: str = "0.1"
    video: VideoMeta
    entities: list[Entity]
    scenes: list[PlannedScene]


class PlannedStoryboard(_Model):
    """Wrapper pairing the scene plan with the starter VidIR it lowers to."""

    scene_plan: ScenePlan
    storyboard: SemanticIR


class LivePlannerStatus(_Model):
    """Diagnosed availability for the optional Claude-backed planner path."""

    available: bool
    reason: str | None = None
    help: str | None = None


__all__ = [
    "AuthoringBrief",
    "BriefProject",
    "ContextFileRequest",
    "ContextItem",
    "ContextItemKind",
    "ContextRequest",
    "IngestRequest",
    "LivePlannerStatus",
    "PlannedScene",
    "PlannedStoryboard",
    "ProjectRequest",
    "RepoContextRequest",
    "ScenePlan",
    "SceneSeed",
    "ScriptDocument",
    "ScriptScene",
    "SemanticIR",
    "SourceKind",
    "SourceRequest",
    "ValidationSpec",
    "VideoMeta",
]
