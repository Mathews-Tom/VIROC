"""Validation entrypoint for ``viroc check``."""

from __future__ import annotations

import argparse
from typing import Any

from viroc.cli._common import compile_storyboard, load_project, print_diagnostics


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
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Check a storyboard end to end without emitting backend artifacts."""
    result = compile_storyboard(load_project(args.path))
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    return 0


__all__ = ["register", "run"]
