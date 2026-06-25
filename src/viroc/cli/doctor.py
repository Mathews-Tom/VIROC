"""Environment inspection entrypoint for ``viroc doctor``."""

from __future__ import annotations

import argparse
from typing import Any

import viroc.adapters.manim as manim
from viroc.cli._common import build_context, load_project, print_diagnostics, resolve_backend


def register(subparsers: Any) -> None:
    """Register the ``doctor`` subcommand."""
    parser = subparsers.add_parser("doctor", help="report backend environment status")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    parser.add_argument("--backend", default=None, choices=["manim"], help="backend id")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Report backend environment diagnostics without attempting a render."""
    project = load_project(args.path)
    backend = resolve_backend(project, args.backend)
    ctx = build_context(project)
    diagnostics = manim.check_environment(ctx)

    print(f"backend: {backend}")
    if diagnostics:
        print("status: unavailable")
        print_diagnostics(diagnostics)
        return 0

    print("status: ok")
    print(f"version: {manim.manim_version(ctx)}")
    return 0


__all__ = ["register", "run"]
