"""Env-gated Motion Canvas render integration."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import cast

import pytest

import viroc.adapters.motion_canvas as motion_canvas
from viroc.core import BuildContext, BuildPaths, artifact_from_text, canonical_json
from viroc.ir import Caption

motion_canvas = importlib.reload(motion_canvas)

_ASSET_HASH = "sha256:" + "e" * 64
_PROJECT_TREE = {
    "package.json": canonical_json(
        {
            "name": "viroc-motion-canvas-smoke",
            "private": True,
            "type": "module",
            "scripts": {"dev": "vite", "build": "tsc && vite build"},
            "dependencies": {
                "@motion-canvas/2d": "^3.17.2",
                "@motion-canvas/core": "^3.17.2",
            },
            "devDependencies": {
                "@motion-canvas/ffmpeg": "^3.17.2",
                "@motion-canvas/ui": "^3.17.2",
                "@motion-canvas/vite-plugin": "^3.17.2",
                "typescript": "^5.2.2",
                "vite": "^5.4.0",
            },
        }
    )
    + "\n",
    "project.meta": canonical_json(
        {
            "version": 1,
            "shared": {
                "background": "rgb(11,16,32)",
                "range": [0, None],
                "size": {"x": 320, "y": 180},
            },
            "preview": {"fps": 15, "resolutionScale": 1},
            "rendering": {
                "colorSpace": "srgb",
                "fileType": "image/png",
                "fps": 15,
                "quality": 1,
                "resolutionScale": 1,
            },
        }
    )
    + "\n",
    "tsconfig.json": canonical_json(
        {"extends": "@motion-canvas/2d/tsconfig.project.json", "include": ["src"]}
    )
    + "\n",
    "vite.config.ts": (
        'import {defineConfig} from "vite";\n'
        'import motionCanvas from "@motion-canvas/vite-plugin";\n'
        'import ffmpeg from "@motion-canvas/ffmpeg";\n\n'
        'export default defineConfig({\n'
        '  plugins: [motionCanvas(), ffmpeg()],\n'
        '});\n'
    ),
    "src/motion-canvas.d.ts": '/// <reference types="@motion-canvas/core/project" />\n',
    "src/project.ts": (
        'import {makeProject} from "@motion-canvas/core";\n\n'
        'import viroc from "./scenes/viroc?scene";\n\n'
        'export default makeProject({\n'
        '  scenes: [viroc],\n'
        '});\n'
    ),
    "src/scenes/viroc.tsx": (
        'import {Circle, makeScene2D} from "@motion-canvas/2d";\n'
        'import {createRef} from "@motion-canvas/core";\n\n'
        'export default makeScene2D(function* (view) {\n'
        '  const circle = createRef<Circle>();\n'
        '  view.fill("#0B1020");\n'
        '  view.add(<Circle ref={circle} size={180} fill={"#38BDF8"} opacity={0} />);\n'
        '  yield* circle().opacity(1, 0.3);\n'
        '  yield* circle().scale(1.2, 0.3).to(1, 0.3);\n'
        '});\n'
    ),
}
_SOURCE = f"{canonical_json(_PROJECT_TREE)}\n"


def _ctx(tmp_path: Path) -> BuildContext:
    return BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "dist"),
        config={"project": "render-smoke", "vidir_version": "0.1"},
        renderer={
            "asset_hashes": {"assets/doc.svg": _ASSET_HASH},
            "fps": 15,
            "output_name": "render-smoke",
            "sample_frames": 1,
            "timeout_seconds": 180,
        },
    )


@pytest.mark.integration
def test_env_gated_motion_canvas_render_emits_video_srt_and_manifest(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    diagnostics = motion_canvas.check_environment(ctx)
    if diagnostics:
        pytest.skip("Node/Motion Canvas/FFmpeg render toolchain is unavailable")

    source = artifact_from_text("source", _SOURCE)
    video = motion_canvas.render(
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


def test_motion_canvas_captions_to_srt_rejects_non_positive_fps() -> None:
    with pytest.raises(ValueError, match="renderer.fps must be positive"):
        motion_canvas.captions_to_srt([Caption(text="bad", start_f=0, end_f=1)], 0)
