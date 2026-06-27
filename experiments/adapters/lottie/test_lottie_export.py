"""Byte-determinism + capability-map regression for the Lottie export probe.

Outside the gated tree (`pyproject.toml` excludes `experiments/` from the default
pytest testpaths), so `uv run pytest -q` never collects this. Run it explicitly:

    uv run pytest experiments/adapters -q

The determinism and capability tests use only stdlib + the viroc package and
always run. The optional validation test skips cleanly when `python-lottie` is
not installed — no probe requires an external tool to prove byte-determinism.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sample = _load("adapters_sample", _HERE.parent / "_sample.py")
_export = _load("lottie_export", _HERE / "export.py")


def test_export_is_byte_deterministic() -> None:
    """The lowering is a pure function of the Concrete IR (ADR-0002 emit boundary)."""
    ir = _sample.sample_concrete_ir()
    assert _export.export_json(ir) == _export.export_json(ir)


def test_export_is_valid_json_with_one_layer_per_object() -> None:
    ir = _sample.sample_concrete_ir()
    document = json.loads(_export.export_json(ir))
    assert document["fr"] == ir.fps
    assert document["w"], document["h"] == ir.resolution
    assert len(document["layers"]) == len(ir.objects)
    # Every floor primitive lowers to a shape (ty=4) or text (ty=5) layer.
    assert {layer["ty"] for layer in document["layers"]} <= {4, 5}


def test_capability_map_is_locked() -> None:
    """Above-floor primitives + non-floor motions degrade explicitly, never silently."""
    ir = _sample.sample_concrete_ir()
    notes = _export.degradations(ir)
    assert any('primitive "icon" degraded to the rect floor' in n for n in notes)
    assert any('primitive "code" degraded to the rect floor' in n for n in notes)
    assert any('primitive "formula" degraded to the rect floor' in n for n in notes)
    assert any('keyframe "highlight" degraded to a scale pulse' in n for n in notes)
    assert any('easing "spring" degraded to "ease_in_out"' in n for n in notes)
    assert any("caption" in n and "SRT sidecar" in n for n in notes)


def test_optional_python_lottie_accepts_the_document() -> None:
    """If python-lottie is installed, the emitted document parses; else skip cleanly."""
    lottie_objects = pytest.importorskip("lottie.objects")
    ir = _sample.sample_concrete_ir()
    document = json.loads(_export.export_json(ir))
    animation = lottie_objects.Animation.load(document)
    assert animation.frame_rate == ir.fps
