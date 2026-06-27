"""Stable serialization and ingest helpers for authoring artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from viroc.authoring.models import (
    AuthoringBrief,
    BriefProject,
    ContextItem,
    ContextRequest,
    IngestRequest,
)
from viroc.core import hash_bytes, slugify

_BRIEF_FILENAME = "authoring-brief.yaml"
_SCENE_PLAN_FILENAME = "scene-plan.yaml"
_SCRIPT_FILENAME = "script.md"
_STORYBOARD_FILENAME = "storyboard.vidir.yaml"
_VIROC_CONFIG_FILENAME = "viroc.yaml"


def authoring_brief_filename() -> str:
    return _BRIEF_FILENAME


def scene_plan_filename() -> str:
    return _SCENE_PLAN_FILENAME


def script_filename() -> str:
    return _SCRIPT_FILENAME


def storyboard_filename() -> str:
    return _STORYBOARD_FILENAME


def viroc_config_filename() -> str:
    return _VIROC_CONFIG_FILENAME


def project_defaults(request: IngestRequest) -> BriefProject:
    """Resolve stable project metadata from a typed ingest request."""

    project_id = request.project.id or slugify(request.source.title)
    title = request.project.title or request.source.title
    return BriefProject(
        id=project_id,
        title=title,
        duration_target=request.project.duration_target,
        default_backend=request.project.default_backend,
    )


def build_authoring_brief(request: IngestRequest, request_path: Path) -> AuthoringBrief:
    """Materialize repo/document context into the stable authoring brief."""

    context_items = _context_items(request.context, request_path)
    notes = list(request.context.notes) if request.context is not None else []
    return AuthoringBrief(
        project=project_defaults(request),
        source=request.source,
        entities=request.entities,
        scene_seeds=request.scene_seeds,
        context_items=context_items,
        notes=notes,
    )


def load_ingest_request(path: Path) -> IngestRequest:
    """Load one typed ingest request YAML file."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return IngestRequest.model_validate(data)


def load_authoring_brief(path: Path) -> AuthoringBrief:
    """Load a previously written authoring brief."""

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AuthoringBrief.model_validate(data)


def dump_yaml(model: object) -> str:
    """Serialize a Pydantic-style model or mapping to stable YAML."""
    if isinstance(model, BaseModel):
        data = model.model_dump(by_alias=True, exclude_none=True)
    else:
        data = model
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=4096,
    )


def write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text and return the resolved path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def project_root_from_request(request: IngestRequest, request_path: Path) -> Path:
    """Resolve the ingest request's target project path."""

    return (request_path.parent / request.project.path).resolve()


def excerpt_text(text: str, *, max_lines: int = 12, max_chars: int = 1200) -> str:
    """Return a deterministic excerpt for a context file."""

    lines = text.splitlines()
    clipped = "\n".join(lines[:max_lines]).strip()
    if len(clipped) > max_chars:
        return clipped[: max_chars - 1].rstrip() + "…"
    return clipped


def file_digest(text: str) -> str:
    """Return the stable digest for one text context item."""

    return hash_bytes(text.encode("utf-8"))


def viroc_config_text(project_id: str, *, default_backend: str) -> str:
    """Return the standard project config text shared by init/ingest."""

    return (
        f"project: {project_id}\n"
        f"default_backend: {default_backend}\n"
        "paths:\n"
        "  out: build\n"
    )


def _context_items(context: ContextRequest | None, request_path: Path) -> list[ContextItem]:
    items: list[ContextItem] = []
    if context is None:
        return items
    for note in context.notes:
        items.append(ContextItem(kind="note", label="note", excerpt=note))
    for document in context.documents:
        path = (request_path.parent / document.path).resolve()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(
                "failed to read document context "
                f"{document.path!r} referenced by {request_path}: {exc}"
            ) from exc
        items.append(
            ContextItem(
                kind="document",
                label=document.label or path.name,
                path=document.path,
                digest=file_digest(text),
                excerpt=excerpt_text(text),
            )
        )
    if context.repo is None:
        return items
    root = (request_path.parent / context.repo.root).resolve()
    for relative in context.repo.files:
        path = (root / relative).resolve()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(
                f"failed to read repo context file {relative!r} from {context.repo.root!r}: {exc}"
            ) from exc
        items.append(
            ContextItem(
                kind="repo_file",
                label=Path(relative).name,
                path=relative,
                digest=file_digest(text),
                excerpt=excerpt_text(text),
            )
        )
    return items


__all__ = [
    "authoring_brief_filename",
    "build_authoring_brief",
    "dump_yaml",
    "excerpt_text",
    "file_digest",
    "load_authoring_brief",
    "load_ingest_request",
    "project_defaults",
    "project_root_from_request",
    "scene_plan_filename",
    "script_filename",
    "storyboard_filename",
    "viroc_config_filename",
    "viroc_config_text",
    "write_text",
]
