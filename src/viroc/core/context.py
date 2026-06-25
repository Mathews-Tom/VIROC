"""Build context and artifacts shared across the compiler and adapters.

A :class:`BuildContext` is the read-only environment threaded through a compile:
where the project lives, where outputs go, project config, and renderer config
(design §5 adapter contract). A :class:`BuildArtifact` is a content-addressed
output — generated source, a rendered video, captions, a manifest — pairing the
payload (in memory and/or on disk) with its ``sha256:`` digest.

These are pure data carriers; construction helpers that compute the digest live
as module functions (:func:`artifact_from_bytes`, :func:`artifact_from_text`,
:func:`artifact_from_path`) so the dataclasses stay behavior-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from viroc.core.hashing import hash_bytes


@dataclass(frozen=True, slots=True)
class BuildPaths:
    """Filesystem locations for a build: the project root and the output dir."""

    project_root: Path
    out_dir: Path


@dataclass(frozen=True, slots=True)
class BuildContext:
    """The read-only environment for one compile.

    ``config`` is the project configuration (``viroc.yaml``); ``renderer`` is the
    selected backend's configuration. Both default to empty mappings so a context
    can be built from paths alone.
    """

    paths: BuildPaths
    config: dict[str, Any] = field(default_factory=dict[str, Any])
    renderer: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass(frozen=True, slots=True)
class BuildArtifact:
    """A content-addressed build output.

    ``kind`` names the output ("source", "video", "captions", "manifest", …).
    ``digest`` is the ``sha256:`` hash of the content. ``data`` holds the bytes
    when the artifact is in memory; ``path`` records its on-disk location once
    materialized. An artifact may carry either or both.
    """

    kind: str
    digest: str
    data: bytes | None = None
    path: Path | None = None


def artifact_from_bytes(kind: str, data: bytes, *, path: Path | None = None) -> BuildArtifact:
    """Build a :class:`BuildArtifact` from in-memory bytes, hashing the content."""
    return BuildArtifact(kind=kind, digest=hash_bytes(data), data=data, path=path)


def artifact_from_text(kind: str, text: str, *, path: Path | None = None) -> BuildArtifact:
    """Build a :class:`BuildArtifact` from text (UTF-8 encoded before hashing)."""
    return artifact_from_bytes(kind, text.encode("utf-8"), path=path)


def artifact_from_path(kind: str, path: Path) -> BuildArtifact:
    """Build a :class:`BuildArtifact` from a file on disk, hashing its bytes.

    The bytes are read to compute the digest but not retained on the artifact;
    ``data`` is left ``None`` so large outputs (e.g. video) are not held in
    memory.
    """
    return BuildArtifact(kind=kind, digest=hash_bytes(path.read_bytes()), path=path)
