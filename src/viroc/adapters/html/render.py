"""Impure HTML render path: browser frame capture, FFmpeg muxing, and probes."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

from viroc.compiler.postvalidate import (
    perceptual_hash_frames,
    probe_duration_seconds,
    sample_video_frames,
)
from viroc.core import (
    BuildArtifact,
    BuildContext,
    Diagnostic,
    DiagnosticClass,
    artifact_from_path,
    build_manifest,
    code,
    write_manifest,
)
from viroc.ir import Caption

VIR_MISSING_BROWSER = code(DiagnosticClass.RENDERER, 45)
VIR_MISSING_NODE = code(DiagnosticClass.RENDERER, 46)
VIR_TOOL_PROBE_FAILED = code(DiagnosticClass.RENDERER, 47)
VIR_MISSING_FFMPEG = code(DiagnosticClass.RENDERER, 48)
VIR_MISSING_FFPROBE = code(DiagnosticClass.RENDERER, 49)

_DEFAULT_OUTPUT_NAME = "viroc"
_DEFAULT_TIMEOUT_SECONDS = 180
_DEFAULT_BROWSER_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
)
_NODE_SCRIPT = r"""
const { spawn } = await import("node:child_process");
const { mkdtemp, mkdir, readFile, rm, writeFile } = await import("node:fs/promises");
const { tmpdir } = await import("node:os");
const { join } = await import("node:path");

const [browser, sourcePath, framesDir, metadataPath] = process.argv.slice(2);
const sourceUrl = new URL(`file://${sourcePath}`).toString();
const profileRoot = await mkdtemp(join(tmpdir(), "viroc-html-render-"));
const userDataDir = join(profileRoot, "profile");
await mkdir(userDataDir, { recursive: true });
const browserArgs = [
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--mute-audio",
  "--force-device-scale-factor=1",
  "--remote-debugging-port=0",
  `--user-data-dir=${userDataDir}`,
  "about:blank",
];
const child = spawn(browser, browserArgs, { stdio: ["ignore", "pipe", "pipe"] });
let stderr = "";
let socket;
child.stderr.on("data", chunk => {
  stderr += chunk.toString();
});
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
try {
  const activePortPath = join(userDataDir, "DevToolsActivePort");
  let port = "";
  for (let attempt = 0; attempt < 200; attempt += 1) {
    try {
      const text = await readFile(activePortPath, "utf8");
      port = text.split("\n")[0]?.trim() ?? "";
      if (port) break;
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
    if (child.exitCode !== null) {
      break;
    }
    await sleep(50);
  }
  if (!port) {
    throw new Error(stderr.trim() || "Chrome DevTools port did not appear");
  }
  let page;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(
      response => response.json()
    );
    page = targets.find(target => target.type === "page");
    if (page) break;
    await sleep(50);
  }
  if (!page) {
    throw new Error("Chrome DevTools did not expose a page target");
  }
  socket = new WebSocket(page.webSocketDebuggerUrl);
  const pending = new Map();
  let nextId = 1;
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const entry = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        entry.reject(new Error(JSON.stringify(message.error)));
      } else {
        entry.resolve(message.result);
      }
    }
  };
  await new Promise((resolve, reject) => {
    socket.onopen = () => resolve(undefined);
    socket.onerror = event => reject(new Error(String(event.message || event.type)));
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = nextId;
      nextId += 1;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  const evaluate = async expression => {
    const result = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    return result.result.value;
  };
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url: `${sourceUrl}?frame=0` });
  await sleep(150);
  const metadata = await evaluate(`(() => {
    const scene = document.getElementById("scene");
    if (!scene) throw new Error("missing #scene root");
    const fps = Number(scene.dataset.fps || "0");
    const totalFrames = Number(window.__viroc_frame_count || scene.dataset.totalFrames || "0");
    return { width: scene.clientWidth, height: scene.clientHeight, fps, totalFrames };
  })()`);
  if (!metadata || !metadata.width || !metadata.height || !metadata.fps) {
    throw new Error(`invalid scene metadata: ${JSON.stringify(metadata)}`);
  }
  await send("Emulation.setDeviceMetricsOverride", {
    width: metadata.width,
    height: metadata.height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await send("Page.navigate", { url: `${sourceUrl}?frame=0` });
  await sleep(150);
  await mkdir(framesDir, { recursive: true });
  for (let frame = 0; frame < metadata.totalFrames; frame += 1) {
    await evaluate(`window.__viroc_setFrame(${frame})`);
    const shot = await send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
    });
    const framePath = join(framesDir, `${String(frame).padStart(6, "0")}.png`);
    await writeFile(framePath, Buffer.from(shot.data, "base64"));
  }
  await writeFile(metadataPath, JSON.stringify(metadata));
} finally {
  try {
    socket?.close();
  } catch {}
  if (child.exitCode === null) {
    child.kill("SIGKILL");
  }
  await rm(profileRoot, { recursive: true, force: true });
}
"""


class RenderEnvironmentError(RuntimeError):
    """Raised when required render tools are missing or unusable."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("html render environment is unavailable")
        self.diagnostics = diagnostics


