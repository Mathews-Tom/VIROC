"""Integration coverage for the multi-adapter VIROC codebase showcase."""

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
_EXAMPLE = _ROOT / "examples" / "viroc-codebase"
_README = (_EXAMPLE / "README.md").read_text(encoding="utf-8")
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
    "entry_point",
    "project_scaffold",
    "authored_input",
    "validation_boundary",
    "resolver_boundary",
    "adapter_fanout",
    "proof_artifacts",
]
_PREVIEW_FILES = {
    "video_entry": "expected/preview/manim/viroc-codebase.mp4",
    "captions_entry": "expected/preview/manim/captions.srt",
    "manifest_entry": "expected/preview/manim/build.json",
}
_PROJECT = load_project(_EXAMPLE)


def _clean_build() -> None:
    shutil.rmtree(_EXAMPLE / "build", ignore_errors=True)


@pytest.mark.integration
def test_viroc_codebase_showcase_check_compile_and_gallery(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_build()

    assert main(["check", str(_EXAMPLE)]) == 0
    assert capsys.readouterr().err == ""

    for backend, generated in _COMPILE_OUTPUTS.items():
        assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
        compile_capture = capsys.readouterr()
        assert str(generated) in compile_capture.out
        assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in compile_capture.out
        assert generated.exists()

    assert _GALLERY["project"] == "viroc-codebase"
    assert _GALLERY["tagline"] == "Video IR. Open compiler. Pluggable renderers."
    story_arc = cast(list[dict[str, str]], _GALLERY["story_arc"])
    assert [entry["id"] for entry in story_arc] == _STORY_ARC_IDS
    assert story_arc[1]["claim"] == "viroc init creates viroc.yaml and storyboard.vidir.yaml."
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

    assert "Committed generated source now lives under `expected/generated/`" in _README
    assert "`expected/preview/manim/viroc-codebase.mp4`" in _README
    assert (
        "The machine-readable companion for this scene arc, committed source "
        "roots, and preview paths is `expected/gallery.json`."
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

    if status == 1 and "VIR5" in render_capture.err:
        pytest.skip(render_capture.err.splitlines()[0])

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
