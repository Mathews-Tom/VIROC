"""Env-gated Remotion render integration."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import viroc.adapters.remotion as remotion
from viroc.core import BuildContext, BuildPaths, artifact_from_text, canonical_json
from viroc.ir import Caption

_ASSET_HASH = "sha256:" + "d" * 64
_PROJECT_TREE = {
    "package.json": "{\"private\":true}\n",
    "tsconfig.json": "{\"compilerOptions\":{\"jsx\":\"react-jsx\"}}\n",
    "src/index.ts": (
        'import {registerRoot} from "remotion";\n'
        'import {RemotionRoot} from "./Root";\n\n'
        "registerRoot(RemotionRoot);\n"
    ),
    "src/Root.tsx": (
        'import React from "react";\n'
        'import {Composition} from "remotion";\n'
        'import {VirocScene} from "./Composition";\n\n'
        'export const RemotionRoot: React.FC = () => (\n'
        '  <Composition id="VirocScene" component={VirocScene} durationInFrames={6} fps={15} width={320} height={180} defaultProps={{}} />\n'
        ');\n'
    ),
    "src/Composition.tsx": (
        'import React from "react";\n'
        'import {AbsoluteFill, useCurrentFrame} from "remotion";\n\n'
        'export const VirocScene: React.FC = () => {\n'
        '  const frame = useCurrentFrame();\n'
        '  return (\n'
        '    <AbsoluteFill style={{backgroundColor: "#0B1020", color: "#E5E7EB", fontFamily: "Inter, sans-serif", alignItems: "center", justifyContent: "center"}}>\n'
        '      <div style={{width: 180, height: 72, borderRadius: 16, border: "2px solid #60A5FA", background: "#1D4ED8", display: "grid", placeItems: "center", opacity: frame < 2 ? 0.4 : 1}}>Render smoke {frame}</div>\n'
        '    </AbsoluteFill>\n'
        '  );\n'
        '};\n'
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
def test_env_gated_remotion_render_emits_video_srt_and_manifest(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    diagnostics = remotion.check_environment(ctx)
    if diagnostics:
        pytest.skip("Node/Remotion/FFmpeg render toolchain is unavailable")

    source = artifact_from_text("source", _SOURCE)
    video = remotion.render(
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
