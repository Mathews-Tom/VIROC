"""Integration coverage for the showcase-composition grammar proof example.

This example exercises the bounded ``showcase`` grammar (non-row grid, fan-out,
comparison) and its above-floor ``code``/``formula`` primitives: native on HTML,
Remotion, and the static-storyboard review surface; deterministically degraded to
``rect`` with a non-blocking ``VIR5033`` note on Manim. The compiler-level golden
contract lives separately under ``tests/fixtures`` + ``tests/golden`` and is
decoupled from this example's committed baselines.
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
import viroc.adapters.static_storyboard as static_storyboard_adapter
from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "showcase-composition"
_README = (_EXAMPLE / "README.md").read_text(encoding="utf-8")
_BACKEND_MODULES = {
    "manim": manim_adapter,
    "html": html_adapter,
    "remotion": remotion_adapter,
    "static_storyboard": static_storyboard_adapter,
}
_SUPPORTED_BACKENDS = tuple(_BACKEND_MODULES)
_COMPILE_OUTPUTS = {
    "manim": _EXAMPLE / "build" / "generated" / "manim" / "scene.py",
    "html": _EXAMPLE / "build" / "generated" / "html" / "scene.html",
    "remotion": _EXAMPLE / "build" / "generated" / "remotion",
    "static_storyboard": _EXAMPLE / "build" / "generated" / "static_storyboard",
}
_GALLERY_SOURCE_ENTRIES = {
    "manim": "expected/generated/manim/scene.py",
    "html": "expected/generated/html/scene.html",
    "remotion": "expected/generated/remotion/package.json",
    "static_storyboard": "expected/generated/static_storyboard/storyboard.md",
}
_EXPECTED_SOURCE_HASHES = {
    backend: (_EXAMPLE / "expected" / backend / "source.sha256")
    .read_text(encoding="utf-8")
    .strip()
    for backend in _SUPPORTED_BACKENDS
}
_STORY_ARC_IDS = ["title_card", "primitives", "fanout", "comparison"]
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
def test_check_passes_with_no_diagnostics(capsys: pytest.CaptureFixture[str]) -> None:
    """The example passes pre-validation on its default (review) backend with no output."""
    assert main(["check", str(_EXAMPLE)]) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.integration
@pytest.mark.parametrize("backend", _SUPPORTED_BACKENDS)
def test_compiles_with_committed_hash(
    backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each supported backend compiles to exit 0 with its committed source hash."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
    captured = capsys.readouterr()
    generated = _COMPILE_OUTPUTS[backend]
    assert str(generated) in captured.out
    assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in captured.out
    assert generated.exists()
    assert (_EXAMPLE / _GALLERY_SOURCE_ENTRIES[backend]).exists()
    assert _EXPECTED_SOURCE_HASHES[backend] in _README


@pytest.mark.integration
def test_compile_is_deterministic_and_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    """Every supported backend compiles to its committed hash, twice, identically."""
    for backend in _SUPPORTED_BACKENDS:
        digests: list[str] = []
        for _ in range(2):
            _clean_build()
            assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
            out = capsys.readouterr().out
            line = next(line for line in out.splitlines() if line.startswith("source_hash: "))
            digests.append(line.removeprefix("source_hash: "))
        assert digests[0] == digests[1] == _EXPECTED_SOURCE_HASHES[backend]


@pytest.mark.integration
def test_manim_degrades_code_and_formula_not_omitted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Manim lacks code/formula, so it degrades to rect with VIR5033 notes, exit 0."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", "manim"]) == 0
    err = capsys.readouterr().err
    assert "VIR5033" in err
    assert 'renders primitive "code" as "rect"' in err
    assert 'renders primitive "formula" as "rect"' in err
    assert "VIR5031" not in err
    assert (_EXAMPLE / "build" / "generated" / "manim" / "scene.py").exists()


@pytest.mark.integration
def test_guided_flow_artifacts_are_regenerable_and_stable(tmp_path: Path) -> None:
    """ingest + plan reproduce the committed provenance byte-for-byte."""
    work = tmp_path / "showcase-composition"
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
    work = tmp_path / "showcase-composition"
    shutil.copytree(_EXAMPLE, work)
    shutil.rmtree(work / "build", ignore_errors=True)

    assert main(["critique", str(work)]) == 0
    capsys.readouterr()
    review = work / "build" / "review"
    committed = _EXAMPLE / "expected" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review / name).read_bytes() == (committed / name).read_bytes(), name


@pytest.mark.integration
def test_gallery_schema_and_above_floor_parity() -> None:
    """gallery.json carries the shared schema; above-floor primitives degrade on Manim."""
    gallery = cast(
        dict[str, object],
        json.loads((_EXAMPLE / "expected" / "gallery.json").read_text(encoding="utf-8")),
    )
    assert gallery["project"] == "showcase-composition"
    assert gallery["grammar"] == "showcase"
    preview = cast(dict[str, str], gallery["preview"])
    assert preview["backend"] == "manim"
    assert preview["video_entry"] == "expected/preview/manim/showcase-composition.mp4"
    assert (_EXAMPLE / preview["video_entry"]).exists()

    authoring = cast(dict[str, str], gallery["authoring"])
    assert authoring["request"] == "authoring-request.yaml"
    assert authoring["review"] == "expected/review/"

    story_arc = cast(list[dict[str, str]], gallery["story_arc"])
    assert [entry["id"] for entry in story_arc] == _STORY_ARC_IDS

    parity = cast(dict[str, list[str]], gallery["parity"])
    assert parity["floor"] == ["arrow", "rect", "text"]
    assert parity["above_floor"] == ["code", "formula"]

    backends = cast(list[dict[str, object]], gallery["backends"])
    assert [entry["id"] for entry in backends] == list(_SUPPORTED_BACKENDS)
    by_id = {cast(str, entry["id"]): entry for entry in backends}
    assert by_id["manim"]["degradations"] == {"code": "rect", "formula": "rect"}
    for backend in ("html", "remotion", "static_storyboard"):
        assert by_id[backend]["degradations"] == {}
    # Above-floor primitives degrade on Manim, are native on the web/review backends.
    for primitive in parity["above_floor"]:
        assert primitive in dict(manim_adapter.capabilities.degradations)
        assert primitive in html_adapter.capabilities.primitives
        assert primitive in remotion_adapter.capabilities.primitives

    for entry in backends:
        backend = cast(str, entry["id"])
        adapter = _BACKEND_MODULES[backend]
        capabilities = cast(dict[str, list[str]], entry["capabilities"])
        assert (_EXAMPLE / cast(str, entry["source_root"])).exists()
        assert (_EXAMPLE / cast(str, entry["source_entry"])).exists()
        assert entry["source_hash"] == _EXPECTED_SOURCE_HASHES[backend]
        assert capabilities["primitives"] == sorted(adapter.capabilities.primitives)
        assert capabilities["animations"] == sorted(adapter.capabilities.animations)


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
    assert (
        "The machine-readable companion for this scene arc, committed source "
        "roots, guided-flow artifacts, and parity story is `expected/gallery.json`."
        in _README
    )
