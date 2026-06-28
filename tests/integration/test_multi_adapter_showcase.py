"""Integration coverage for the multi-adapter VIROC codebase flagship showcase.

The flagship walks the guided flow (ingest -> plan -> critique -> compile ->
render) and demonstrates it with committed, regenerable artifacts: the authoring
provenance, the critique review surface, top-three deterministic compile output,
and an env-gated Manim preview. The richer ``showcase`` grammar emits above-floor
``code``/``formula`` primitives that degrade deterministically to ``rect`` with a
non-blocking ``VIR5033`` note on Manim and render natively on HTML/Remotion.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest
import yaml

import viroc.adapters.html as html_adapter
import viroc.adapters.manim as manim_adapter
import viroc.adapters.remotion as remotion_adapter
from viroc.cli import main
from viroc.cli._common import load_expected_render_baseline, load_project

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "viroc-codebase"
_README = (_EXAMPLE / "README.md").read_text(encoding="utf-8")
_STORYBOARD = cast(
    dict[str, object],
    yaml.safe_load((_EXAMPLE / "storyboard.vidir.yaml").read_text(encoding="utf-8")),
)
_GALLERY = cast(
    dict[str, object],
    json.loads((_EXAMPLE / "expected" / "gallery.json").read_text(encoding="utf-8")),
)
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
_GALLERY_SOURCE_ROOTS = {
    "manim": "expected/generated/manim",
    "html": "expected/generated/html",
    "remotion": "expected/generated/remotion",
}
_EXPECTED_SOURCE_HASHES = {
    backend: (
        (_EXAMPLE / "expected" / backend / "source.sha256")
        .read_text(encoding="utf-8")
        .strip()
    )
    for backend in _BACKEND_MODULES
}

_STORY_ARC_IDS = [
    "concept_input",
    "script_and_scene_plan",
    "editable_vidir",
    "validate_repair",
    "storyboard_review",
    "compile_fanout",
    "parity_proof",
]
_PREVIEW_FILES = {
    "video_entry": "expected/preview/manim/viroc-codebase.mp4",
    "captions_entry": "expected/preview/manim/captions.srt",
    "manifest_entry": "expected/preview/manim/build.json",
}
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
_PROJECT = load_project(_EXAMPLE)


def _clean_build() -> None:
    shutil.rmtree(_EXAMPLE / "build", ignore_errors=True)


@pytest.mark.integration
def test_viroc_codebase_showcase_check_compile_and_gallery(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_build()

    # Default backend is manim, which degrades the richer showcase's code/formula
    # primitives to rect; check still exits 0 and surfaces the VIR5033 notes.
    assert main(["check", str(_EXAMPLE)]) == 0
    assert "VIR5033" in capsys.readouterr().err

    for backend, generated in _COMPILE_OUTPUTS.items():
        assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
        compile_capture = capsys.readouterr()
        assert str(generated) in compile_capture.out
        assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in compile_capture.out
        assert generated.exists()

    assert _GALLERY["project"] == "viroc-codebase"
    assert _GALLERY["tagline"] == "Topic to verified video. Typed IR. Portable renderers."
    assert _GALLERY["grammar"] == "showcase"
    assert _GALLERY["storyboard"] == "storyboard.vidir.yaml"
    story_arc = cast(list[dict[str, str]], _GALLERY["story_arc"])
    assert [entry["id"] for entry in story_arc] == _STORY_ARC_IDS
    assert story_arc[1]["claim"] == (
        "The guided planner derives a script, a scene plan, and an outline."
    )
    preview = cast(dict[str, str], _GALLERY["preview"])
    assert preview["backend"] == "manim"
    for key, value in _PREVIEW_FILES.items():
        assert preview[key] == value
        assert (_EXAMPLE / value).exists()

    backends = cast(list[dict[str, object]], _GALLERY["backends"])
    assert [entry["id"] for entry in backends] == ["manim", "html", "remotion"]

    for entry in backends:
        backend = cast(str, entry["id"])
        capabilities = cast(dict[str, list[str]], entry["capabilities"])
        adapter = _BACKEND_MODULES[backend]
        assert entry["source_root"] == _GALLERY_SOURCE_ROOTS[backend]
        assert entry["source_entry"] == _GALLERY_SOURCE_ENTRIES[backend]
        assert (_EXAMPLE / cast(str, entry["source_root"])).exists()
        assert (_EXAMPLE / cast(str, entry["source_entry"])).exists()
        assert entry["source_hash"] == _EXPECTED_SOURCE_HASHES[backend]
        assert capabilities["primitives"] == sorted(adapter.capabilities.primitives)
        assert capabilities["animations"] == sorted(adapter.capabilities.animations)
        assert _EXPECTED_SOURCE_HASHES[backend] in _README

    assert "Committed generated source lives under `expected/generated/`" in _README
    assert "`expected/preview/manim/viroc-codebase.mp4`" in _README
    assert (
        "The machine-readable companion for this scene arc, committed source "
        "roots, guided-flow artifacts, and preview paths is `expected/gallery.json`."
        in _README
    )


@pytest.mark.integration
@pytest.mark.parametrize("backend", ["manim", "html", "remotion"])
def test_viroc_codebase_showcase_render_matrix(
    backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_build()

    status = main(["render", str(_EXAMPLE), "--backend", backend])
    render_capture = capsys.readouterr()
    manifest_path = _EXAMPLE / "build" / "build.json"
    video_path = _EXAMPLE / "build" / "viroc-codebase.mp4"
    srt_path = _EXAMPLE / "build" / "captions.srt"
    baseline = load_expected_render_baseline(_PROJECT, backend=backend)

    # Skip only on a missing render environment (error[VIR5...]); the non-blocking
    # note[VIR5033] degradation notes must never mask a real render failure.
    if status == 1 and "error[VIR5" in render_capture.err:
        reason = next(
            line for line in render_capture.err.splitlines() if "error[VIR5" in line
        )
        pytest.skip(reason)

    assert status == 0
    assert manifest_path.exists()
    assert video_path.exists()
    assert srt_path.exists()
    assert str(video_path) in render_capture.out
    assert str(manifest_path) in render_capture.out
    assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in render_capture.out

    manifest = cast(
        dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    renderer = cast(dict[str, object], manifest["renderer"])
    perceptual_hash = cast(str, manifest["perceptual_hash"])

    assert manifest["project"] == "viroc-codebase"
    assert manifest["source_hash"] == _EXPECTED_SOURCE_HASHES[backend]
    assert renderer["id"] == backend
    assert isinstance(renderer["version"], str)
    assert perceptual_hash.startswith("phash:")

    if baseline is not None:
        assert perceptual_hash == baseline.perceptual_hash


@pytest.mark.integration
def test_flagship_uses_richer_showcase_composition() -> None:
    """The flagship exercises the showcase grammar's non-row compositions, not one row."""
    scenes = cast(list[dict[str, object]], _STORYBOARD["scenes"])
    assert scenes
    assert {cast(str, scene["grammar"]) for scene in scenes} == {"showcase"}

    has_fan_out = False
    has_comparison = False
    for scene in scenes:
        edges = cast(list[dict[str, str]], scene.get("edges", []))
        sources = [edge["from"] for edge in edges]
        if any(sources.count(source) >= 2 for source in sources):
            has_fan_out = True
        if any(edge.get("kind") == "compare" for edge in edges):
            has_comparison = True
    assert has_fan_out, "expected a fan-out scene (a node sourcing >=2 edges)"
    assert has_comparison, "expected a comparison scene (a compare edge)"


