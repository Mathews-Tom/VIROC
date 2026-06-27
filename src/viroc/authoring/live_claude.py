"""Optional Claude-backed planner path for M17 authoring flow."""

from __future__ import annotations

import importlib.util
import os
from importlib import import_module
from typing import Any

from viroc.authoring.io import dump_yaml
from viroc.authoring.models import AuthoringBrief, LivePlannerStatus, ScenePlan
from viroc.ir import VideoMeta

_MODEL = "claude-opus-4-8"


class LivePlannerError(RuntimeError):
    """Raised when the optional live planner cannot run or returns invalid data."""


def live_planner_status() -> LivePlannerStatus:
    """Report whether the optional Claude-backed planner can run locally."""

    if importlib.util.find_spec("anthropic") is None:
        return LivePlannerStatus(
            available=False,
            reason="Anthropic SDK is not installed",
            help="install the optional planner extra (for example: uv sync --extra planner)",
        )
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return LivePlannerStatus(available=True)
    return LivePlannerStatus(
        available=False,
        reason="Anthropic credentials are not configured",
        help="set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN before using --live",
    )


def build_live_scene_plan(brief: AuthoringBrief) -> ScenePlan:
    """Call Claude to expand the brief into a structured scene plan."""

    status = live_planner_status()
    if not status.available:
        raise LivePlannerError(_status_message(status))

    try:
        anthropic: Any = import_module("anthropic")
        client = anthropic.Anthropic()
    except Exception as exc:
        raise LivePlannerError(
            "live planner setup failed; reinstall the planner extra "
            "and verify Anthropic credentials"
        ) from exc
    prompt = _prompt_for(brief)
    try:
        response = client.messages.parse(
            model=_MODEL,
            max_tokens=4000,
            system=_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
            output_format=ScenePlan,
        )
    except anthropic.AuthenticationError as exc:
        raise LivePlannerError(f"live planner authentication failed: {exc}") from exc
    except anthropic.APIConnectionError as exc:
        raise LivePlannerError(f"live planner connection failed: {exc}") from exc
    except anthropic.APIStatusError as exc:
        request_id = getattr(exc, "request_id", None)
        suffix = f" (request_id={request_id})" if request_id else ""
        raise LivePlannerError(f"live planner request failed: {exc.message}{suffix}") from exc

    parsed = response.parsed_output
    if parsed is None:
        raise LivePlannerError("live planner returned no structured scene plan")
    return ScenePlan(
        video=_resolved_video(brief, parsed.video),
        entities=parsed.entities,
        scenes=parsed.scenes,
    )


def _resolved_video(brief: AuthoringBrief, video: VideoMeta) -> VideoMeta:
    return VideoMeta(
        id=brief.project.id,
        title=brief.project.title,
        duration_target=brief.project.duration_target,
        fps=video.fps,
        resolution=video.resolution,
    )


def _status_message(status: LivePlannerStatus) -> str:
    message = status.reason or "live planner is unavailable"
    if status.help:
        return f"{message}; {status.help}"
    return message


def _system_prompt() -> str:
    return (
        "You plan VIROC authoring artifacts. Return a ScenePlan only. "
        "Keep VidIR as the only compiler input. Preserve renderer neutrality, use "
        'the pipeline grammar, keep scene ids/entity ids slug-safe, and ensure every '
        "scene references declared entities only."
    )


def _prompt_for(brief: AuthoringBrief) -> str:
    return (
        "Build a deterministic starter scene plan for this VIROC authoring brief. "
        "Use the provided project identity, entities, and scene seeds as anchors. "
        "Return only data that fits the ScenePlan schema.\n\n"
        f"{dump_yaml(brief)}"
    )


__all__ = ["LivePlannerError", "build_live_scene_plan", "live_planner_status"]
