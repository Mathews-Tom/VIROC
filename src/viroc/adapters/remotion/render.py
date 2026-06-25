"""Impure Remotion render path: CLI invocation, caption muxing, and probes."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from viroc.adapters.remotion.emit import materialize_source
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

VIR_MISSING_NODE = code(DiagnosticClass.RENDERER, 51)
VIR_MISSING_NPX = code(DiagnosticClass.RENDERER, 52)
VIR_MISSING_REMOTION = code(DiagnosticClass.RENDERER, 53)
VIR_MISSING_FFMPEG = code(DiagnosticClass.RENDERER, 54)
VIR_MISSING_FFPROBE = code(DiagnosticClass.RENDERER, 55)
VIR_TOOL_PROBE_FAILED = code(DiagnosticClass.RENDERER, 56)

_DEFAULT_OUTPUT_NAME = "viroc"
_DEFAULT_TIMEOUT_SECONDS = 180
_DEFAULT_REMOTION_COMMAND = ("npx", "--no-install", "remotion")
_COMPOSITION_ID = "VirocScene"


class RenderEnvironmentError(RuntimeError):
    """Raised when required render tools are missing or unusable."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("render environment is unavailable")
        self.diagnostics = diagnostics


class RenderCommandError(RuntimeError):
    """Raised when the Remotion CLI or FFmpeg exits unsuccessfully."""

    def __init__(self, command: list[str], stderr: str) -> None:
        super().__init__("render command failed")
        self.command = command
        self.stderr = stderr


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """Return diagnostics for missing or unusable impure render dependencies."""
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(
        _probe_command(
            [_renderer_str(ctx, "node_executable", "node"), "--version"],
            missing_code=VIR_MISSING_NODE,
            label="node",
            help_text='install Node.js or set renderer.node_executable to an absolute path',
        )
    )
    try:
        remotion = _remotion_command(ctx)
    except ValueError as exc:
        return [
            Diagnostic(
                code=VIR_MISSING_REMOTION,
                message="invalid renderer.remotion_command configuration",
                help=str(exc),
            )
        ]
    if remotion[:1] == ["npx"]:
        diagnostics.extend(
            _probe_command(
                ["npx", "--version"],
                missing_code=VIR_MISSING_NPX,
                label="npx",
                help_text='install npm/npx or set renderer.remotion_command to a direct executable',
            )
        )
    diagnostics.extend(
        _probe_command(
            [*remotion, "--version"],
            missing_code=VIR_MISSING_REMOTION,
            label="Remotion CLI",
            help_text=(
                'install Remotion so "npx --no-install remotion --version" succeeds '
                'or set renderer.remotion_command explicitly'
            ),
        )
    )
    diagnostics.extend(
        _probe_command(
            [_renderer_str(ctx, "ffmpeg_executable", "ffmpeg"), "-version"],
            missing_code=VIR_MISSING_FFMPEG,
            label="ffmpeg",
            help_text='install FFmpeg or set renderer.ffmpeg_executable to an absolute path',
        )
    )
    diagnostics.extend(
        _probe_command(
            [_renderer_str(ctx, "ffprobe_executable", "ffprobe"), "-version"],
            missing_code=VIR_MISSING_FFPROBE,
            label="ffprobe",
            help_text='install ffprobe or set renderer.ffprobe_executable to an absolute path',
        )
    )
    return diagnostics


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: Iterable[Caption] = (),
) -> BuildArtifact:
    """Render a generated Remotion project and mux captions with FFmpeg."""
    caption_list = list(captions)
    diagnostics = check_environment(ctx)
    if diagnostics:
        raise RenderEnvironmentError(diagnostics)

    out_dir = ctx.paths.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    render_dir = out_dir / "remotion"
    render_dir.mkdir(parents=True, exist_ok=True)
    project_dir = _materialize_source(source, render_dir / "project")

    srt_text = captions_to_srt(caption_list, _caption_fps(ctx, caption_list))
    srt_path = out_dir / "captions.srt"
    srt_path.write_text(srt_text, encoding="utf-8")

    output_name = _renderer_str(ctx, "output_name", _DEFAULT_OUTPUT_NAME)
    raw_video = render_dir / f"{output_name}-raw.mp4"
    final_path = out_dir / f"{output_name}.mp4"

    _run_remotion(project_dir, raw_video, ctx)
    if srt_text:
        _mux_srt(raw_video, srt_path, final_path, ctx)
    else:
        raw_video.replace(final_path)

    artifact = artifact_from_path("video", final_path)
    _write_build_manifest(source, final_path, ctx)
    return artifact


def remotion_version(ctx: BuildContext) -> str:
    """Return the installed Remotion CLI version string."""
    completed = _run_command([* _remotion_command(ctx), "--version"], timeout=_timeout(ctx))
    output = completed.stdout.strip() or completed.stderr.strip()
    return output.splitlines()[-1] if output else "unknown"


