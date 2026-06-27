"""Static storyboard review adapter: deterministic scene cards and script artifacts."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from pathlib import Path

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.static_storyboard.emit import (
    REVIEW_MANIFEST_FILENAME,
    emit,
    materialize_source,
    review_manifest,
    scene_cards,
    source_for,
    source_tree,
    storyboard_markdown,
)
from viroc.core import BuildArtifact, BuildContext, Diagnostic, build_manifest, write_manifest
from viroc.ir import Caption, ConcreteIR

id = "static_storyboard"
version = "0.1"
source_filename = "storyboard.md"

SUPPORTED_PRIMITIVES = frozenset({"arrow", "code", "formula", "icon", "rect", "text"})
SUPPORTED_ANIMATIONS = frozenset({"draw", "fade_in", "fade_out", "highlight"})
capabilities = CapabilityManifest(
    primitives=SUPPORTED_PRIMITIVES,
    animations=SUPPORTED_ANIMATIONS,
)


def check_environment(ctx: BuildContext) -> list[Diagnostic]:
    """Review compilation has no required external toolchain."""
    _ = ctx
    return []


def supports(ir: ConcreteIR) -> list[Diagnostic]:
    """Return renderer-compatibility diagnostics for unsupported Concrete IR."""
    return support_diagnostics(
        id,
        capabilities,
        ir,
        primitive_fallback_backends=(
            "html",
            "image_sequence",
            "motion_canvas",
            "remotion",
            "manim",
        ),
    )


def render(
    source: BuildArtifact,
    ctx: BuildContext,
    *,
    captions: Iterable[Caption] = (),
) -> BuildArtifact:
    """Materialize deterministic review artifacts and write a review manifest."""
    _ = captions
    if source.path is not None and source.path.is_dir():
        artifact = BuildArtifact(kind=source.kind, digest=source.digest, path=source.path)
    else:
        destination = ctx.paths.out_dir / "generated" / id
        artifact = materialize_source(source, destination)
    root = artifact.path
    assert root is not None
    cards_path = root / "scene-cards.json"
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    max_end = max((float(card["end_seconds"]) for card in cards), default=1.0)
    manifest = build_manifest(
        project=ctx.config.get("project", ctx.paths.project_root.name),
        source_hash=artifact.digest,
        asset_hashes={},
        renderer_id=id,
        renderer_version=version,
        perceptual_hash=f"phash:{artifact.digest.split(':', 1)[1][:16]}",
        duration_seconds=max_end,
        vidir_version=ctx.config.get("vidir_version", "0.1"),
    )
    write_manifest(manifest, ctx.paths.out_dir / "build.json")
    return BuildArtifact(kind="video", digest=artifact.digest, path=root / "storyboard.md")


def materialize_review(source: BuildArtifact, destination: Path) -> BuildArtifact:
    """Write the review artifact tree plus the deterministic review manifest.

    Unlike :func:`render`, this is the dedicated critique review surface: it
    materializes the artifact tree and a ``review-manifest.json`` linking each
    artifact to its content hash, without writing the build manifest.
    """
    artifact = materialize_source(source, destination)
    root = artifact.path
    assert root is not None
    (root / REVIEW_MANIFEST_FILENAME).write_text(review_manifest(source), encoding="utf-8")
    return artifact


def invalidate_review(destination: Path) -> None:
    """Remove a stale review directory so failed validation leaves no fresh outputs."""
    if destination.exists():
        shutil.rmtree(destination)


__all__ = [
    "REVIEW_MANIFEST_FILENAME",
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "check_environment",
    "emit",
    "id",
    "invalidate_review",
    "materialize_review",
    "materialize_source",
    "render",
    "review_manifest",
    "scene_cards",
    "source_filename",
    "source_for",
    "source_tree",
    "storyboard_markdown",
    "supports",
    "version",
]
