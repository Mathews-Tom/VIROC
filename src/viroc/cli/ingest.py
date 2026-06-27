"""Authoring-brief intake for ``viroc ingest``."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from viroc.authoring import (
    authoring_brief_filename,
    build_authoring_brief,
    dump_yaml,
    load_ingest_request,
    project_defaults,
    project_root_from_request,
    viroc_config_filename,
    viroc_config_text,
    write_text,
)
from viroc.cli._common import CliError
from viroc.ir import load_project_config


def register(subparsers: Any) -> None:
    """Register the ``ingest`` subcommand."""

    parser = subparsers.add_parser(
        "ingest",
        help="normalize a topic/repo/docs request into authoring-brief.yaml",
        description=(
            "Normalize a topic, repo, or document-set request into "
            "authoring-brief.yaml and scaffold the target project root."
        ),
    )
    parser.add_argument("request", help="authoring request YAML file")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Write a stable authoring brief and scaffold the target project root."""

    request_path = Path(args.request).expanduser().resolve()
    if not request_path.exists() or not request_path.is_file():
        raise CliError(f"authoring request not found: {request_path}")

    try:
        request = load_ingest_request(request_path)
        project = project_defaults(request)
        project_root = project_root_from_request(request, request_path)
        _ensure_project_root(project_root, project.id, project.default_backend)
        brief = build_authoring_brief(request, request_path)
    except (OSError, UnicodeDecodeError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise CliError(f"failed to load authoring request {request_path}: {exc}") from exc

    brief_path = write_text(project_root / authoring_brief_filename(), dump_yaml(brief))
    print(brief_path)
    return 0


def _ensure_project_root(project_root: Path, project_id: str, default_backend: str) -> None:
    if project_root.exists() and not project_root.is_dir():
        raise CliError(f"cannot ingest into file path: {project_root}")
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "assets").mkdir(exist_ok=True)

    config_path = project_root / viroc_config_filename()
    if not config_path.exists():
        write_text(config_path, viroc_config_text(project_id, default_backend=default_backend))
        return

    try:
        config = load_project_config(config_path)
    except (OSError, UnicodeDecodeError, ValidationError, ValueError, yaml.YAMLError) as exc:
        raise CliError(f"failed to load project config {config_path}: {exc}") from exc
    if config.project != project_id:
        raise CliError(
            "existing viroc.yaml project "
            f"{config.project!r} does not match ingest target {project_id!r}"
        )


__all__ = ["register", "run"]