class RenderCommandError(RuntimeError):
    """Raised when the browser automation or FFmpeg exits unsuccessfully."""

    def __init__(self, command: list[str], stderr: str) -> None:
        super().__init__("render command failed")
        self.command = command
        self.stderr = stderr


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """Return diagnostics for missing or unusable impure render dependencies."""
    diagnostics: list[Diagnostic] = []
    try:
        browser = _browser_command(ctx)
    except ValueError as exc:
        return [
            Diagnostic(
                code=VIR_MISSING_BROWSER,
                message="invalid renderer.browser_executable configuration",
                help=str(exc),
            )
        ]
    if browser is None:
        diagnostics.append(
            Diagnostic(
                code=VIR_MISSING_BROWSER,
                message="browser executable not found",
                help=(
                    "install Chrome/Chromium or set renderer.browser_executable to an absolute path"
                ),
            )
        )
    else:
        diagnostics.extend(
            _probe_tool(browser, ["--version"], missing_code=VIR_MISSING_BROWSER, label="browser")
        )
    diagnostics.extend(
        _probe_tool(
            _renderer_str(ctx, "node_executable", "node"),
            ["--version"],
            missing_code=VIR_MISSING_NODE,
            label="node",
        )
    )
    diagnostics.extend(
        _probe_tool(
            _renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
            ["-version"],
            missing_code=VIR_MISSING_FFMPEG,
            label="ffmpeg",
        )
    )
    diagnostics.extend(
        _probe_tool(
            _renderer_str(ctx, "ffprobe_executable", "ffprobe"),
            ["-version"],
            missing_code=VIR_MISSING_FFPROBE,
            label="ffprobe",
        )
    )
    return diagnostics


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: list[Caption] | tuple[Caption, ...] = (),
) -> BuildArtifact:
    """Render emitted HTML through a headless browser and FFmpeg."""
    caption_list = list(captions)
    diagnostics = check_environment(ctx)
    if diagnostics:
        raise RenderEnvironmentError(diagnostics)

    out_dir = ctx.paths.out_dir
    render_dir = out_dir / "render"
    frames_dir = render_dir / "frames"
    render_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    source_path = _materialize_source(source, render_dir / "scene.html")
    metadata_path = render_dir / "metadata.json"
    node_script = render_dir / "capture_frames.mjs"
    node_script.write_text(_NODE_SCRIPT, encoding="utf-8")

    browser = _require_browser(ctx)
    node = _renderer_str(ctx, "node_executable", "node")
    command = [
        node,
        str(node_script),
        browser,
        str(source_path),
        str(frames_dir),
        str(metadata_path),
    ]
    completed = _run_command(
        command,
        timeout=_renderer_int(ctx, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
    )
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)

    metadata = cast(dict[str, Any], json.loads(metadata_path.read_text(encoding="utf-8")))
    fps = _metadata_int(metadata, "fps")
    total_frames = _metadata_int(metadata, "totalFrames")
    if total_frames <= 0:
        raise ValueError("HTML renderer reported zero frames")

    raw_video = out_dir / f"{_renderer_str(ctx, 'output_name', _DEFAULT_OUTPUT_NAME)}-raw.mp4"
    final_path = out_dir / f"{_renderer_str(ctx, 'output_name', _DEFAULT_OUTPUT_NAME)}.mp4"
    _encode_frames(frames_dir, raw_video, fps, ctx)

    srt_text = captions_to_srt(caption_list, fps)
    srt_path = out_dir / "captions.srt"
    srt_path.write_text(srt_text, encoding="utf-8")
    if srt_text:
        _mux_srt(raw_video, srt_path, final_path, ctx)
    else:
        shutil.copy2(raw_video, final_path)

    artifact = artifact_from_path("video", final_path)
    _write_build_manifest(source, final_path, ctx)
    return artifact


def browser_version(ctx: BuildContext) -> str:
    """Return the installed browser version string reported by the executable."""
    command = [_require_browser(ctx), "--version"]
    completed = _run_command(command, timeout=10)
    output = completed.stdout.strip()
    return output if output else "unknown"