def captions_to_srt(captions: Iterable[Caption], fps: int) -> str:
    """Lower resolved frame captions to deterministic SRT text."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    lines: list[str] = []
    for index, caption in enumerate(captions, start=1):
        lines.extend(
            [
                str(index),
                f"{_srt_timestamp(caption.start_f, fps)} --> {_srt_timestamp(caption.end_f, fps)}",
                caption.text,
                "",
            ]
        )
    return "\n".join(lines)


def _materialize_source(source: BuildArtifact, destination: Path) -> Path:
    if source.path is not None and source.path.is_dir():
        return source.path
    if source.data is not None:
        materialize_source(source, destination)
        return destination
    if source.path is not None:
        materialized = BuildArtifact(
            kind=source.kind,
            digest=source.digest,
            data=source.path.read_bytes(),
            path=source.path,
        )
        materialize_source(materialized, destination)
        return destination
    raise ValueError("source artifact did not carry a Remotion project tree")


def _run_remotion(project_dir: Path, output_path: Path, ctx: BuildContext) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        *_remotion_command(ctx),
        "render",
        "src/index.ts",
        _COMPOSITION_ID,
        str(output_path),
    ]
    completed = _run_command(command, timeout=_timeout(ctx), cwd=project_dir)
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)


def _mux_srt(raw_video: Path, srt_path: Path, final_path: Path, ctx: BuildContext) -> None:
    command = [
        _renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
        "-y",
        "-i",
        str(raw_video),
        "-i",
        str(srt_path),
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        str(final_path),
    ]
    completed = _run_command(command, timeout=_timeout(ctx), cwd=ctx.paths.project_root)
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)


def _write_build_manifest(source: BuildArtifact, video_path: Path, ctx: BuildContext) -> None:
    frames = sample_video_frames(
        video_path,
        sample_count=_renderer_int(ctx, "sample_frames", 4),
        ffmpeg=_renderer_str(ctx, "ffmpeg_executable", "ffmpeg"),
    )
    manifest = build_manifest(
        project=_project(ctx),
        source_hash=source.digest,
        asset_hashes=_asset_hashes(ctx),
        renderer_id="remotion",
        renderer_version=remotion_version(ctx),
        perceptual_hash=perceptual_hash_frames(frames),
        duration_seconds=probe_duration_seconds(
            video_path,
            ffprobe=_renderer_str(ctx, "ffprobe_executable", "ffprobe"),
        ),
        vidir_version=_config_str(ctx, "vidir_version", "0.1"),
    )
    write_manifest(manifest, ctx.paths.out_dir / "build.json")


def _probe_command(
    command: Sequence[str],
    *,
    missing_code: str,
    label: str,
    help_text: str,
) -> list[Diagnostic]:
    executable = command[0]
    if shutil.which(executable) is None:
        return [
            Diagnostic(
                code=missing_code,
                message=f"{label} is not installed",
                help=help_text,
            )
        ]
    completed = _run_command(list(command), timeout=_DEFAULT_TIMEOUT_SECONDS)
    if completed.returncode == 0:
        return []
    stderr = completed.stderr.strip() or completed.stdout.strip() or "tool exited unsuccessfully"
    return [
        Diagnostic(
            code=VIR_TOOL_PROBE_FAILED,
            message=f"{label} probe failed",
            help=stderr,
        )
    ]


def _run_command(
    command: list[str],
    *,
    timeout: int,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )


def _remotion_command(ctx: BuildContext) -> list[str]:
    configured = ctx.renderer.get("remotion_command")
    if configured is None:
        return list(_DEFAULT_REMOTION_COMMAND)
    if isinstance(configured, str):
        return shlex.split(configured)
    if isinstance(configured, Sequence):
        parts = cast(Sequence[object], configured)
        if all(isinstance(part, str) for part in parts):
            return list(cast(Sequence[str], parts))
    raise ValueError("renderer.remotion_command must be a string or sequence of strings")


def _caption_fps(ctx: BuildContext, captions: list[Caption]) -> int:
    if not captions:
        return _renderer_int(ctx, "fps", 30)
    return _renderer_int_required(ctx, "fps")


def _renderer_int_required(ctx: BuildContext, key: str) -> int:
    if key not in ctx.renderer:
        raise ValueError(f"renderer.{key} is required when rendering captions")
    return _renderer_int(ctx, key, 0)


def _renderer_str(ctx: BuildContext, key: str, default: str) -> str:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"renderer.{key} must be a non-empty string")
    return value


def _renderer_int(ctx: BuildContext, key: str, default: int) -> int:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"renderer.{key} must be an integer")
    return value


def _timeout(ctx: BuildContext) -> int:
    return _renderer_int(ctx, "timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)


def _asset_hashes(ctx: BuildContext) -> dict[str, str]:
    value = ctx.renderer.get("asset_hashes", {})
    if not isinstance(value, dict):
        raise ValueError("renderer.asset_hashes must be a mapping")
    hashes: dict[str, str] = {}
    items = cast(dict[object, object], value)
    for asset, digest in items.items():
        if not isinstance(asset, str) or not isinstance(digest, str):
            raise ValueError("renderer.asset_hashes must map strings to strings")
        hashes[asset] = digest
    return dict(sorted(hashes.items()))


def _project(ctx: BuildContext) -> str:
    return _config_str(ctx, "project", ctx.paths.project_root.name)


def _config_str(ctx: BuildContext, key: str, default: str) -> str:
    value = ctx.config.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
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
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_NODE",
    "VIR_MISSING_NPX",
    "VIR_MISSING_REMOTION",
    "VIR_TOOL_PROBE_FAILED",
    "captions_to_srt",
    "check_environment",
    "remotion_version",
    "render",
]
