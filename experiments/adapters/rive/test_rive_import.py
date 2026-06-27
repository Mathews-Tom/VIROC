"""Byte-determinism + fidelity checks for the Rive Lottie-import remediation.

Outside the gated tree (`pyproject.toml` excludes `experiments/` from the default
pytest testpaths), so `uv run pytest -q` never collects this. Run it explicitly:

    uv run pytest experiments/adapters -q

The determinism and fidelity tests use only stdlib + the viroc package and always
run. The end-to-end editor-import test skips cleanly when no Rive import tool is
configured (the Rive editor is an external, render-side step) — exactly like the
optional-validator tests in the Lottie probe.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
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
_prepare = _load("rive_prepare", _HERE / "prepare.py")
_lottie = _load("lottie_export", _HERE.parent / "lottie" / "export.py")


def test_import_bundle_is_byte_deterministic() -> None:
    """The Rive-import preparation is a pure function of the Concrete IR (I1.3)."""
    ir = _sample.sample_concrete_ir()
    assert _prepare.prepare_import_bundle(ir) == _prepare.prepare_import_bundle(ir)
    assert _prepare.export_json(ir) == _prepare.export_json(ir)


def test_bundle_carries_the_gold_lottie_document() -> None:
    """Option A reuses the GO'd Lottie emit verbatim — no Rive-specific re-lowering."""
    ir = _sample.sample_concrete_ir()
    bundle = _prepare.prepare_import_bundle(ir)
    assert set(bundle) == {_prepare.BUNDLE_LOTTIE_NAME, _prepare.BUNDLE_MANIFEST_NAME}
    assert bundle[_prepare.BUNDLE_LOTTIE_NAME] == _lottie.export_json(ir)


def test_fidelity_matrix_marks_every_layer_baked() -> None:
    """Rive's importer bakes the vector graphics + timeline VIROC emits (I1.2)."""
    ir = _sample.sample_concrete_ir()
    matrix = _prepare.fidelity_matrix(ir)
    assert len(matrix) == len(ir.objects)
    # Every emitted Lottie construct survives import as baked keyframe data; VIROC
    # emits no Rive-only interactivity (bones/constraints), so nothing else is lost.
    assert all(outcome == "baked" for record in matrix for outcome in record["rive_import"])
    # The floor primitives carry their animated transform/shape properties through.
    by_object = {record["object"]: record["lottie_constructs"] for record in matrix}
    assert "opacity_anim" in by_object["title"]  # fade_in + fade_out
    assert "position_anim" in by_object["store_icon"]  # move
    assert "scale_anim" in by_object["model"]  # highlight pulse
    assert "trim_anim" in by_object["ingest_to_retriever"]  # draw


def test_manifest_records_upstream_degradations() -> None:
    """Above-floor losses happen in the Lottie emit, not at import; record them honestly."""
    ir = _sample.sample_concrete_ir()
    manifest = json.loads(_prepare.prepare_import_bundle(ir)[_prepare.BUNDLE_MANIFEST_NAME])
    degradations = manifest["upstream_degradations"]
    assert any('primitive "icon" degraded to the rect floor' in n for n in degradations)
    assert any('primitive "code" degraded to the rect floor' in n for n in degradations)
    assert any('primitive "formula" degraded to the rect floor' in n for n in degradations)
    assert manifest["import_is"].startswith("render-side")


def test_rive_editor_import_when_available(tmp_path: Path) -> None:
    """End-to-end I1.2: import the prepared Lottie with a real Rive tool if present.

    The Rive editor's Lottie import is an external, render-side, Enterprise-gated
    step with no public headless CLI, so this skips unless an importer is wired via
    ``$VIROC_RIVE_IMPORT_CLI`` (``<cli> <lottie-json> <out.riv>``). It is the
    executable hook for I1.2; absent a tool it records the honest skip.
    """
    cli = os.environ.get("VIROC_RIVE_IMPORT_CLI")
    if not cli or shutil.which(cli) is None:
        pytest.skip("no Rive import CLI configured (VIROC_RIVE_IMPORT_CLI); import is render-side/external")
    import subprocess  # noqa: PLC0415 - only needed on the rare configured path

    ir = _sample.sample_concrete_ir()
    lottie_path = tmp_path / _prepare.BUNDLE_LOTTIE_NAME
    lottie_path.write_text(_prepare.prepare_import_bundle(ir)[_prepare.BUNDLE_LOTTIE_NAME])
    out_riv = tmp_path / "viroc-sample.riv"
    subprocess.run([cli, str(lottie_path), str(out_riv)], check=True)  # noqa: S603
    assert out_riv.exists() and out_riv.stat().st_size > 0
