"""Integration coverage for the ``viroc critique`` review surface (M18)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "authoring"
_HAPPY_PATH = _FIXTURES / "happy-path-project"

_REVIEW_ARTIFACTS = ("storyboard.md", "script.md", "scene-cards.json", "captions.md")


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "happy-path-project"
    shutil.copytree(_HAPPY_PATH, project)
    return project


def _authoring_workspace(tmp_path: Path) -> tuple[Path, Path]:
    fixture_root = tmp_path / "tests" / "fixtures" / "authoring"
    fixture_root.mkdir(parents=True)
    shutil.copy2(_FIXTURES / "topic-brief.yaml", fixture_root / "topic-brief.yaml")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    shutil.copy2(_ROOT / "docs" / "overview.md", docs_dir / "overview.md")
    return fixture_root / "topic-brief.yaml", fixture_root / "happy-path-project"


@pytest.mark.integration
def test_critique_appears_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["critique", "--help"]) == 0
    captured = capsys.readouterr()
    assert "review" in captured.out
    assert captured.err == ""


@pytest.mark.integration
def test_critique_writes_review_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)

    assert main(["critique", str(project)]) == 0

    captured = capsys.readouterr()
    review_dir = project / "build" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review_dir / name).is_file(), name
    assert "source_hash: sha256:" in captured.out
    assert captured.err == ""


@pytest.mark.integration
def test_critique_review_artifacts_are_deterministic(tmp_path: Path) -> None:
    project = _project(tmp_path)
    review_dir = project / "build" / "review"

    assert main(["critique", str(project)]) == 0
    first = {name: (review_dir / name).read_text(encoding="utf-8") for name in _REVIEW_ARTIFACTS}

    assert main(["critique", str(project)]) == 0
    second = {name: (review_dir / name).read_text(encoding="utf-8") for name in _REVIEW_ARTIFACTS}

    assert first == second


@pytest.mark.integration
def test_critique_writes_review_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)

    assert main(["critique", str(project)]) == 0

    captured = capsys.readouterr()
    manifest_path = project / "build" / "review" / "review-manifest.json"
    assert manifest_path.is_file()
    assert str(manifest_path) in captured.out
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_hash"].startswith("sha256:")
    assert set(manifest["artifacts"]) == {
        "captions.md",
        "scene-cards.json",
        "script.md",
        "storyboard.md",
    }


@pytest.mark.integration
def test_critique_invalidates_stale_review_on_invalid_vidir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)
    review_dir = project / "build" / "review"

    assert main(["critique", str(project)]) == 0
    assert review_dir.is_dir()
    capsys.readouterr()

    # Replace the storyboard with one that loads but fails timing validation.
    bad_vidir = _ROOT / "tests" / "fixtures" / "bad-time.vidir.yaml"
    (project / "storyboard.vidir.yaml").write_text(
        bad_vidir.read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert main(["critique", str(project)]) == 1
    captured = capsys.readouterr()
    assert "VIR2001" in captured.err
    assert not review_dir.exists()


@pytest.mark.integration
def test_plan_hands_off_into_critique(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _authoring_workspace(tmp_path)

    assert main(["ingest", str(request_path)]) == 0
    capsys.readouterr()

    assert main(["plan", str(project_path)]) == 0
    plan_out = capsys.readouterr()
    assert "next: viroc critique" in plan_out.out
    assert plan_out.err == ""

    assert main(["critique", str(project_path)]) == 0
    critique_out = capsys.readouterr()
    review_dir = project_path / "build" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review_dir / name).is_file(), name
    assert (review_dir / "review-manifest.json").is_file()
    assert "next: viroc compile" in critique_out.out
    assert critique_out.err == ""


@pytest.mark.integration
def test_critique_review_manifest_is_stable_across_runs(tmp_path: Path) -> None:
    project = _project(tmp_path)
    manifest_path = project / "build" / "review" / "review-manifest.json"

    assert main(["critique", str(project)]) == 0
    first = manifest_path.read_text(encoding="utf-8")

    assert main(["critique", str(project)]) == 0
    second = manifest_path.read_text(encoding="utf-8")

    assert first == second


@pytest.mark.integration
def test_critique_broken_vidir_emits_no_review_surface(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / "viroc.yaml").write_text("project: broken\n", encoding="utf-8")
    bad_vidir = _ROOT / "tests" / "fixtures" / "bad-time.vidir.yaml"
    (project / "storyboard.vidir.yaml").write_text(
        bad_vidir.read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert main(["critique", str(project)]) == 1
    captured = capsys.readouterr()
    assert "VIR2001" in captured.err
    assert not (project / "build" / "review").exists()
