"""Byte-determinism + capability checks for the interactive web export probe.

Outside the gated tree; `uv run pytest -q` never collects this. Run explicitly:

    uv run pytest experiments/adapters -q

Uses only stdlib + the viroc package and always runs (the bundle is vanilla
JS/SVG, so there is no external tool to gate on).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sample = _load("adapters_sample", _HERE.parent / "_sample.py")
_export = _load("interactive_web_export", _HERE / "export.py")


def test_bundle_is_byte_deterministic() -> None:
    """The whole bundle is a pure function of the Concrete IR (ADR-0002 boundary)."""
    ir = _sample.sample_concrete_ir()
    assert _export.export_bundle(ir) == _export.export_bundle(ir)
    assert _export.export_json(ir) == _export.export_json(ir)


def test_bundle_is_source_only() -> None:
    """Bundle is emit-side source: a viewer + a timeline, no rendered pixels."""
    ir = _sample.sample_concrete_ir()
    bundle = _export.export_bundle(ir)
    assert set(bundle) == {"index.html", "timeline.json"}
    assert bundle["index.html"].startswith("<!doctype html>")
    assert "<svg" in bundle["index.html"] and "requestAnimationFrame" in bundle["index.html"]


def test_timeline_covers_every_object_and_keyframe() -> None:
    ir = _sample.sample_concrete_ir()
    timeline = json.loads(_export.export_bundle(ir)["timeline.json"])
    assert timeline["fps"] == ir.fps
    assert timeline["duration_f"] == _export.total_frames(ir)
    assert len(timeline["objects"]) == len(ir.objects)
    emitted_segments = sum(len(o["segments"]) for o in timeline["objects"])
    assert emitted_segments == len(ir.keyframes)


def test_every_keyframe_kind_is_native() -> None:
    """Interactive web interpolates the full keyframe vocabulary in vanilla JS."""
    ir = _sample.sample_concrete_ir()
    assert _export.unsupported_keyframes(ir) == set()


def test_above_floor_primitives_degrade_explicitly() -> None:
    ir = _sample.sample_concrete_ir()
    notes = _export.degradations(ir)
    assert any('primitive "formula"' in n for n in notes)
    assert any('primitive "icon"' in n for n in notes)
