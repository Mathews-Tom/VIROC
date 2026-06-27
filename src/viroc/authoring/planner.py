"""Deterministic starter planning from an authoring brief to scene plan + VidIR."""

from __future__ import annotations

from viroc.authoring.models import (
    AuthoringBrief,
    PlannedScene,
    PlannedStoryboard,
    ScenePlan,
    SceneSeed,
    ScriptDocument,
    ScriptScene,
)
from viroc.core import slugify
from viroc.ir import Edge, Scene, SemanticIR, ValidationSpec, VideoMeta


def scene_seed_edges(seed: SceneSeed) -> list[Edge]:
    """Return the explicit edges for ``seed`` or a simple left-to-right chain."""

    if seed.edges:
        return list(seed.edges)
    if len(seed.nodes) < 2:
        return []
    return [
        Edge.model_validate({"from": source, "to": target, "kind": seed.edge_kind})
        for source, target in zip(seed.nodes, seed.nodes[1:], strict=False)
    ]


def build_scene_plan(brief: AuthoringBrief) -> ScenePlan:
    """Lower a stable authoring brief into a deterministic scene plan."""

    _validate_scene_seed_references(brief)
    scenes = [
        PlannedScene(
            id=seed.id or slugify(seed.title),
            title=seed.title,
            goal=seed.goal,
            grammar=seed.grammar,
            duration=seed.duration,
            nodes=list(seed.nodes),
            edges=scene_seed_edges(seed),
            narration=seed.narration,
        )
        for seed in brief.scene_seeds
    ]
    video = VideoMeta(
        id=brief.project.id,
        title=brief.project.title,
        duration_target=brief.project.duration_target,
    )
    return ScenePlan(video=video, entities=brief.entities, scenes=scenes)


def build_script_document(brief: AuthoringBrief, scene_plan: ScenePlan) -> ScriptDocument:
    """Render the reviewable script view from the scene plan."""

    return ScriptDocument(
        title=brief.project.title,
        audience=brief.source.audience,
        objective=brief.source.objective,
        scenes=[
            ScriptScene(
                scene_id=scene.id,
                title=scene.title,
                goal=scene.goal,
                duration=scene.duration,
                narration=scene.narration,
            )
            for scene in scene_plan.scenes
        ],
    )


def scene_plan_to_vidir(scene_plan: ScenePlan) -> SemanticIR:
    """Project the richer scene plan down into editable VidIR."""

    return SemanticIR(
        vidir_version="0.1",
        video=scene_plan.video,
        entities=scene_plan.entities,
        scenes=[
            Scene(
                id=scene.id,
                grammar=scene.grammar,
                duration=scene.duration,
                nodes=scene.nodes,
                edges=scene.edges,
                narration=scene.narration,
            )
            for scene in scene_plan.scenes
        ],
        validation=ValidationSpec(
            required_entities=[entity.id for entity in scene_plan.entities],
            checks=["schema", "layout", "timing"],
        ),
    )


def build_storyboard(
    brief: AuthoringBrief, scene_plan: ScenePlan | None = None
) -> PlannedStoryboard:
    """Build the full authoring bundle for one brief."""

    resolved_plan = scene_plan or build_scene_plan(brief)
    storyboard = scene_plan_to_vidir(resolved_plan)
    return PlannedStoryboard(scene_plan=resolved_plan, storyboard=storyboard)


def script_markdown(script: ScriptDocument) -> str:
    """Serialize the script review artifact to Markdown."""

    lines = [
        f"# Script — {script.title}\n",
        "\n",
        f"- audience: {script.audience}\n",
        f"- objective: {script.objective}\n",
        "\n",
    ]
    for scene in script.scenes:
        lines.extend(
            [
                f"## {scene.title}\n",
                "\n",
                f"- scene_id: `{scene.scene_id}`\n",
                f"- duration: `{scene.duration}`\n",
                f"- goal: {scene.goal}\n",
                "\n",
                "### Narration\n",
                "\n",
                f"{scene.narration}\n",
                "\n",
            ]
        )
    return "".join(lines)


def _validate_scene_seed_references(brief: AuthoringBrief) -> None:
    entity_ids = {entity.id for entity in brief.entities}
    for seed in brief.scene_seeds:
        unknown_nodes = [node for node in seed.nodes if node not in entity_ids]
        if unknown_nodes:
            missing = ", ".join(sorted(unknown_nodes))
            raise ValueError(f'scene seed "{seed.title}" references unknown entities: {missing}')
        for edge in scene_seed_edges(seed):
            if edge.from_ not in entity_ids or edge.to not in entity_ids:
                raise ValueError(
                    f'scene seed "{seed.title}" edge references undeclared entities: '
                    f'{edge.from_} -> {edge.to}'
                )


__all__ = [
    "build_scene_plan",
    "build_script_document",
    "build_storyboard",
    "scene_plan_to_vidir",
    "scene_seed_edges",
    "script_markdown",
]
