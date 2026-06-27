"""Starter script/scene-plan/VidIR generation for ``viroc plan``."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from viroc.authoring import (
    authoring_brief_filename,
    build_scene_plan,
    build_script_document,
    dump_yaml,
    load_authoring_brief,
    scene_plan_filename,
    scene_plan_to_vidir,
    script_filename,
    script_markdown,
    storyboard_filename,
    write_text,
)
from viroc.authoring.live_claude import LivePlannerError, build_live_scene_plan
from viroc.cli._common import CliError, compile_storyboard, load_project, print_diagnostics
from viroc.ir import load_project_config


def register(subparsers: Any) -> None:
    """Register the ``plan`` subcommand."""

    parser = subparsers.add_parser(
        "plan",
        help="emit script.md, scene-plan.yaml, and starter storyboard.vidir.yaml",
        description=(
            "Emit script.md, scene-plan.yaml, and starter storyboard.vidir.yaml "
            "from a project's authoring-brief.yaml."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory with authoring-brief.yaml (default: current directory)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="use the optional Claude-backed planner instead of the deterministic starter path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite storyboard.vidir.yaml when it already exists with different content",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Plan authoring artifacts from a stable brief and verify the emitted VidIR."""

    project_root = Path(args.path).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise CliError(f"authoring project not found: {project_root}")

    try:
        config = load_project_config(project_root / "viroc.yaml")
        brief = load_authoring_brief(project_root / authoring_brief_filename())
    except (OSError, UnicodeDecodeError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise CliError(f"failed to load authoring inputs from {project_root}: {exc}") from exc
    if config.project != brief.project.id:
        raise CliError(
            "authoring brief project "
            f"{brief.project.id!r} does not match viroc.yaml project {config.project!r}"
        )

    try:
        scene_plan = build_live_scene_plan(brief) if args.live else build_scene_plan(brief)
    except LivePlannerError as exc:
        raise CliError(str(exc)) from exc
    except ValueError as exc:
        raise CliError(str(exc)) from exc

    script = build_script_document(brief, scene_plan)
    storyboard = scene_plan_to_vidir(scene_plan)

    scene_plan_path = write_text(project_root / scene_plan_filename(), dump_yaml(scene_plan))
    script_path = write_text(project_root / script_filename(), script_markdown(script))
    storyboard_path = _write_storyboard(project_root, dump_yaml(storyboard), force=args.force)

    result = compile_storyboard(load_project(project_root))
    if result.diagnostics:
        print_diagnostics(result.diagnostics)
        return 1

    print(scene_plan_path)
    print(script_path)
    print(storyboard_path)
    print(f"next: viroc critique {project_root}")
    return 0


def _write_storyboard(project_root: Path, content: str, *, force: bool) -> Path:
    path = project_root / storyboard_filename()
    if not path.exists():
        return write_text(path, content)
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CliError(f"failed to read existing storyboard {path}: {exc}") from exc
    if existing == content:
        return path
    if not force:
        raise CliError(
            f"{path.name} already contains edits; rerun `viroc plan {project_root} --force` "
            "to replace it"
        )
    return write_text(path, content)


__all__ = ["register", "run"]
