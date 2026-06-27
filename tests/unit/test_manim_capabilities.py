"""Manim adapter capability negotiation (M9, PR-3)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import viroc.adapters.manim as manim
from viroc.adapters import RendererAdapter
from viroc.core import BuildContext, BuildPaths, Severity
from viroc.ir import ConcreteIR, Keyframe, ResolvedObject


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-manim-capabilities-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _ir(
    *, objects: list[ResolvedObject] | None = None, keyframes: list[Keyframe] | None = None
) -> ConcreteIR:
    return ConcreteIR(
        fps=30,
        resolution=(1920, 1080),
        objects=objects if objects is not None else [],
        keyframes=keyframes if keyframes is not None else [],
        captions=[],
    )


def _object(**overrides: object) -> ResolvedObject:
    fields: dict[str, object] = {
        "id": "demo.panel",
        "primitive": "rect",
        "box": {"x": 0.0, "y": 0.0, "w": 100.0, "h": 50.0},
        "style_ref": "node.process",
    }
    fields.update(overrides)
    return ResolvedObject.model_validate(fields)


def _missing_tool(command: str) -> None:
    _ = command
    return None


def test_manim_module_satisfies_renderer_adapter_protocol() -> None:
    assert isinstance(manim, RendererAdapter)
    assert manim.id == "manim"
    assert "rect" in manim.capabilities.primitives


def test_manim_check_environment_reports_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", _missing_tool)

    diagnostics = manim.check_environment(_ctx())

    assert [diag.code for diag in diagnostics] == [
        manim.VIR_MISSING_MANIM,
        manim.VIR_MISSING_FFMPEG,
        manim.VIR_MISSING_FFPROBE,
    ]


def test_supported_rag_primitives_emit_no_diagnostics() -> None:
    diagnostics = manim.supports(
        _ir(
            objects=[
                _object(primitive="rect"),
                _object(id="demo.label", primitive="text", style_ref="label"),
                _object(id="demo.arrow", primitive="arrow", style_ref="edge.default"),
            ]
        )
    )

    assert diagnostics == []


def test_unsupported_primitive_is_vir5031_with_help() -> None:
    diagnostics = manim.supports(_ir(objects=[_object(primitive="icon")]))

    assert [diag.code for diag in diagnostics] == [manim.VIR_UNSUPPORTED_PRIMITIVE]
    assert diagnostics[0].code == "VIR5031"
    assert diagnostics[0].message == 'renderer "manim" does not support primitive "icon"'
    assert diagnostics[0].help == (
        'use renderer "html", or provide a fallback image asset for object "demo.panel"'
    )


def test_degraded_primitive_is_vir5033_note() -> None:
    diagnostics = manim.supports(
        _ir(
            objects=[
                _object(
                    id="scene.semantic_ir.code_card",
                    primitive="code",
                    style_ref="code_card.intermediate",
                ),
                _object(
                    id="scene.hashes.evidence",
                    primitive="formula",
                    style_ref="evidence.storage",
                ),
            ]
        )
    )

    assert [diag.code for diag in diagnostics] == [
        manim.VIR_DEGRADED_PRIMITIVE,
        manim.VIR_DEGRADED_PRIMITIVE,
    ]
    assert all(diag.severity is Severity.NOTE for diag in diagnostics)
    assert diagnostics[0].message == (
        'renderer "manim" renders primitive "code" as "rect" (deterministic degradation)'
    )
    assert diagnostics[1].message == (
        'renderer "manim" renders primitive "formula" as "rect" (deterministic degradation)'
    )


def test_unsupported_animation_is_renderer_diagnostic() -> None:
    diagnostics = manim.supports(
        _ir(
            keyframes=[
                Keyframe(
                    object_id="demo.panel",
                    kind="move",
                    start_f=0,
                    end_f=30,
                    easing="linear",
                )
            ]
        )
    )

    assert [diag.code for diag in diagnostics] == [manim.VIR_UNSUPPORTED_ANIMATION]
    assert diagnostics[0].code.startswith("VIR5")
