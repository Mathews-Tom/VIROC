"""Review entrypoint for ``viroc critique``."""

from __future__ import annotations

import argparse
from typing import Any

import viroc.adapters.static_storyboard as static_storyboard
from viroc.cli._common import (
    compile_storyboard,
    load_project,
    print_diagnostics,
)

_REVIEW_DIRNAME = "review"


def register(subparsers: Any) -> None:
    """Register the ``critique`` subcommand."""
    parser = subparsers.add_parser(
        "critique",
        help="emit deterministic static-storyboard review artifacts before render",
        description=(
            "Compile a storyboard and materialize the static-storyboard review "
            "surface (storyboard.md, script.md, scene-cards.json) so the script "
            "and scene structure are inspectable before compile/render."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Compile a storyboard and write the static-storyboard review artifacts."""
    project = load_project(args.path)
    review_dir = project.out_dir / _REVIEW_DIRNAME

    result = compile_storyboard(project)
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1
    assert result.state is not None

    support_diagnostics = static_storyboard.supports(result.state.concrete)
    if support_diagnostics:
        print_diagnostics(support_diagnostics)
        return 1

    source = static_storyboard.emit(result.state.concrete, result.ctx)
    materialized = static_storyboard.materialize_source(source, review_dir)
    root = materialized.path
    assert root is not None

    print(root / "storyboard.md")
    print(root / "script.md")
    print(root / "scene-cards.json")
    print(f"source_hash: {materialized.digest}")
    return 0


__all__ = ["register", "run"]