@pytest.mark.integration
def test_top_three_compile_is_deterministic_and_pinned(
    capsys: pytest.CaptureFixture[str],
) -> None:
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
def test_manim_compile_degrades_code_and_formula_not_omitted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Manim compile exits 0 and surfaces VIR5033 degradation notes, never VIR5031."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", "manim"]) == 0
    err = capsys.readouterr().err
    assert "VIR5031" not in err
    assert 'renders primitive "code" as "rect"' in err
    assert 'renders primitive "formula" as "rect"' in err
    assert (_EXAMPLE / "build" / "generated" / "manim" / "scene.py").exists()


@pytest.mark.integration
def test_gallery_degradations_and_parity_match_adapter_capabilities() -> None:
    """The gallery's per-backend degradations + parity mirror the adapters' policy."""
    backends = cast(list[dict[str, object]], _GALLERY["backends"])
    for entry in backends:
        adapter = _BACKEND_MODULES[cast(str, entry["id"])]
        assert entry["degradations"] == dict(adapter.capabilities.degradations)
    by_id = {cast(str, entry["id"]): entry for entry in backends}
    assert by_id["manim"]["degradations"] == {"code": "rect", "formula": "rect"}
    assert by_id["html"]["degradations"] == {}
    assert by_id["remotion"]["degradations"] == {}

    parity = cast(dict[str, list[str]], _GALLERY["parity"])
    assert parity["floor"] == ["arrow", "rect", "text"]
    assert parity["above_floor"] == ["code", "formula"]
    # Above-floor primitives are native on the web backends, degraded on Manim.
    for primitive in parity["above_floor"]:
        assert primitive in dict(manim_adapter.capabilities.degradations)
        assert primitive in html_adapter.capabilities.primitives
        assert primitive in remotion_adapter.capabilities.primitives
        assert primitive not in manim_adapter.capabilities.primitives


