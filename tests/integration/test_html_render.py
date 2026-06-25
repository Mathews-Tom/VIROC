"""Env-gated HTML render integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import viroc.adapters.html as html_adapter
from viroc.core import BuildContext, BuildPaths, artifact_from_text
from viroc.ir import Caption

_ASSET_HASH = "sha256:" + "e" * 64
_SOURCE = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>VIROC Smoke</title>
<style>
html, body { margin: 0; background: #0B1020; }
#scene { position: relative; width: 320px; height: 180px; background: #0B1020; }
.box { position: absolute; left: 40px; top: 50px; width: 120px; height: 40px; border-radius: 12px; background: #0891B2; }
.caption { position: absolute; left: 32px; right: 32px; bottom: 24px; color: #E5E7EB; font: 600 20px/1.2 sans-serif; text-align: center; }
</style>
</head>
<body>
<div id=\"scene\" data-fps=\"15\" data-total-frames=\"3\">
  <div class=\"box\"></div>
  <div class=\"caption\">render smoke caption</div>
</div>
<script>
window.__viroc_frame_count = 3;
window.__viroc_setFrame = (frame) => {
  document.getElementById("scene").dataset.frame = String(frame);
  return frame;
};
window.__viroc_setFrame(0);
</script>
</body>
</html>
"""


def _ctx(tmp_path: Path) -> BuildContext:
    return BuildContext(
        paths=BuildPaths(project_root=tmp_path, out_dir=tmp_path / "dist"),
        config={"project": "html-render-smoke", "vidir_version": "0.1"},
        renderer={
            "asset_hashes": {"assets/doc.svg": _ASSET_HASH},
            "fps": 15,
            "output_name": "html-render-smoke",
            "sample_frames": 1,
            "timeout_seconds": 180,
        },
    )


@pytest.mark.integration
def test_env_gated_html_render_emits_video_srt_and_manifest(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    diagnostics = html_adapter.check_environment(ctx)
    if diagnostics:
        pytest.skip("browser/FFmpeg render toolchain is unavailable")

    source = artifact_from_text("source", _SOURCE)
    video = html_adapter.render(
        source,
        ctx,
        captions=[Caption(text="render smoke caption", start_f=0, end_f=3)],
    )

    srt_path = ctx.paths.out_dir / "captions.srt"
    manifest_path = ctx.paths.out_dir / "build.json"
    manifest = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))
    renderer = cast(dict[str, object], manifest["renderer"])
    phash = manifest["perceptual_hash"]

    assert isinstance(phash, str)
    assert video.path is not None
    assert video.path == ctx.paths.out_dir / "html-render-smoke.mp4"
    assert video.path.exists()
    assert srt_path.exists()
    assert manifest_path.exists()
    assert "render smoke caption" in srt_path.read_text(encoding="utf-8")
    assert manifest["project"] == "html-render-smoke"
    assert manifest["source_hash"] == source.digest
    assert manifest["asset_hashes"] == {"assets/doc.svg": _ASSET_HASH}
    assert renderer["id"] == "html"
    assert isinstance(renderer["version"], str)
    assert phash.startswith("phash:")
