"""End-to-end CLI coverage for the committed rag-pipeline example."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "rag-pipeline"
_EXPECTED_SOURCE = (_EXAMPLE / "expected" / "source.sha256").read_text(encoding="utf-8").strip()
_EXPECTED_HTML_SOURCE = (
    _EXAMPLE / "expected" / "html" / "source.sha256"
).read_text(encoding="utf-8").strip()
_EXPECTED_REMOTION_SOURCE = (
    _EXAMPLE / "expected" / "remotion" / "source.sha256"
).read_text(encoding="utf-8").strip()
_EXPECTED_MOTION_CANVAS_SOURCE = (
    _EXAMPLE / "expected" / "motion_canvas" / "source.sha256"
).read_text(encoding="utf-8").strip()
_EXPECTED_IMAGE_SEQUENCE_SOURCE = (
    _EXAMPLE / "expected" / "image_sequence" / "source.sha256"
).read_text(encoding="utf-8").strip()
_EXPECTED_STATIC_STORYBOARD_SOURCE = (
    _EXAMPLE / "expected" / "static_storyboard" / "source.sha256"
).read_text(encoding="utf-8").strip()
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

    assert main(["compile", str(_EXAMPLE), "--backend", "html"]) == 0
    html_compile_out = capsys.readouterr().out
    html_generated = _EXAMPLE / "build" / "generated" / "html" / "scene.html"
    assert html_generated.exists()
    assert str(html_generated) in html_compile_out
    assert f"source_hash: {_EXPECTED_HTML_SOURCE}" in html_compile_out

    assert main(["compile", str(_EXAMPLE), "--backend", "remotion"]) == 0
    remotion_compile_out = capsys.readouterr().out
    remotion_generated = _EXAMPLE / "build" / "generated" / "remotion"
    assert remotion_generated.exists()
    assert str(remotion_generated) in remotion_compile_out
    assert (remotion_generated / "package.json").exists()
    assert (remotion_generated / "tsconfig.json").exists()
    assert (remotion_generated / "src" / "index.ts").exists()
    assert (remotion_generated / "src" / "Root.tsx").exists()
    assert (remotion_generated / "src" / "Composition.tsx").exists()
    assert f"source_hash: {_EXPECTED_REMOTION_SOURCE}" in remotion_compile_out

    assert main(["compile", str(_EXAMPLE), "--backend", "motion_canvas"]) == 0
    motion_canvas_compile_out = capsys.readouterr().out
    motion_canvas_generated = _EXAMPLE / "build" / "generated" / "motion_canvas"
    assert motion_canvas_generated.exists()
    assert str(motion_canvas_generated) in motion_canvas_compile_out
    assert (motion_canvas_generated / "package.json").exists()
    assert (motion_canvas_generated / "vite.config.ts").exists()
    assert (motion_canvas_generated / "src" / "project.ts").exists()
    assert (motion_canvas_generated / "src" / "scenes" / "viroc.tsx").exists()
    assert f"source_hash: {_EXPECTED_MOTION_CANVAS_SOURCE}" in motion_canvas_compile_out

    assert main(["compile", str(_EXAMPLE), "--backend", "image_sequence"]) == 0
    image_sequence_compile_out = capsys.readouterr().out
    image_sequence_generated = _EXAMPLE / "build" / "generated" / "image_sequence"
    assert image_sequence_generated.exists()
    assert str(image_sequence_generated) in image_sequence_compile_out
    assert (image_sequence_generated / "frame-plan.json").exists()
    assert (image_sequence_generated / "summary.md").exists()
    assert (image_sequence_generated / "captions.md").exists()
    assert f"source_hash: {_EXPECTED_IMAGE_SEQUENCE_SOURCE}" in image_sequence_compile_out

    assert main(["compile", str(_EXAMPLE), "--backend", "static_storyboard"]) == 0
    static_storyboard_compile_out = capsys.readouterr().out
    static_storyboard_generated = _EXAMPLE / "build" / "generated" / "static_storyboard"
    assert static_storyboard_generated.exists()
    assert str(static_storyboard_generated) in static_storyboard_compile_out
    assert (static_storyboard_generated / "storyboard.md").exists()
    assert (static_storyboard_generated / "scene-cards.json").exists()
    assert (static_storyboard_generated / "script.md").exists()
    assert (static_storyboard_generated / "captions.md").exists()
    assert f"source_hash: {_EXPECTED_STATIC_STORYBOARD_SOURCE}" in static_storyboard_compile_out

    assert main(["graph", str(_EXAMPLE)]) == 0
    graph_out = capsys.readouterr().out
    assert "scene: problem_setup" in graph_out
    assert "scene: payoff" in graph_out
    assert "bare_answer -[compare]-> retrieved_context" in graph_out

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
        assert manifest["perceptual_hash"].startswith("phash:")
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