@pytest.mark.integration
def test_committed_manim_preview_matches_source_and_baseline() -> None:
    """The env-gated Manim preview is diagnostic-backed: pinned to source and baseline."""
    preview_manifest = cast(
        dict[str, object],
        json.loads(
            (_EXAMPLE / "expected" / "preview" / "manim" / "build.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    assert preview_manifest["source_hash"] == _EXPECTED_SOURCE_HASHES["manim"]
    perceptual_hash = cast(str, preview_manifest["perceptual_hash"])
    assert perceptual_hash.startswith("phash:")

    baseline = load_expected_render_baseline(_PROJECT, backend="manim")
    assert baseline is not None
    assert perceptual_hash == baseline.perceptual_hash
    for name in ("viroc-codebase.mp4", "captions.srt", "build.json"):
        assert (_EXAMPLE / "expected" / "preview" / "manim" / name).exists()
    # HTML keeps no committed perceptual baseline: its render is env-gated.
    assert load_expected_render_baseline(_PROJECT, backend="html") is None


@pytest.mark.integration
def test_guided_flow_artifacts_are_regenerable_and_stable(tmp_path: Path) -> None:
    """ingest + plan reproduce the committed flagship provenance byte-for-byte."""
    work = tmp_path / "viroc-codebase"
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
    work = tmp_path / "viroc-codebase"
    shutil.copytree(_EXAMPLE, work)
    shutil.rmtree(work / "build", ignore_errors=True)

    assert main(["critique", str(work)]) == 0
    capsys.readouterr()
    review = work / "build" / "review"
    committed = _EXAMPLE / "expected" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review / name).read_bytes() == (committed / name).read_bytes(), name


@pytest.mark.integration
def test_gallery_authoring_block_points_at_committed_provenance() -> None:
    """The gallery authoring block references the committed guided-flow artifacts."""
    authoring = cast(dict[str, str], _GALLERY["authoring"])
    assert authoring["request"] == "authoring-request.yaml"
    assert authoring["brief"] == "authoring-brief.yaml"
    assert authoring["script"] == "script.md"
    assert authoring["scene_plan"] == "scene-plan.yaml"
    assert authoring["review"] == "expected/review/"
    for key in ("request", "brief", "script", "scene_plan"):
        assert (_EXAMPLE / authoring[key]).exists()
    assert (_EXAMPLE / "expected" / "review").is_dir()


@pytest.mark.integration
def test_readme_carries_guided_flow_and_provenance() -> None:
    """The README documents the guided flow on the shared template."""
    for heading in (
        "## Guided flow",
        "## Scene arc",
        "## Top-three parity",
        "## Inspectable artifacts",
    ):
        assert heading in _README
    assert "viroc ingest examples/viroc-codebase/authoring-request.yaml" in _README
    assert "| Concept input | `authoring-request.yaml` | hand-authored |" in _README
