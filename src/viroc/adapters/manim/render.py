"""Impure Manim render path: backend invocation, caption muxing, and probes."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from viroc.core import (
    BuildArtifact,
    BuildContext,
    Diagnostic,
    DiagnosticClass,
    artifact_from_path,
    code,
)
from viroc.ir import Caption

VIR_MISSING_MANIM = code(DiagnosticClass.RENDERER, 41)
VIR_MISSING_FFMPEG = code(DiagnosticClass.RENDERER, 42)
VIR_TOOL_PROBE_FAILED = code(DiagnosticClass.RENDERER, 43)
VIR_MISSING_FFPROBE = code(DiagnosticClass.RENDERER, 44)

_DEFAULT_SCENE_CLASS = "VirocScene"
_DEFAULT_SEED = 0
_DEFAULT_QUALITY = "-ql"
_DEFAULT_OUTPUT_NAME = "viroc"


class RenderEnvironmentError(RuntimeError):
    """Raised when required render tools are missing or unusable."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("render environment is not available")
        self.diagnostics = diagnostics


class RenderCommandError(RuntimeError):
    """Raised when Manim or FFmpeg exits unsuccessfully."""

    def __init__(self, command: list[str], stderr: str) -> None:
        super().__init__(f"render command failed: {' '.join(command)}")
        self.command = command
        self.stderr = stderr


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """Return diagnostics for missing or unusable impure render dependencies."""
    manim = _renderer_str(ctx, "manim_executable", "manim")
    ffmpeg = _renderer_str(ctx, "ffmpeg_executable", "ffmpeg")
    ffprobe = _renderer_str(ctx, "ffprobe_executable", "ffprobe")
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_probe_tool(manim, ["--version"], VIR_MISSING_MANIM, "Manim"))
    diagnostics.extend(_probe_tool(ffmpeg, ["-version"], VIR_MISSING_FFMPEG, "FFmpeg"))
    diagnostics.extend(_probe_tool(ffprobe, ["-version"], VIR_MISSING_FFPROBE, "ffprobe"))
    return diagnostics


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: Iterable[Caption] = (),
) -> BuildArtifact:
    """Render ``scene.py`` with Manim and mux SRT captions with FFmpeg.

    The generated source remains the reproducibility boundary; this function is
    deliberately impure and fails loudly when the render environment is absent.
    """
    diagnostics = check_environment(ctx)
    if diagnostics:
        raise RenderEnvironmentError(diagnostics)

    out_dir = ctx.paths.out_dir
    render_dir = out_dir / "manim"
    media_dir = render_dir / "media"
    render_dir.mkdir(parents=True, exist_ok=True)
    source_path = _materialize_source(source, render_dir / "scene.py")
    srt_path = out_dir / "captions.srt"
    srt_path.write_text(captions_to_srt(captions, _renderer_int(ctx, "fps", 30)), encoding="utf-8")

    raw_name = f"{_renderer_str(ctx, 'output_name', _DEFAULT_OUTPUT_NAME)}-raw"
    final_path = out_dir / f"{_renderer_str(ctx, 'output_name', _DEFAULT_OUTPUT_NAME)}.mp4"
    _run_manim(source_path, media_dir, raw_name, ctx)
    raw_video = _latest_rendered_video(media_dir, raw_name)
    if srt_path.read_text(encoding="utf-8"):
        _mux_srt(raw_video, srt_path, final_path, ctx)
    else:
        shutil.copy2(raw_video, final_path)
    return artifact_from_path("video", final_path)


def captions_to_srt(captions: Iterable[Caption], fps: int) -> str:
    """Lower resolved frame captions to deterministic SRT text."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    lines: list[str] = []
    ordered = sorted(captions, key=lambda item: (item.start_f, item.end_f, item.text))
    for index, caption in enumerate(ordered, start=1):
        if caption.end_f < caption.start_f:
            raise ValueError(
                f"caption end frame {caption.end_f} precedes start frame {caption.start_f}"
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


def manim_version(ctx: BuildContext) -> str:
    """Return the installed Manim version string reported by the CLI."""
    command = _renderer_str(ctx, "manim_executable", "manim")
    completed = _run_command([command, "--version"], timeout=10)
    output = (completed.stdout or completed.stderr).strip()
    return output.rsplit(" ", maxsplit=1)[-1] if output else "unknown"


def _probe_tool(
    command: str, args: list[str], missing_code: str, label: str
) -> list[Diagnostic]:
    if shutil.which(command) is None:
        return [
            Diagnostic(
                code=missing_code,
                message=f"{label} executable not found",
                help=f'install {label} or set renderer.{command}_executable to its path',
            )
        ]
    completed = _run_command([command, *args], timeout=10)
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
    if source.path is None:
        raise ValueError("source artifact must carry data or a path")
    destination.write_bytes(source.path.read_bytes())
    return destination


def _run_manim(source_path: Path, media_dir: Path, raw_name: str, ctx: BuildContext) -> None:
    command = [
        _renderer_str(ctx, "manim_executable", "manim"),
        "render",
        _renderer_str(ctx, "quality", _DEFAULT_QUALITY),
        "--disable_caching",
        "--media_dir",
        str(media_dir),
        "--format=mp4",
        "-o",
        raw_name,
        "--seed",
        str(_renderer_int(ctx, "seed", _DEFAULT_SEED)),
        str(source_path),
        _renderer_str(ctx, "scene_class", _DEFAULT_SCENE_CLASS),
    ]
    completed = _run_command(command, timeout=_renderer_int(ctx, "timeout_seconds", 120))
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
    completed = _run_command(command, timeout=_renderer_int(ctx, "timeout_seconds", 120))
    if completed.returncode != 0:
        raise RenderCommandError(command, completed.stderr)


def _latest_rendered_video(media_dir: Path, raw_name: str) -> Path:
    candidates = sorted(
        media_dir.rglob(f"{raw_name}.mp4"), key=lambda path: (path.stat().st_mtime_ns, str(path))
    )
    if not candidates:
        raise FileNotFoundError(f"Manim did not produce {raw_name}.mp4 under {media_dir}")
    return candidates[-1]


def _srt_timestamp(frame: int, fps: int) -> str:
    total_ms = round(frame * 1000 / fps)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _run_command(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _renderer_str(ctx: BuildContext, key: str, default: str) -> str:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, str):
        raise TypeError(f"renderer.{key} must be a string")
    return value


def _renderer_int(ctx: BuildContext, key: str, default: int) -> int:
    value = ctx.renderer.get(key, default)
    if not isinstance(value, int):
        raise TypeError(f"renderer.{key} must be an int")
    return value


__all__ = [
    "RenderCommandError",
    "RenderEnvironmentError",
    "VIR_MISSING_FFMPEG",
    "VIR_MISSING_FFPROBE",
    "VIR_MISSING_MANIM",
    "VIR_TOOL_PROBE_FAILED",
    "captions_to_srt",
    "check_environment",
    "manim_version",
    "render",
]
