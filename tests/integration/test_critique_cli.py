"""Integration coverage for the ``viroc critique`` review surface (M18)."""

from __future__ import annotations

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
