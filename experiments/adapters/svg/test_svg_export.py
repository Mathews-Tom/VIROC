"""Byte-determinism, well-formedness, and capability checks for the SVG export probe.

Outside the gated tree (`pyproject.toml` excludes `experiments/` from the default
pytest testpaths); `uv run pytest -q` never collects this. Run it explicitly:

    uv run pytest experiments/adapters -q

The determinism, well-formedness, and capability tests use only stdlib + the viroc
package and always run. The optional rasterizer test skips cleanly when neither
`cairosvg` nor the `resvg` CLI is available — rasterization is render-side and never
a core dependency.
"""

from __future__ import annotations

import importlib.util
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType

import pytest

_HERE = Path(__file__).resolve().parent
_SVG_NS = "http://www.w3.org/2000/svg"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sample = _load("adapters_sample", _HERE.parent / "_sample.py")
_export = _load("svg_export", _HERE / "export.py")
_rasterize = _load("svg_rasterize", _HERE / "rasterize.py")


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def test_export_is_byte_deterministic() -> None:
    """The lowering is a pure function of the Concrete IR (ADR-0002 emit boundary)."""
    ir = _sample.sample_concrete_ir()
    assert _export.export_svg(ir) == _export.export_svg(ir)
    assert _export.source_hash(ir) == _export.source_hash(ir)
    assert _export.source_hash(ir).startswith("sha256:")


def test_export_is_wellformed_standalone_svg() -> None:
    """A single parseable SVG file (no HTML/JS), sized to the resolution."""
    ir = _sample.sample_concrete_ir()
    svg = _export.export_svg(ir)
    assert "<script" not in svg and "<foreignObject" not in svg  # standalone, headless-rasterizable
    root = ET.fromstring(svg)
    assert _localname(root.tag) == "svg"
    width, height = ir.resolution
    assert root.get("viewBox") == f"0 0 {width} {height}"


def test_one_drawable_group_per_object() -> None:
    ir = _sample.sample_concrete_ir()
    root = ET.fromstring(_export.export_svg(ir))
    groups = [el for el in root.iter(f"{{{_SVG_NS}}}g")]
    assert len(groups) == len(ir.objects)


def test_every_keyframe_lowers_to_one_animation_element() -> None:
    """Each keyframe becomes exactly one SMIL animation (native motion coverage)."""
    ir = _sample.sample_concrete_ir()
    root = ET.fromstring(_export.export_svg(ir))
    animations = [el for el in root.iter() if _localname(el.tag) in {"animate", "animateTransform"}]
    assert len(animations) == len(ir.keyframes)


def test_floor_native_above_floor_degraded() -> None:
    """Floor primitives are native; icon/code/formula degrade to the rect floor."""
    ir = _sample.sample_concrete_ir()
    notes = _export.degradations(ir)
    assert any('primitive "icon" degraded to the rect floor' in n for n in notes)
    assert any('primitive "code" degraded to the rect floor' in n for n in notes)
    assert any('primitive "formula" degraded to the rect floor' in n for n in notes)
    assert any('easing "spring" degraded to "ease_in_out"' in n for n in notes)
    assert any("caption" in n and "SRT sidecar" in n for n in notes)


def test_optional_rasterizer_produces_a_png(tmp_path: Path) -> None:
    """If a rasterizer is installed, the SVG renders to a non-empty PNG; else skip."""
    if importlib.util.find_spec("cairosvg") is None and shutil.which("resvg") is None:
        pytest.skip("no SVG rasterizer (cairosvg / resvg); rasterization is render-side/optional")
    ir = _sample.sample_concrete_ir()
    out = _rasterize.rasterize_png(_export.export_svg(ir), tmp_path / "frame.png")
    assert out.exists() and out.stat().st_size > 0
