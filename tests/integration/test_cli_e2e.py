"""End-to-end CLI coverage for the committed rag-pipeline example."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "rag-pipeline"
_EXPECTED_SOURCE = (_EXAMPLE / "expected" / "source.sha256").read_text(encoding="utf-8").strip()
_EXPECTED_RENDER = json.loads((_EXAMPLE / "expected" / "render.json").read_text(encoding="utf-8"))
_FIXTURES = _ROOT / "tests" / "fixtures"


@pytest.mark.integration
def test_cli_e2e_example_and_failing_storyboard(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", str(_EXAMPLE), "--backend", "manim"]) == 0
    assert capsys.readouterr().err == ""

    assert main(["compile", str(_EXAMPLE), "--backend", "manim"]) == 0
    compile_out = capsys.readouterr().out
    generated = _EXAMPLE / "build" / "generated" / "manim" / "scene.py"
    assert generated.exists()
    assert str(generated) in compile_out
    assert f"source_hash: {_EXPECTED_SOURCE}" in compile_out

    assert main(["graph", str(_EXAMPLE)]) == 0
    graph_out = capsys.readouterr().out
    assert "video: rag-overview" in graph_out
    assert "scene: pipeline" in graph_out
    assert "documents -[split]-> chunks" in graph_out

    doctor_status = main(["doctor", str(_EXAMPLE), "--backend", "manim"])
    doctor_capture = capsys.readouterr()
    assert "backend: manim" in doctor_capture.out
    assert "status: " in doctor_capture.out
    if "status: unavailable" in doctor_capture.out:
        assert doctor_status == 1
        assert "VIR5" in doctor_capture.err
    else:
        assert doctor_status == 0

    manifest_path = _EXAMPLE / "build" / "build.json"
    video_path = _EXAMPLE / "build" / "rag-overview.mp4"
    srt_path = _EXAMPLE / "build" / "captions.srt"
    for path in (manifest_path, video_path, srt_path):
        if path.exists():
            path.unlink()

    render_status = main(["render", str(_EXAMPLE), "--backend", "manim"])
    render_capture = capsys.readouterr()
    if manifest_path.exists():
        assert render_status == 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert video_path.exists()
        assert srt_path.exists()
        assert str(video_path) in render_capture.out
        assert str(manifest_path) in render_capture.out
        assert manifest["source_hash"] == _EXPECTED_SOURCE
        assert manifest["perceptual_hash"] == _EXPECTED_RENDER["perceptual_hash"]
    else:
        assert render_status == 1
        assert "VIR5" in render_capture.err

    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "viroc.yaml").write_text("project: broken\n", encoding="utf-8")
    (broken / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "bad-time.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["check", str(broken)]) == 1
    assert "VIR2001" in capsys.readouterr().err
