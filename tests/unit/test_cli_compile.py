"""CLI compile coverage for deterministic backend source emission."""

from __future__ import annotations

from pathlib import Path

import pytest

from viroc.cli import main
from viroc.core import hash_bytes

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_GOLDEN_SOURCE = Path(__file__).resolve().parents[1] / "golden" / "rag_pipeline_scene.py"


def test_compile_emits_expected_manim_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "rag-pipeline"
    expected_dir = project / "expected"
    expected_dir.mkdir(parents=True)
    (project / "viroc.yaml").write_text("project: rag-pipeline\n", encoding="utf-8")
    (project / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "rag-overview.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (expected_dir / "source.sha256").write_text(
        f"{hash_bytes(_GOLDEN_SOURCE.read_bytes())}\n",
        encoding="utf-8",
    )

    assert main(["compile", str(project), "--backend", "manim"]) == 0

    generated = project / "build" / "generated" / "manim" / "scene.py"
    captured = capsys.readouterr()
    assert generated.exists()
    assert str(generated) in captured.out
    assert f"source_hash: {hash_bytes(_GOLDEN_SOURCE.read_bytes())}" in captured.out


def test_compile_reports_unknown_backend_diagnostic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "rag-pipeline"
    project.mkdir()
    (project / "viroc.yaml").write_text("project: rag-pipeline\n", encoding="utf-8")
    (project / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "rag-overview.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["compile", str(project), "--backend", "static"]) == 1

    captured = capsys.readouterr()
    assert "VIR5011" in captured.err
    assert 'available backends: "html", "image_sequence", "manim", "motion_canvas", "remotion"' in captured.err
