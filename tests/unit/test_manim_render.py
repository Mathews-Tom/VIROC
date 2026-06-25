"""Unit coverage for renderer-independent Manim render helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import viroc.adapters.manim as manim
from viroc.core import BuildContext, BuildPaths, artifact_from_text
from viroc.ir import Caption


def _ctx(*, renderer: dict[str, object] | None = None) -> BuildContext:
    root = Path("/tmp/viroc-manim-render-test")
    return BuildContext(
        paths=BuildPaths(project_root=root, out_dir=root / "dist"),
        renderer=renderer if renderer is not None else {},
    )


def _missing_tool(command: str) -> None:
    _ = command
    return None


def test_captions_to_srt_formats_and_sorts_captions() -> None:
    captions = [
        Caption(text="second", start_f=30, end_f=60),
        Caption(text="first", start_f=0, end_f=15),
        Caption(text="after one hour", start_f=108_000, end_f=108_030),
    ]

    assert manim.captions_to_srt(captions, 30) == "\n".join(
        [
            "1",
            "00:00:00,000 --> 00:00:00,500",
            "first",
            "",
            "2",
            "00:00:01,000 --> 00:00:02,000",
            "second",
            "",
            "3",
            "01:00:00,000 --> 01:00:01,000",
            "after one hour",
            "",
        ]
    )


def test_captions_to_srt_handles_empty_captions() -> None:
    assert manim.captions_to_srt([], 30) == ""


def test_captions_to_srt_rejects_invalid_timing() -> None:
    with pytest.raises(ValueError, match="fps must be positive"):
        manim.captions_to_srt([], 0)

    with pytest.raises(ValueError, match="precedes start frame"):
        manim.captions_to_srt([Caption(text="bad", start_f=10, end_f=9)], 30)


def test_check_environment_help_uses_config_key_for_overridden_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", _missing_tool)

    diagnostics = manim.check_environment(_ctx(renderer={"manim_executable": "/opt/mymanim"}))

    assert diagnostics[0].help == "install Manim or set renderer.manim_executable to its path"


def test_render_requires_fps_when_captions_are_present(tmp_path: Path) -> None:
    ctx = BuildContext(paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "dist"))

    with pytest.raises(ValueError, match="renderer.fps is required"):
        manim.render(
            artifact_from_text("source", "from manim import Scene\n"),
            ctx,
            captions=[Caption(text="caption", start_f=0, end_f=15)],
        )
