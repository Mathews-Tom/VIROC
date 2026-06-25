"""Graph inspection entrypoint for ``viroc graph``."""

from __future__ import annotations

import argparse
from typing import Any

from viroc.cli._common import load_project, print_diagnostics
from viroc.ir import load_document
from viroc.validators import pre_validate


def register(subparsers: Any) -> None:
    """Register the ``graph`` subcommand."""
    parser = subparsers.add_parser("graph", help="print the scene/entity graph")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory or storyboard file (default: current directory)",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    """Render a deterministic text graph from the pre-validated Semantic IR."""
    project = load_project(args.path)
    doc = load_document(project.storyboard_path)
    ir, diagnostics = pre_validate(doc)
    if diagnostics:
        print_diagnostics(diagnostics)
        return 1
    assert ir is not None

    entities = {entity.id: entity for entity in ir.entities}
    print(f"video: {ir.video.id}")
    for scene in ir.scenes:
        print(f"scene: {scene.id}")
        print(f"  grammar: {scene.grammar}")
        print(f"  duration: {scene.duration}")
        print("  nodes:")
        for node_id in scene.nodes:
            entity = entities[node_id]
            print(f"    - {entity.id} [{entity.type}] {entity.label}")
        print("  edges:")
        for edge in scene.edges:
            print(f"    - {edge.from_} -[{edge.kind}]-> {edge.to}")
    return 0


__all__ = ["register", "run"]
