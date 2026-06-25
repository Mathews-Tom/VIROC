"""Compiler pipeline P3+P4 wiring (M5).

The driver runs normalize (P3) then asset resolution (P4). These tests assert
both phases execute and their outputs and diagnostics land on the returned
state; layout/timeline/Concrete-IR assembly (P5+) is out of scope here.
"""

from __future__ import annotations

from pathlib import Path

from viroc.compiler.assets import VIR_ASSET_MISSING
from viroc.compiler.normalize import normalize
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths
from viroc.ir import SemanticIR

_RAW_IR: dict[str, object] = {
    "vidir_version": "0.1",
    "video": {"id": "RAG Overview", "title": "How RAG Works"},
    "entities": [
        {"id": "Doc Source", "label": "Documents", "type": "data_source"},
        {"id": "Vector DB", "label": "Vector DB", "type": "storage"},
    ],
    "scenes": [
        {
            "id": "Main Scene",
            "grammar": "pipeline",
            "duration": "35s",
            "nodes": ["Doc Source", "Vector DB"],
            "edges": [{"from": "Doc Source", "to": "Vector DB", "kind": "store"}],
        }
    ],
}


def _ir() -> SemanticIR:
    return SemanticIR.model_validate(_RAW_IR)


def _ctx(root: Path) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def test_run_pipeline_normalizes_the_ir(tmp_path: Path) -> None:
    """P3 runs: the state carries the canonical, normalized Semantic IR."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    assert isinstance(state, CompileState)
    assert state.ir == normalize(_ir())
    assert state.ir.video.id == "rag_overview"
    # P3 output is already canonical: re-normalizing is a no-op.
    assert normalize(state.ir) == state.ir


def test_run_pipeline_resolves_present_assets(tmp_path: Path) -> None:
    """P4 runs: a present asset is resolved and hashed, with no diagnostics."""
    (tmp_path / "logo.png").write_bytes(b"bytes")
    state = run_pipeline(_ir(), _ctx(tmp_path), asset_refs=["logo.png"])
    assert [asset.ref for asset in state.assets] == ["logo.png"]
    assert state.assets[0].digest.startswith("sha256:")
    assert state.diagnostics == []


def test_run_pipeline_propagates_asset_diagnostics(tmp_path: Path) -> None:
    """A missing asset surfaces as a VIR4001 diagnostic on the state."""
    state = run_pipeline(_ir(), _ctx(tmp_path), asset_refs=["gone.png"])
    assert state.assets == []
    assert [diag.code for diag in state.diagnostics] == [VIR_ASSET_MISSING]


def test_run_pipeline_defaults_to_no_assets(tmp_path: Path) -> None:
    """With no asset references the asset phase is a clean no-op."""
    state = run_pipeline(_ir(), _ctx(tmp_path))
    assert state.assets == []
    assert state.diagnostics == []
