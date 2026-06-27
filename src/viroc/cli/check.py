"""Validation entrypoint for ``viroc check``."""

from __future__ import annotations

import argparse
from typing import Any

from viroc.adapters.registry import UnknownBackendError
from viroc.cli._common import (
    compile_storyboard,
    has_errors,
    load_project,
    print_diagnostics,
    register_backend_argument,
    resolve_backend,
)


def register(subparsers: Any) -> None:
    """Register the ``check`` subcommand."""
    parser = subparsers.add_parser(
        "check",
        help="run pre-validation and post-resolve validation",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    register_backend_argument(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Check a storyboard end to end without emitting backend artifacts."""
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
    return 0


__all__ = ["register", "run"]
