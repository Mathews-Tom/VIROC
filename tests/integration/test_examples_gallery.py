"""Cross-example consistency coverage for the examples/ gallery.

Every example must share one shape: a shared-template README, the guided-flow
provenance, a committed critique review surface, a machine-readable gallery on the
shared schema, per-backend committed source hashes reproduced by a fresh
deterministic compile, and an explicit top-three parity/degradation story. The
top-level examples/README.md indexes the three by role and pins their hashes.
"""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLES_DIR = _ROOT / "examples"
_INDEX = (_EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")

# Example directory -> project id recorded in its gallery.
_EXAMPLES = {
    "rag-pipeline": "rag-overview",
    "showcase-composition": "showcase-composition",
    "viroc-codebase": "viroc-codebase",
}
_README_SECTIONS = (
    "## Guided flow",
    "## Scene arc",
    "## Top-three parity",
    "## Inspectable artifacts",
)
_GUIDED_FLOW_FILES = (
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
_FLOOR = ["arrow", "rect", "text"]


def _gallery(example: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(
            (_EXAMPLES_DIR / example / "expected" / "gallery.json").read_text(
                encoding="utf-8"
            )
        ),
    )


def _adapter(backend: str) -> ModuleType:
    return importlib.import_module(f"viroc.adapters.{backend}")


def _example_backends() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for example in _EXAMPLES:
        backends = cast(list[dict[str, object]], _gallery(example)["backends"])
        for entry in backends:
            pairs.append((example, cast(str, entry["id"])))
    return pairs


@pytest.mark.integration
def test_index_lists_every_example_with_tagline_and_pinned_hashes() -> None:
    """examples/README.md links each example, its tagline, and its abbreviated hashes."""
    for example in _EXAMPLES:
        gallery = _gallery(example)
        assert f"[`{example}`]({example}/)" in _INDEX
        assert cast(str, gallery["tagline"]) in _INDEX
        backends = cast(list[dict[str, object]], gallery["backends"])
        for entry in backends:
            abbreviated = cast(str, entry["source_hash"]).split(":", 1)[1][:7]
            assert abbreviated in _INDEX, (example, entry["id"], abbreviated)


@pytest.mark.integration
@pytest.mark.parametrize("example", list(_EXAMPLES))
def test_example_readme_uses_shared_template(example: str) -> None:
    """Every example README carries the shared-template sections."""
    readme = (_EXAMPLES_DIR / example / "README.md").read_text(encoding="utf-8")
    for section in _README_SECTIONS:
        assert section in readme, (example, section)
    assert "Committed generated source lives under `expected/generated/`" in readme


@pytest.mark.integration
@pytest.mark.parametrize("example", list(_EXAMPLES))
def test_example_carries_guided_flow_provenance_and_review(example: str) -> None:
    """Every example ships committed guided-flow provenance and a review surface."""
    root = _EXAMPLES_DIR / example
    for name in _GUIDED_FLOW_FILES:
        assert (root / name).is_file(), (example, name)
    review = root / "expected" / "review"
    for name in _REVIEW_ARTIFACTS:
        assert (review / name).is_file(), (example, name)


@pytest.mark.integration
@pytest.mark.parametrize("example", list(_EXAMPLES))
def test_example_gallery_schema(example: str) -> None:
    """Every gallery.json carries the shared schema."""
    gallery = _gallery(example)
    assert gallery["project"] == _EXAMPLES[example]
    assert isinstance(gallery["tagline"], str)
    assert gallery["grammar"] in {"pipeline", "showcase"}
    assert gallery["storyboard"] == "storyboard.vidir.yaml"

    authoring = cast(dict[str, str], gallery["authoring"])
    assert authoring["request"] == "authoring-request.yaml"
    assert authoring["brief"] == "authoring-brief.yaml"
    assert authoring["script"] == "script.md"
    assert authoring["scene_plan"] == "scene-plan.yaml"
    assert authoring["review"] == "expected/review/"

    story_arc = cast(list[dict[str, str]], gallery["story_arc"])
    assert story_arc and all({"id", "claim"} <= set(entry) for entry in story_arc)

    parity = cast(dict[str, list[str]], gallery["parity"])
    assert parity["floor"] == _FLOOR
    assert isinstance(parity["above_floor"], list)

    backends = cast(list[dict[str, object]], gallery["backends"])
    assert backends
    for entry in backends:
        assert {
            "id",
            "source_root",
            "source_entry",
            "source_hash",
            "render_status",
            "render_baseline",
            "capabilities",
            "degradations",
        } <= set(entry)

    preview = gallery["preview"]
    assert preview is None or set(cast(dict[str, str], preview)) == {
        "backend",
        "video_entry",
        "captions_entry",
        "manifest_entry",
    }


@pytest.mark.integration
@pytest.mark.parametrize("example", list(_EXAMPLES))
def test_example_parity_story_holds(example: str) -> None:
    """Above-floor primitives degrade on Manim and are native on the web backends."""
    parity = cast(dict[str, list[str]], _gallery(example)["parity"])
    manim_degradations = dict(_adapter("manim").capabilities.degradations)
    html_primitives = _adapter("html").capabilities.primitives
    remotion_primitives = _adapter("remotion").capabilities.primitives
    for primitive in parity["above_floor"]:
        assert primitive in manim_degradations, (example, primitive)
        assert primitive in html_primitives, (example, primitive)
        assert primitive in remotion_primitives, (example, primitive)


@pytest.mark.integration
@pytest.mark.parametrize(("example", "backend"), _example_backends())
def test_committed_hash_matches_fresh_deterministic_compile(
    example: str, backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each gallery backend compiles, twice, to its committed source.sha256 + gallery hash."""
    root = _EXAMPLES_DIR / example
    committed = (root / "expected" / backend / "source.sha256").read_text(
        encoding="utf-8"
    ).strip()
    backends = cast(list[dict[str, object]], _gallery(example)["backends"])
    gallery_hash = next(
        cast(str, entry["source_hash"]) for entry in backends if entry["id"] == backend
    )
    assert committed == gallery_hash

    digests: list[str] = []
    for _ in range(2):
        shutil.rmtree(root / "build", ignore_errors=True)
        assert main(["compile", str(root), "--backend", backend]) == 0
        out = capsys.readouterr().out
        line = next(line for line in out.splitlines() if line.startswith("source_hash: "))
        digests.append(line.removeprefix("source_hash: "))
    shutil.rmtree(root / "build", ignore_errors=True)
    assert digests[0] == digests[1] == committed

    adapter = _adapter(backend)
    entry = next(item for item in backends if item["id"] == backend)
    capabilities = cast(dict[str, list[str]], entry["capabilities"])
    assert capabilities["primitives"] == sorted(adapter.capabilities.primitives)
    assert capabilities["animations"] == sorted(adapter.capabilities.animations)
    assert entry["degradations"] == dict(adapter.capabilities.degradations)
