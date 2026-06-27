"""Unit coverage for the M17 guided authoring flow."""

from __future__ import annotations

import os
from pathlib import Path

from viroc.authoring import (
    build_authoring_brief,
    build_scene_plan,
    build_script_document,
    load_ingest_request,
    scene_plan_to_vidir,
    script_markdown,
)
from viroc.authoring.live_claude import live_planner_status

_ROOT = Path(__file__).resolve().parents[2]
_TOPIC_REQUEST = _ROOT / "tests" / "fixtures" / "authoring" / "topic-brief.yaml"
_REPO_REQUEST = _ROOT / "tests" / "fixtures" / "authoring" / "repo-brief.yaml"


def test_ingest_builds_stable_brief_with_context() -> None:
    request = load_ingest_request(_TOPIC_REQUEST)
    brief = build_authoring_brief(request, _TOPIC_REQUEST)

    assert brief.project.id == "guided_authoring_flow"
    assert brief.project.title == "Guided VIROC Authoring Flow"
    assert brief.project.duration_target == 24
    assert brief.source.kind == "topic"
    assert [item.kind for item in brief.context_items] == ["note", "document"]
    assert brief.context_items[1].label == "overview"
    assert brief.context_items[1].digest is not None
    assert brief.context_items[1].digest.startswith("sha256:")
    assert "VIROC" in brief.context_items[1].excerpt


def test_scene_plan_script_and_vidir_lower_deterministically() -> None:
    request = load_ingest_request(_TOPIC_REQUEST)
    brief = build_authoring_brief(request, _TOPIC_REQUEST)

    first = build_scene_plan(brief)
    second = build_scene_plan(brief)
    assert first == second
    assert [scene.id for scene in first.scenes] == [
        "topic_intake",
        "script_drafting",
        "scene_planning",
        "validation_handoff",
    ]

    script = build_script_document(brief, first)
    markdown = script_markdown(script)
    assert "# Script — Guided VIROC Authoring Flow" in markdown
    assert "## Topic intake" in markdown
    assert "VidIR" in markdown

    storyboard = scene_plan_to_vidir(first)
    assert storyboard.video.id == "guided_authoring_flow"
    assert storyboard.validation is not None
    assert storyboard.validation.checks == ["schema", "layout", "timing"]
    assert [scene.id for scene in storyboard.scenes] == [
        "topic_intake",
        "script_drafting",
        "scene_planning",
        "validation_handoff",
    ]


def test_repo_ingest_captures_repo_file_context() -> None:
    request = load_ingest_request(_REPO_REQUEST)
    brief = build_authoring_brief(request, _REPO_REQUEST)

    repo_items = [item for item in brief.context_items if item.kind == "repo_file"]
    assert [item.label for item in repo_items] == ["README.md", "design.md"]
    assert all(item.digest and item.digest.startswith("sha256:") for item in repo_items)
    assert brief.notes == ["Keep the walkthrough grounded in real repo files."]


def test_live_planner_status_is_explicit() -> None:
    status = live_planner_status()

    if status.available:
        assert os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        return

    assert status.reason is not None
    assert status.help is not None
