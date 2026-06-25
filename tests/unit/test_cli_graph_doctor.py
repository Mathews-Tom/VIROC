"""CLI graph and doctor coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from viroc.cli import main

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "rag-pipeline"
    project.mkdir()
    (project / "viroc.yaml").write_text("project: rag-pipeline\n", encoding="utf-8")
    (project / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "rag-overview.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return project


def test_graph_prints_scene_entity_structure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)

    assert main(["graph", str(project)]) == 0

    captured = capsys.readouterr()
    assert "video: rag-overview" in captured.out
    assert "scene: pipeline" in captured.out
    assert "documents -[split]-> chunks" in captured.out
    assert "embedder [model] Embedding Model" in captured.out


def test_doctor_reports_backend_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)

    status = main(["doctor", str(project), "--backend", "manim"])

    captured = capsys.readouterr()
    assert "backend: manim" in captured.out
    assert "status: " in captured.out
    if "status: unavailable" in captured.out:
        assert status == 1
        assert "VIR5" in captured.err
    else:
        assert status == 0


def test_doctor_reports_unknown_backend_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)

    assert main(["doctor", str(project), "--backend", "static"]) == 1

    captured = capsys.readouterr()
    assert "VIR5011" in captured.err
    assert 'available backends: "html", "manim", "motion_canvas", "remotion"' in captured.err
