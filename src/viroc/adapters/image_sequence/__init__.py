"""Image-sequence review adapter: deterministic frame plans and review artifacts."""

from __future__ import annotations

import json
from collections.abc import Iterable

from viroc.adapters.capabilities import (
    VIR_UNSUPPORTED_ANIMATION,
    VIR_UNSUPPORTED_PRIMITIVE,
    CapabilityManifest,
    support_diagnostics,
)
from viroc.adapters.image_sequence.emit import (
    emit,
    frame_plan,
    materialize_source,
    source_for,
    source_tree,
    total_frames,
)
from viroc.core import BuildArtifact, BuildContext, Diagnostic, build_manifest, write_manifest
from viroc.ir import Caption, ConcreteIR

id = "image_sequence"
version = "0.1"
source_filename = "frame-plan.json"

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
        primitive_fallback_backends=("html", "motion_canvas", "remotion", "manim"),
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
    plan_path = root / "frame-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    duration_seconds = float(plan["total_frames"]) / float(plan["fps"])
    manifest = build_manifest(
        project=ctx.config.get("project", ctx.paths.project_root.name),
        source_hash=artifact.digest,
        asset_hashes={},
        renderer_id=id,
        renderer_version=version,
        perceptual_hash=f"phash:{artifact.digest.split(':', 1)[1][:16]}",
        duration_seconds=max(duration_seconds, 1 / max(int(plan["fps"]), 1)),
        vidir_version=ctx.config.get("vidir_version", "0.1"),
    )
    write_manifest(manifest, ctx.paths.out_dir / "build.json")
    return BuildArtifact(kind="video", digest=artifact.digest, path=plan_path)


__all__ = [
    "SUPPORTED_ANIMATIONS",
    "SUPPORTED_PRIMITIVES",
    "VIR_UNSUPPORTED_ANIMATION",
    "VIR_UNSUPPORTED_PRIMITIVE",
    "capabilities",
    "check_environment",
    "emit",
    "frame_plan",
    "id",
    "materialize_source",
    "render",
    "source_filename",
    "source_for",
    "source_tree",
    "supports",
    "total_frames",
    "version",
]
