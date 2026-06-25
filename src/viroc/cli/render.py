"""Render entrypoint for ``viroc render``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, cast

import viroc.adapters.manim as manim
from viroc.cli._common import (
    compile_storyboard,
    load_expected_render_baseline,
    load_expected_source_hash,
    load_project,
    print_diagnostics,
    write_generated_source,
)
from viroc.compiler.postvalidate import validate_perceptual_hash
from viroc.core import VIR_SOURCE_HASH_MISMATCH, Diagnostic


def register(subparsers: Any) -> None:
    """Register the ``render`` subcommand."""
    parser = subparsers.add_parser("render", help="render the storyboard with the backend")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    parser.add_argument("--backend", default=None, choices=["manim"], help="backend id")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Compile a storyboard, render it, and verify any committed baseline."""
    project = load_project(args.path)
    baseline = load_expected_render_baseline(project)
    sample_frames = baseline.sample_frames if baseline is not None else 4
    result = compile_storyboard(project, sample_frames=sample_frames)
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    assert result.state is not None

    support_diagnostics = manim.supports(result.state.concrete)
    if support_diagnostics:
        print_diagnostics(support_diagnostics)
        return 1

    source = manim.emit(result.state.concrete, result.ctx)
    materialized = write_generated_source(source, project, backend="manim")
    expected_hash = load_expected_source_hash(project)
    if expected_hash is not None and materialized.digest != expected_hash:
        print_diagnostics(
            [
                Diagnostic(
                    code=VIR_SOURCE_HASH_MISMATCH,
                    message="generated source hash does not match expected baseline",
                    help=f"expected {expected_hash}, got {materialized.digest}",
                )
            ]
        )
        return 1

    env_diagnostics = manim.check_environment(result.ctx)
    if env_diagnostics:
        print('render skipped: backend "manim" is unavailable', file=sys.stderr)
        print_diagnostics(env_diagnostics)
        return 0

    try:
        video = manim.render(materialized, result.ctx, captions=result.state.concrete.captions)
    except manim.RenderEnvironmentError as exc:
        print_diagnostics(exc.diagnostics)
        return 1
    except manim.RenderCommandError as exc:
        print("render failed:", *exc.command, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1

    manifest_path = result.ctx.paths.out_dir / "build.json"
    manifest = cast(dict[str, object], json.loads(manifest_path.read_text(encoding="utf-8")))
    perceptual_hash = cast(str, manifest["perceptual_hash"])
    if baseline is not None:
        diagnostics = validate_perceptual_hash(
            perceptual_hash,
            baseline.perceptual_hash,
            threshold=baseline.threshold,
        )
        if diagnostics:
            print_diagnostics(diagnostics)
            return 1

    print(video.path)
    print(manifest_path)
    print(f"source_hash: {materialized.digest}")
    print(f"perceptual_hash: {perceptual_hash}")
    return 0


__all__ = ["register", "run"]
