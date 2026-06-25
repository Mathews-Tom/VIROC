"""Source emission entrypoint for ``viroc compile``."""

from __future__ import annotations

import argparse
from typing import Any

import viroc.adapters.manim as manim
from viroc.cli._common import (
    compile_storyboard,
    load_expected_source_hash,
    load_project,
    print_diagnostics,
    resolve_backend,
    write_generated_source,
)
from viroc.core import VIR_SOURCE_HASH_MISMATCH, Diagnostic


def register(subparsers: Any) -> None:
    """Register the ``compile`` subcommand."""
    parser = subparsers.add_parser("compile", help="emit deterministic backend source")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    parser.add_argument("--backend", default=None, choices=["manim"], help="backend id")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Compile a storyboard and emit backend source to the build directory."""
    project = load_project(args.path)
    backend = resolve_backend(project, args.backend)
    result = compile_storyboard(project)
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    assert result.state is not None

    diagnostics = manim.supports(result.state.concrete)
    if diagnostics:
        print_diagnostics(diagnostics)
        return 1

    source = manim.emit(result.state.concrete, result.ctx)
    materialized = write_generated_source(source, project, backend=backend)
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

    print(materialized.path)
    print(f"source_hash: {materialized.digest}")
    return 0


__all__ = ["register", "run"]
