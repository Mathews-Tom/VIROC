"""Render entrypoint for ``viroc render``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, cast

from viroc.adapters.registry import UnknownBackendError
from viroc.cli._common import (
    compile_storyboard,
    load_expected_render_baseline,
    load_expected_source_hash,
    load_project,
    print_diagnostics,
    register_backend_argument,
    resolve_backend,
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
    register_backend_argument(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Compile a storyboard, render it, and verify any committed baseline."""
    project = load_project(args.path)
    try:
        adapter = resolve_backend(project, args.backend)
    except UnknownBackendError as exc:
        print_diagnostics([exc.diagnostic])
        return 1
    baseline = load_expected_render_baseline(project, backend=adapter.id)
    sample_frames = baseline.sample_frames if baseline is not None else 4
    result = compile_storyboard(project, sample_frames=sample_frames)
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    assert result.state is not None

    support_diagnostics = adapter.supports(result.state.concrete)
    if support_diagnostics:
        print_diagnostics(support_diagnostics)
        return 1

    source = adapter.emit(result.state.concrete, result.ctx)
    materialized = write_generated_source(source, project, adapter=adapter)
    expected_hash = load_expected_source_hash(project, backend=adapter.id)
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
    env_diagnostics = adapter.check_environment(result.ctx)


    if env_diagnostics:

        print_diagnostics(env_diagnostics)
        return 1

    render_environment_error = getattr(adapter, "RenderEnvironmentError", None)
    render_command_error = getattr(adapter, "RenderCommandError", None)
    try:
        video = adapter.render(
            materialized,
            result.ctx,
            captions=result.state.concrete.captions,
        )
    except Exception as exc:
        if render_environment_error is not None and isinstance(exc, render_environment_error):
            env_exc = cast(Any, exc)
            print_diagnostics(env_exc.diagnostics)
            return 1
        if render_command_error is not None and isinstance(exc, render_command_error):
            command_exc = cast(Any, exc)
            print("render failed:", *command_exc.command, file=sys.stderr)
            if command_exc.stderr:
                print(command_exc.stderr, file=sys.stderr)
            return 1
        raise

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
