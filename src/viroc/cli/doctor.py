"""Environment inspection entrypoint for ``viroc doctor``."""

from __future__ import annotations

import argparse
from typing import Any

from viroc.adapters.registry import UnknownBackendError
from viroc.cli._common import (
    backend_version,
    build_context,
    load_project,
    print_diagnostics,
    register_backend_argument,
    resolve_backend,
)


def register(subparsers: Any) -> None:
    """Register the ``doctor`` subcommand."""
    parser = subparsers.add_parser("doctor", help="report backend environment status")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    register_backend_argument(parser)
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Report backend environment diagnostics without attempting a render."""
    project = load_project(args.path)
    try:
        adapter = resolve_backend(project, args.backend)
    except UnknownBackendError as exc:
        print_diagnostics([exc.diagnostic])
        return 1
    ctx = build_context(project)
    diagnostics = adapter.check_environment(ctx)

    print(f"backend: {adapter.id}")
    if diagnostics:
        print("status: unavailable")
        print_diagnostics(diagnostics)
        return 1

    print("status: ok")
    print(f"version: {backend_version(adapter, ctx)}")
    return 0


__all__ = ["register", "run"]
