"""VIROC command-line surface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from viroc import __version__
from viroc.cli import check, compile, doctor, graph, ingest, init, plan, render
from viroc.cli._common import CliError

__all__ = ["main"]


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="viroc")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    init.register(subparsers)
    check.register(subparsers)
    compile.register(subparsers)
    render.register(subparsers)
    graph.register(subparsers)
    doctor.register(subparsers)
    ingest.register(subparsers)
    plan.register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``viroc`` console script."""
    parser = build_parser()
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        parser.print_help()
        return 0
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exc:
        return 0 if exc.code is None else int(exc.code)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return int(handler(args))
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 2
