"""Project scaffolding for ``viroc init``."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent
from typing import Any

from viroc.cli._common import CliError


def register(subparsers: Any) -> None:
    """Register the ``init`` subcommand."""
    parser = subparsers.add_parser("init", help="scaffold a new VIROC project")
    parser.add_argument("path", help="directory to create")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Scaffold a starter project with config, storyboard, and assets dir."""
    target = Path(args.path).expanduser()
    if target.exists() and not target.is_dir():
        raise CliError(f"cannot initialize project at file path: {target}")
    if target.exists() and any(target.iterdir()):
        raise CliError(f"target directory is not empty: {target}")

    target.mkdir(parents=True, exist_ok=True)
    (target / "assets").mkdir(exist_ok=True)

    project_id = target.name or "viroc-project"
    title = project_id.replace("-", " ").replace("_", " ").title()

    (target / "viroc.yaml").write_text(
        dedent(
            f"""\
            project: {project_id}
            default_backend: manim
            paths:
              out: build
            """
        ),
        encoding="utf-8",
    )
    (target / "storyboard.vidir.yaml").write_text(
        dedent(
            f"""\
            vidir_version: "0.1"
            video:
              id: "{project_id}"
              title: "{title}"
              resolution: {{ width: 1920, height: 1080 }}
              fps: 30

            entities:
              - {{ id: start, label: "Start", type: data_source }}

            scenes:
              - id: intro
                grammar: pipeline
                duration: 5s
                nodes: [start]
                narration: "Describe this scene."

            validation:
              required_entities: [start]
              checks: [schema, layout, timing]
            """
        ),
        encoding="utf-8",
    )
    print(target.resolve())
    return 0


__all__ = ["register", "run"]
