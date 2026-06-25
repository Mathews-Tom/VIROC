"""Unit coverage for the first CLI commands: init and check."""

from __future__ import annotations

from pathlib import Path

import pytest

from viroc.cli import main

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_init_scaffolds_project(tmp_path: Path) -> None:
    project = tmp_path / "demo-video"

    assert main(["init", str(project)]) == 0

    assert (project / "assets").is_dir()
    assert (project / "storyboard.vidir.yaml").exists()
    assert (project / "viroc.yaml").exists()


def test_check_accepts_scaffolded_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "demo-video"
    assert main(["init", str(project)]) == 0
    _ = capsys.readouterr()

    assert main(["check", str(project), "--backend", "manim"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""


def test_check_reports_unknown_backend_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "demo-video"
    assert main(["init", str(project)]) == 0
    _ = capsys.readouterr()

    assert main(["check", str(project), "--backend", "static"]) == 1

    captured = capsys.readouterr()
    assert "VIR5011" in captured.err
    assert (
        'available backends: "html", "image_sequence", "manim", '
        '"motion_canvas", "remotion", "static_storyboard"'
        in captured.err
    )


def test_check_reports_pipeline_diagnostic_for_bad_storyboard(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / "viroc.yaml").write_text("project: broken\n", encoding="utf-8")
    (project / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "bad-time.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["check", str(project)]) == 1

    captured = capsys.readouterr()
    assert "VIR2001" in captured.err