def captions_to_srt(captions: list[Caption], fps: int) -> str:
    """Lower resolved frame captions to deterministic SRT text."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    lines: list[str] = []
    ordered = sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))
    for index, caption in enumerate(ordered, start=1):
        if caption.end_f < caption.start_f:
            raise ValueError(
                f"caption end_f must be >= start_f, got {caption.start_f}>{caption.end_f}"
            )
        lines.extend(
            [
                str(index),
                f"{_srt_timestamp(caption.start_f, fps)} --> {_srt_timestamp(caption.end_f, fps)}",
                caption.text,
                "",
            ]
        )
    return "\n".join(lines)


def _encode_frames(frames_dir: Path, output_path: Path, fps: int, ctx: BuildContext) -> None:
    command = [
        _renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "%06d.png"),
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    completed = _run_command(
        command,
        timeout=_renderer_int(ctx, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
    )
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)


def _mux_srt(raw_video: Path, srt_path: Path, final_path: Path, ctx: BuildContext) -> None:
    command = [
        _renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw_video),
        "-i",
        str(srt_path),
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "mov_text",
        str(final_path),
    ]
    completed = _run_command(
        command,
        timeout=_renderer_int(ctx, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS),
    )
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)


def _write_build_manifest(source: BuildArtifact, video_path: Path, ctx: BuildContext) -> None:
    frames = sample_video_frames(
        video_path,
        sample_count=_renderer_int(ctx, "sample_frames", 4),
        ffmpeg=_renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
        ffprobe=_renderer_str(ctx, "ffprobe_executable", "ffprobe"),
    )
    manifest = build_manifest(
        project=_config_str(ctx, "project", ctx.paths.project_root.name),
        source_hash=source.digest,
        asset_hashes=_asset_hashes(ctx),
        renderer_id="html",
        renderer_version=browser_version(ctx),
        perceptual_hash=perceptual_hash_frames(frames),
        duration_seconds=probe_duration_seconds(
            video_path,
            ffprobe=_renderer_str(ctx, "ffprobe_executable", "ffprobe"),
        ),
        vidir_version=_config_str(ctx, "vidir_version", "0.1"),
    )
    write_manifest(manifest, ctx.paths.out_dir / "build.json")


def _probe_tool(
    command: str,
    args: list[str],
    *,
    missing_code: str,
    label: str,
) -> list[Diagnostic]:
    resolved = _resolve_executable(command)
    if resolved is None:
        return [
            Diagnostic(
                code=missing_code,
                message=f"{label} executable not found",
                help=f"install {label} or set renderer.{label}_executable to its path",
            )
        ]
    completed = _run_command([resolved, *args], timeout=10)
    if completed.returncode != 0:
        return [
            Diagnostic(
                code=VIR_TOOL_PROBE_FAILED,
                message=f"{label} probe failed",
                help=completed.stderr.strip() or completed.stdout.strip() or None,
            )
        ]
    return []


def _materialize_source(source: BuildArtifact, destination: Path) -> Path:
    if source.data is not None:
        destination.write_bytes(source.data)
        return destination
    if source.path is not None:
        destination.write_bytes(source.path.read_bytes())
        return destination
    raise ValueError("source artifact did not carry bytes or a path")


def _run_command(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _browser_command(ctx: BuildContext) -> str | None:
    if "browser_executable" in ctx.renderer:
        configured = ctx.renderer["browser_executable"]
        if not isinstance(configured, str) or not configured.strip():
            raise ValueError("renderer.browser_executable must be a non-empty string")
        return _resolve_executable(configured)
    for candidate in _DEFAULT_BROWSER_CANDIDATES:
        resolved = _resolve_executable(candidate)
        if resolved is not None:
            return resolved
    return None


def _require_browser(ctx: BuildContext) -> str:
    browser = _browser_command(ctx)
    if browser is None:
        raise ValueError("browser executable not configured")
    return browser


def _resolve_executable(command: str) -> str | None:
    path = Path(command)
    if path.is_absolute():
        return command if path.exists() else None
    resolved = shutil.which(command)
    return resolved if resolved else None


def _renderer_str(ctx: BuildContext, key: str, default: str) -> str:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"renderer.{key} must be a string")
    return value


def _renderer_int(ctx: BuildContext, key: str, default: int) -> int:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"renderer.{key} must be an integer")
    return value


def _metadata_int(metadata: dict[str, Any], key: str) -> int:
    value = metadata.get(key)
    if not isinstance(value, int):
        raise ValueError(f"render metadata {key!r} must be an integer")
    return value


def _asset_hashes(ctx: BuildContext) -> dict[str, str]:
    value = ctx.renderer.get("asset_hashes", {})
    if not isinstance(value, dict):
        raise ValueError("renderer.asset_hashes must be a mapping")
    hashes: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise ValueError("renderer.asset_hashes must map strings to strings")
        hashes[key] = item
    return dict(sorted(hashes.items()))


def _config_str(ctx: BuildContext, key: str, default: str) -> str:
    value = ctx.config.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"config.{key} must be a string")
    return value


def _srt_timestamp(frame: int, fps: int) -> str:
    total_ms = round(frame * 1000 / fps)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


__all__ = [
    "RenderCommandError",
    "RenderEnvironmentError",
    "VIR_MISSING_BROWSER",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_NODE",
    "VIR_TOOL_PROBE_FAILED",
    "browser_version",
    "captions_to_srt",
    "check_environment",
    "render",
]
