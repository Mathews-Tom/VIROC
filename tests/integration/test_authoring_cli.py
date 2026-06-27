"""Integration coverage for the ingest + live-planner halves of M17."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from viroc.authoring import authoring_brief_filename, scene_plan_filename, script_filename
from viroc.authoring.live_claude import live_planner_status
from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "authoring"


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    fixture_root = tmp_path / "tests" / "fixtures" / "authoring"
    fixture_root.mkdir(parents=True)
    shutil.copy2(_FIXTURES / "topic-brief.yaml", fixture_root / "topic-brief.yaml")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    shutil.copy2(_ROOT / "docs" / "overview.md", docs_dir / "overview.md")

    return fixture_root / "topic-brief.yaml", fixture_root / "happy-path-project"


@pytest.mark.integration
def test_authoring_commands_appear_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ingest", "--help"]) == 0
    ingest_help = capsys.readouterr()
    assert "authoring-brief.yaml" in ingest_help.out
    assert ingest_help.err == ""

    assert main(["plan", "--help"]) == 0
    plan_help = capsys.readouterr()
    assert "script.md" in plan_help.out
    assert "storyboard.vidir.yaml" in plan_help.out
    assert "--force" in plan_help.out
    assert plan_help.err == ""


@pytest.mark.integration
def test_ingest_invalid_request_fails_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad_request = tmp_path / "bad-request.yaml"
    bad_request.write_text("source: [broken\n", encoding="utf-8")

    assert main(["ingest", str(bad_request)]) == 2
    captured = capsys.readouterr()
    assert "failed to load authoring request" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.integration
def test_ingest_writes_authoring_brief(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)

    assert main(["ingest", str(request_path)]) == 0
    ingest_capture = capsys.readouterr()
    assert str(project_path / authoring_brief_filename()) in ingest_capture.out
    assert ingest_capture.err == ""
    assert (project_path / authoring_brief_filename()).exists()


@pytest.mark.integration
def test_plan_invalid_brief_fails_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)
    assert main(["ingest", str(request_path)]) == 0
    _ = capsys.readouterr()

    (project_path / authoring_brief_filename()).write_text("project: [broken\n", encoding="utf-8")

    assert main(["plan", str(project_path)]) == 2
    captured = capsys.readouterr()
    assert "failed to load authoring inputs" in captured.err
    assert "Traceback" not in captured.err



@pytest.mark.integration
def test_ingest_plan_and_check_happy_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)

    assert main(["ingest", str(request_path)]) == 0
    ingest_capture = capsys.readouterr()
    assert str(project_path / authoring_brief_filename()) in ingest_capture.out
    assert ingest_capture.err == ""

    assert main(["plan", str(project_path)]) == 0
    plan_capture = capsys.readouterr()
    assert str(project_path / scene_plan_filename()) in plan_capture.out
    assert str(project_path / script_filename()) in plan_capture.out
    assert str(project_path / "storyboard.vidir.yaml") in plan_capture.out
    assert plan_capture.err == ""

    assert (project_path / authoring_brief_filename()).exists()
    assert (project_path / scene_plan_filename()).exists()
    assert (project_path / script_filename()).exists()
    assert (project_path / "storyboard.vidir.yaml").exists()

    assert main(["check", str(project_path)]) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.integration
def test_plan_refuses_to_overwrite_edited_storyboard_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)
    assert main(["ingest", str(request_path)]) == 0
    _ = capsys.readouterr()
    assert main(["plan", str(project_path)]) == 0
    _ = capsys.readouterr()

    storyboard = project_path / "storyboard.vidir.yaml"
    storyboard.write_text("vidir_version: '0.1'\nvideo: [broken]\n", encoding="utf-8")

    assert main(["plan", str(project_path)]) == 2
    captured = capsys.readouterr()
    assert "already contains edits" in captured.err
    assert "Traceback" not in captured.err

    assert main(["plan", str(project_path), "--force"]) == 0
    forced = capsys.readouterr()
    assert str(project_path / "storyboard.vidir.yaml") in forced.out
    assert forced.err == ""

@pytest.mark.integration
def test_live_plan_reports_unavailable_without_fallback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)
    assert main(["ingest", str(request_path)]) == 0
    _ = capsys.readouterr()

    status = live_planner_status()
    if status.available:
        pytest.skip(
            "live planner credentials are configured; "
            "unavailable-path assertion not applicable"
        )

    assert main(["plan", str(project_path), "--live"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert status.reason is not None
    assert status.reason in captured.err
    assert status.help is not None
    assert status.help in captured.err


@pytest.mark.integration
def test_live_plan_happy_path_is_env_gated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)
    assert main(["ingest", str(request_path)]) == 0
    _ = capsys.readouterr()

    status = live_planner_status()
    if not status.available:
        pytest.skip("Anthropic live planner is unavailable")

    assert main(["plan", str(project_path), "--live", "--force"]) == 0
    live_capture = capsys.readouterr()
    assert str(project_path / scene_plan_filename()) in live_capture.out
    assert live_capture.err == ""
