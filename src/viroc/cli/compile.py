"""Source emission entrypoint for ``viroc compile``."""

from __future__ import annotations

import argparse
from typing import Any

from viroc.adapters.registry import UnknownBackendError
from viroc.cli._common import (
    compile_storyboard,
    has_errors,
    load_expected_source_hash,
    load_project,
    print_diagnostics,
    register_backend_argument,
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
    register_backend_argument(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Compile a storyboard and emit backend source to the build directory."""
    project = load_project(args.path)
    try:
        adapter = resolve_backend(project, args.backend)
    except UnknownBackendError as exc:
        print_diagnostics([exc.diagnostic])
        return 1
    result = compile_storyboard(project)
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    assert result.state is not None

    diagnostics = adapter.supports(result.state.concrete)
    print_diagnostics(diagnostics)
    if has_errors(diagnostics):
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

    print(materialized.path)
    print(f"source_hash: {materialized.digest}")
    return 0


__all__ = ["register", "run"]
