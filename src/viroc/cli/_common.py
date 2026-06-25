"""Shared helpers for the VIROC command-line surface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from viroc.adapters import RendererAdapter
from viroc.adapters.registry import builtin_registry
from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import (
    BuildArtifact,
    BuildContext,
    BuildPaths,
    Diagnostic,
    artifact_from_path,
    render,
)
from viroc.ir import ProjectConfig, SemanticIR, load_document, load_project_config
from viroc.validators import pre_validate

_DEFAULT_OUT_DIR = "build"
_DEFAULT_SAMPLE_FRAMES = 4
_DEFAULT_TIMEOUT_SECONDS = 180
_DEFAULT_QUALITY = "-ql"
_DEFAULT_SEED = 0


class CliError(RuntimeError):
    """User-facing command error with a direct stderr message."""


@dataclass(frozen=True, slots=True)
class Project:
    """Resolved project inputs for one CLI invocation."""

    project_root: Path
    storyboard_path: Path
    config_path: Path | None
    config: ProjectConfig
    expected_dir: Path

    @property
    def out_dir(self) -> Path:
        return self.project_root / self.config.paths.get("out", _DEFAULT_OUT_DIR)


@dataclass(frozen=True, slots=True)
class CompileResult:
    """One storyboard compile attempt and its validation outcome."""

    project: Project
    ctx: BuildContext
    ir: SemanticIR | None
    state: CompileState | None
    diagnostics: list[Diagnostic]

    @property
    def ok(self) -> bool:
        return not self.diagnostics and self.ir is not None and self.state is not None


@dataclass(frozen=True, slots=True)
class RenderBaseline:
    """Committed perceptual-render baseline for one example project."""

    perceptual_hash: str
    threshold: int
    sample_frames: int


def load_project(target: str | Path = ".") -> Project:
    """Resolve ``target`` to a project root, config, and storyboard path."""
    path = Path(target).expanduser().resolve()
    if path.exists() and path.is_file():
        root = path.parent
        config_path = root / "viroc.yaml"
        config = _load_config(config_path, root)
        return Project(
            project_root=root,
            storyboard_path=path,
            config_path=config_path if config_path.exists() else None,
            config=config,
            expected_dir=root / "expected",
        )
    if not path.exists():
        raise CliError(f"path not found: {path}")
    if not path.is_dir():
        raise CliError(f"expected a directory or storyboard file, got: {path}")
    config_path = path / "viroc.yaml"
    config = _load_config(config_path, path)
    storyboard_path = _resolve_storyboard(path, config)
    return Project(
        project_root=path,
        storyboard_path=storyboard_path,
        config_path=config_path if config_path.exists() else None,
        config=config,
        expected_dir=path / "expected",
    )


def build_context(
    project: Project,
    *,
    video_id: str | None = None,
    fps: int | None = None,
    asset_hashes: dict[str, str] | None = None,
    sample_frames: int = _DEFAULT_SAMPLE_FRAMES,
) -> BuildContext:
    """Construct the shared build context for one CLI action."""
    renderer: dict[str, object] = {
        "quality": _DEFAULT_QUALITY,
        "sample_frames": sample_frames,
        "seed": _DEFAULT_SEED,
        "timeout_seconds": _DEFAULT_TIMEOUT_SECONDS,
    }
    if video_id is not None:
        renderer["output_name"] = video_id
    if fps is not None:
        renderer["fps"] = fps
    if asset_hashes is not None:
        renderer["asset_hashes"] = asset_hashes
    return BuildContext(
        paths=BuildPaths(project_root=project.project_root, out_dir=project.out_dir),
        config={"project": project.config.project, "vidir_version": "0.1"},
        renderer=renderer,
    )


def compile_storyboard(
    project: Project, *, sample_frames: int = _DEFAULT_SAMPLE_FRAMES
) -> CompileResult:
    """Load, pre-validate, and compile ``project`` through P9."""
    doc = load_document(project.storyboard_path)
    ir, diagnostics = pre_validate(doc)
    if ir is None:
        return CompileResult(
            project=project,
            ctx=build_context(project),
            ir=None,
            state=None,
            diagnostics=diagnostics,
        )
    ctx = build_context(
        project,
        video_id=ir.video.id,
        fps=ir.video.fps,
        sample_frames=sample_frames,
    )
    if diagnostics:
        return CompileResult(project=project, ctx=ctx, ir=ir, state=None, diagnostics=diagnostics)
    state = run_pipeline(ir, ctx)
    return CompileResult(
        project=project,
        ctx=ctx,
        ir=ir,
        state=state,
        diagnostics=state.diagnostics,
    )


def print_diagnostics(diagnostics: list[Diagnostic]) -> None:
    """Render diagnostics in the compiler-grade text format to stderr."""
    if not diagnostics:
        return
    print("\n\n".join(render(diagnostic) for diagnostic in diagnostics), file=sys.stderr)


def load_expected_source_hash(project: Project) -> str | None:
    """Return the committed source-hash baseline when the project provides one."""
    path = project.expected_dir / "source.sha256"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def load_expected_render_baseline(project: Project) -> RenderBaseline | None:
    """Return the committed perceptual-render baseline when the project provides one."""
    path = project.expected_dir / "render.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = cast(dict[str, object], data)
    perceptual_hash = raw.get("perceptual_hash")
    threshold = raw.get("threshold", 4)
    sample_frames = raw.get("sample_frames", _DEFAULT_SAMPLE_FRAMES)
    if not isinstance(perceptual_hash, str):
        raise CliError(f"expected {path} to define string perceptual_hash")
    if not isinstance(threshold, int):
        raise CliError(f"expected {path} to define integer threshold")
    if not isinstance(sample_frames, int):
        raise CliError(f"expected {path} to define integer sample_frames")
    return RenderBaseline(
        perceptual_hash=perceptual_hash,
        threshold=threshold,
        sample_frames=sample_frames,
    )


def write_generated_source(
    source: BuildArtifact, project: Project, *, backend: str
) -> BuildArtifact:
    path = project.out_dir / "generated" / backend / "scene.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    if source.data is not None:
        path.write_bytes(source.data)
        artifact = artifact_from_path(source.kind, path)
        if artifact.digest != source.digest:
            raise CliError("written source hash does not match emitted source")
        return artifact
    if source.path is not None:
        path.write_bytes(source.path.read_bytes())
        return artifact_from_path(source.kind, path)
    raise CliError("source artifact did not carry bytes or a path")

def register_backend_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--backend`` selector to one CLI subcommand."""
    parser.add_argument("--backend", default=None, help="backend id")


