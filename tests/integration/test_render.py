"""Env-gated Manim render integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import viroc.adapters.manim as manim
from viroc.core import BuildContext, BuildPaths, artifact_from_text
from viroc.ir import Caption

_ASSET_HASH = "sha256:" + "d" * 64
_SOURCE = """from manim import Scene, config

config.pixel_width = 320
config.pixel_height = 180
config.frame_rate = 15

class VirocScene(Scene):
    def construct(self) -> None:
        self.wait(0.2)
"""


def _ctx(tmp_path: Path) -> BuildContext:
    return BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "dist"),
        config={"project": "render-smoke", "vidir_version": "0.1"},
        renderer={
            "asset_hashes": {"assets/doc.svg": _ASSET_HASH},
            "fps": 15,
            "output_name": "render-smoke",
            "quality": "-ql",
            "sample_frames": 1,
            "seed": 0,
            "timeout_seconds": 180,
        },
    )


@pytest.mark.integration
def test_env_gated_manim_render_emits_video_srt_and_manifest(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    diagnostics = manim.check_environment(ctx)
    if diagnostics:
        pytest.skip("Manim/FFmpeg render toolchain is unavailable")

    source = artifact_from_text("source", _SOURCE)
    video = manim.render(
        source,
        ctx,
        captions=[Caption(text="render smoke caption", start_f=0, end_f=3)],
    )

    srt_path = ctx.paths.out_dir / "captions.srt"
    manifest_path = ctx.paths.out_dir / "build.json"
    manifest = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))

    phash = manifest["perceptual_hash"]

    assert isinstance(phash, str)
    assert video.path is not None
    assert video.path == ctx.paths.out_dir / "render-smoke.mp4"
    assert video.path.exists()
    assert srt_path.exists()
    assert manifest_path.exists()
    assert "render smoke caption" in srt_path.read_text(encoding="utf-8")
    assert manifest["project"] == "render-smoke"
    assert manifest["source_hash"] == source.digest
    assert manifest["asset_hashes"] == {"assets/doc.svg": _ASSET_HASH}
    assert phash.startswith("phash:")
