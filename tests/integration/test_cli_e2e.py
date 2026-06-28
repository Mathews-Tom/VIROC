"""End-to-end CLI coverage for the committed rag-pipeline example.

The rag-pipeline example is the linear ``pipeline`` onboarding showcase: it walks
the guided flow (ingest -> plan -> critique -> compile -> render) and proves that
the floor-only primitive set renders natively on all top-three backends with zero
degradation. The compiler-level golden contracts live separately under
``tests/fixtures`` + ``tests/golden`` and are intentionally decoupled from this
example's committed baselines.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

import viroc.adapters.html as html_adapter
import viroc.adapters.manim as manim_adapter
import viroc.adapters.remotion as remotion_adapter
from viroc.cli import main
from viroc.cli._common import load_expected_render_baseline, load_project

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "rag-pipeline"
_README = (_EXAMPLE / "README.md").read_text(encoding="utf-8")
_FIXTURES = _ROOT / "tests" / "fixtures"
_PROJECT = load_project(_EXAMPLE)

_BACKEND_MODULES = {
    "manim": manim_adapter,
    "html": html_adapter,
    "remotion": remotion_adapter,
}
_COMPILE_OUTPUTS = {
    "manim": _EXAMPLE / "build" / "generated" / "manim" / "scene.py",
    "html": _EXAMPLE / "build" / "generated" / "html" / "scene.html",
    "remotion": _EXAMPLE / "build" / "generated" / "remotion",
}
_GALLERY_SOURCE_ENTRIES = {
    "manim": "expected/generated/manim/scene.py",
    "html": "expected/generated/html/scene.html",
    "remotion": "expected/generated/remotion/package.json",
}
_EXPECTED_SOURCE_HASHES = {
    backend: (_EXAMPLE / "expected" / backend / "source.sha256")
    .read_text(encoding="utf-8")
    .strip()
    for backend in _BACKEND_MODULES
}
_STORY_ARC_IDS = [
    "problem_setup",
    "indexing_path",
    "retrieval_path",
    "answer_synthesis",
    "payoff",
]
_GUIDED_FLOW_ARTIFACTS = (
    "authoring-request.yaml",
    "authoring-brief.yaml",
    "script.md",
    "scene-plan.yaml",
    "storyboard.vidir.yaml",
)
_REVIEW_ARTIFACTS = (
    "storyboard.md",
    "script.md",
    "scene-cards.json",
    "captions.md",
    "review-manifest.json",
)


def _clean_build() -> None:
    shutil.rmtree(_EXAMPLE / "build", ignore_errors=True)


@pytest.mark.integration
def test_check_passes_floor_only_no_degradation(capsys: pytest.CaptureFixture[str]) -> None:
    """The floor-only pipeline example validates clean with no degradation notes."""
    assert main(["check", str(_EXAMPLE), "--backend", "manim"]) == 0
    err = capsys.readouterr().err
    assert err == ""
    assert "VIR5033" not in err


@pytest.mark.integration
@pytest.mark.parametrize("backend", ["manim", "html", "remotion"])
def test_compile_matches_committed_hash(
    backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each top-three backend compiles to exit 0 with its committed source hash."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
    captured = capsys.readouterr()
    generated = _COMPILE_OUTPUTS[backend]
    assert str(generated) in captured.out
    assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in captured.out
    assert "VIR5033" not in captured.err
    assert generated.exists()
    assert (_EXAMPLE / _GALLERY_SOURCE_ENTRIES[backend]).exists()
    assert _EXPECTED_SOURCE_HASHES[backend] in _README


@pytest.mark.integration
def test_compile_is_deterministic_and_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    """Every top-three backend compiles to its committed hash, twice, identically."""
    for backend in _BACKEND_MODULES:
        digests: list[str] = []
        for _ in range(2):
            _clean_build()
            assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
            out = capsys.readouterr().out
            line = next(line for line in out.splitlines() if line.startswith("source_hash: "))
            digests.append(line.removeprefix("source_hash: "))
        assert digests[0] == digests[1] == _EXPECTED_SOURCE_HASHES[backend]


@pytest.mark.integration
def test_guided_flow_artifacts_are_regenerable_and_stable(tmp_path: Path) -> None:
    """ingest + plan reproduce the committed brief/script/scene-plan/storyboard byte-for-byte."""
    work = tmp_path / "rag-pipeline"
    shutil.copytree(_EXAMPLE, work)
    shutil.rmtree(work / "build", ignore_errors=True)

    assert main(["ingest", str(work / "authoring-request.yaml")]) == 0
    assert main(["plan", str(work)]) == 0

    for name in _GUIDED_FLOW_ARTIFACTS:
        assert (work / name).read_bytes() == (_EXAMPLE / name).read_bytes(), name


@pytest.mark.integration
def test_critique_reproduces_committed_review_surface(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """critique writes a deterministic review surface matching expected/review/."""
    work = tmp_path / "rag-pipeline"
    shutil.copytree(_EXAMPLE, work)
    shutil.rmtree(work / "build", ignore_errors=True)

    assert main(["critique", str(work)]) == 0
    review = work / "build" / "review"
    capsys.readouterr()
    committed = _EXAMPLE / "expected" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review / name).read_bytes() == (committed / name).read_bytes(), name


@pytest.mark.integration
def test_gallery_schema_and_floor_only_parity() -> None:
    """gallery.json carries the shared schema; the pipeline example is floor-only."""
    gallery = cast(
        dict[str, object],
        json.loads((_EXAMPLE / "expected" / "gallery.json").read_text(encoding="utf-8")),
    )
    assert gallery["project"] == "rag-overview"
    assert gallery["grammar"] == "pipeline"
    assert gallery["storyboard"] == "storyboard.vidir.yaml"

    authoring = cast(dict[str, str], gallery["authoring"])
    assert authoring["request"] == "authoring-request.yaml"
    assert authoring["brief"] == "authoring-brief.yaml"
    assert authoring["script"] == "script.md"
    assert authoring["scene_plan"] == "scene-plan.yaml"
    assert authoring["review"] == "expected/review/"

    story_arc = cast(list[dict[str, str]], gallery["story_arc"])
    assert [entry["id"] for entry in story_arc] == _STORY_ARC_IDS

    parity = cast(dict[str, list[str]], gallery["parity"])
    assert parity["floor"] == ["arrow", "rect", "text"]
    assert parity["above_floor"] == []

    backends = cast(list[dict[str, object]], gallery["backends"])
    assert [entry["id"] for entry in backends] == ["manim", "html", "remotion"]
    for entry in backends:
        backend = cast(str, entry["id"])
        adapter = _BACKEND_MODULES[backend]
        capabilities = cast(dict[str, list[str]], entry["capabilities"])
        assert (_EXAMPLE / cast(str, entry["source_root"])).exists()
        assert (_EXAMPLE / cast(str, entry["source_entry"])).exists()
        assert entry["source_hash"] == _EXPECTED_SOURCE_HASHES[backend]
        assert capabilities["primitives"] == sorted(adapter.capabilities.primitives)
        assert capabilities["animations"] == sorted(adapter.capabilities.animations)
        assert entry["degradations"] == dict(adapter.capabilities.degradations)


@pytest.mark.integration
def test_committed_preview_is_pinned_to_manim_source() -> None:
    """The env-gated Manim preview manifest is pinned to the committed source + baseline."""
    preview = cast(
        dict[str, object],
        json.loads(
            (_EXAMPLE / "expected" / "preview" / "manim" / "build.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    assert preview["project"] == "rag-overview"
    assert preview["source_hash"] == _EXPECTED_SOURCE_HASHES["manim"]
    perceptual_hash = cast(str, preview["perceptual_hash"])
    assert perceptual_hash.startswith("phash:")

    baseline = load_expected_render_baseline(_PROJECT, backend="manim")
    assert baseline is not None
    assert perceptual_hash == baseline.perceptual_hash
    for name in ("rag-overview.mp4", "captions.srt", "build.json"):
        assert (_EXAMPLE / "expected" / "preview" / "manim" / name).exists()
    assert load_expected_render_baseline(_PROJECT, backend="html") is None


@pytest.mark.integration
def test_readme_carries_shared_template_sections() -> None:
    """The README follows the shared example template."""
    for heading in (
        "## Guided flow",
        "## Scene arc",
        "## Top-three parity",
        "## Inspectable artifacts",
    ):
        assert heading in _README
    assert "Committed generated source lives under `expected/generated/`" in _README
    assert "`expected/preview/manim/rag-overview.mp4`" in _README
    assert (
        "The machine-readable companion for this scene arc, committed source "
        "roots, guided-flow artifacts, and preview paths is `expected/gallery.json`."
        in _README
    )


@pytest.mark.integration
def test_graph_and_doctor(capsys: pytest.CaptureFixture[str]) -> None:
    """graph prints the resolved scene/edge view; doctor reports backend status."""
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


@pytest.mark.integration
def test_render_is_env_gated(capsys: pytest.CaptureFixture[str]) -> None:
    """render either produces the manifest+video or skips on a missing toolchain."""
    _clean_build()
    manifest_path = _EXAMPLE / "build" / "build.json"
    video_path = _EXAMPLE / "build" / "rag-overview.mp4"
    srt_path = _EXAMPLE / "build" / "captions.srt"

    render_status = main(["render", str(_EXAMPLE), "--backend", "manim"])
    render_capture = capsys.readouterr()
    if manifest_path.exists():
        assert render_status == 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert video_path.exists()
        assert srt_path.exists()
        assert str(video_path) in render_capture.out
        assert str(manifest_path) in render_capture.out
        assert manifest["source_hash"] == _EXPECTED_SOURCE_HASHES["manim"]
    else:
        assert render_status == 1
        assert "VIR5" in render_capture.err


@pytest.mark.integration
def test_check_rejects_broken_storyboard(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A storyboard with an out-of-order time window fails check with VIR2001."""
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "viroc.yaml").write_text("project: broken\n", encoding="utf-8")
    (broken / "storyboard.vidir.yaml").write_text(
        (_FIXTURES / "bad-time.vidir.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["check", str(broken)]) == 1
    assert "VIR2001" in capsys.readouterr().err