def resolve_backend(project: Project, requested: str | None) -> RendererAdapter:
    """Resolve the requested backend, defaulting to project config."""
    backend = requested or project.config.default_backend
    return builtin_registry().require(backend)


def backend_version(adapter: RendererAdapter, ctx: BuildContext) -> str:
    """Report the adapter version string for ``doctor`` output."""
    version_fn = getattr(adapter, "tool_version", None)
    if callable(version_fn):
        reported = version_fn(ctx)
        if isinstance(reported, str):
            return reported
    return adapter.version


def _load_config(config_path: Path, root: Path) -> ProjectConfig:
    if config_path.exists():
        return load_project_config(config_path)
    return ProjectConfig.model_validate({"project": root.name})


def _resolve_storyboard(root: Path, config: ProjectConfig) -> Path:
    candidates = [root / "storyboard.vidir.yaml"]
    storyboards = config.paths.get("storyboards")
    if storyboards:
        candidates.append(root / storyboards / "storyboard.vidir.yaml")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise CliError(f"storyboard.vidir.yaml not found; searched: {searched}")


__all__ = [
    "CliError",
    "CompileResult",
    "Project",
    "RenderBaseline",
    "backend_version",
    "build_context",
    "compile_storyboard",
    "load_expected_render_baseline",
    "load_expected_source_hash",
    "load_project",
    "print_diagnostics",
    "register_backend_argument",
    "resolve_backend",
    "write_generated_source",
]
