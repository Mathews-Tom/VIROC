"""Build manifest provenance and VIR7 reproducibility checks."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from viroc import __version__
from viroc.core.diagnostics import Diagnostic, DiagnosticClass, code
from viroc.core.hashing import canonical_json

VIR_SOURCE_HASH_MISMATCH = code(DiagnosticClass.REPRODUCIBILITY, 1)
VIR_ASSET_HASH_MISMATCH = code(DiagnosticClass.REPRODUCIBILITY, 2)
VIR_RENDERER_VERSION_MISMATCH = code(DiagnosticClass.REPRODUCIBILITY, 3)

_SHA256_PREFIX = "sha256:"
_PHASH_PREFIX = "phash:"
_DEFAULT_VIDIR_VERSION = "0.1"


class _Model(BaseModel):
    """Strict manifest model base; unknown provenance fields are invalid."""

    model_config = ConfigDict(extra="forbid")


class RendererManifest(_Model):
    """Renderer identity captured in the build manifest."""

    id: str
    version: str


class BuildManifest(_Model):
    """Build manifest schema from overview §9.3."""

    project: str
    viroc_version: str
    vidir_version: str
    source_hash: str
    asset_hashes: dict[str, str]
    renderer: RendererManifest
    perceptual_hash: str
    duration_seconds: float
    created_at: datetime


def build_manifest(
    *,
    project: str,
    source_hash: str,
    asset_hashes: dict[str, str],
    renderer_id: str,
    renderer_version: str,
    perceptual_hash: str,
    duration_seconds: float,
    vidir_version: str = _DEFAULT_VIDIR_VERSION,
    viroc_version: str = __version__,
    created_at: datetime | None = None,
) -> BuildManifest:
    """Construct and validate a provenance manifest."""
    _require_sha256(source_hash, "source_hash")
    for ref, digest in asset_hashes.items():
        _require_sha256(digest, f"asset_hashes[{ref!r}]")
    _require_phash(perceptual_hash)
    if duration_seconds <= 0:
        raise ValueError(f"duration_seconds must be positive, got {duration_seconds}")
    return BuildManifest(
        project=project,
        viroc_version=viroc_version,
        vidir_version=vidir_version,
        source_hash=source_hash,
        asset_hashes=dict(sorted(asset_hashes.items())),
        renderer=RendererManifest(id=renderer_id, version=renderer_version),
        perceptual_hash=perceptual_hash,
        duration_seconds=duration_seconds,
        created_at=created_at if created_at is not None else _created_at(),
    )


def manifest_json(manifest: BuildManifest) -> str:
    """Serialize a manifest as stable canonical JSON with a trailing newline."""
    data = manifest.model_dump(mode="json")
    data["created_at"] = _format_timestamp(manifest.created_at)
    return f"{canonical_json(data)}\n"


def write_manifest(manifest: BuildManifest, path: Path) -> Path:
    """Write ``build.json`` content for ``manifest`` and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest_json(manifest), encoding="utf-8")
    return path


def validate_reproducibility(
    manifest: BuildManifest,
    *,
    source_hash: str | None = None,
    asset_hashes: dict[str, str] | None = None,
    renderer_id: str | None = None,
    renderer_version: str | None = None,
) -> list[Diagnostic]:
    """Return VIR7xxx diagnostics for provenance mismatches."""
    diagnostics: list[Diagnostic] = []
    if source_hash is not None and manifest.source_hash != source_hash:
        diagnostics.append(
            Diagnostic(
                code=VIR_SOURCE_HASH_MISMATCH,
                message="manifest source hash does not match generated source",
                help=f"expected {source_hash}, got {manifest.source_hash}",
            )
        )
    if asset_hashes is not None and manifest.asset_hashes != dict(sorted(asset_hashes.items())):
        diagnostics.append(
            Diagnostic(
                code=VIR_ASSET_HASH_MISMATCH,
                message="manifest asset hashes do not match resolved assets",
                help=_asset_diff_help(manifest.asset_hashes, asset_hashes),
            )
        )
    if renderer_id is not None and manifest.renderer.id != renderer_id:
        diagnostics.append(
            Diagnostic(
                code=VIR_RENDERER_VERSION_MISMATCH,
                message="manifest renderer id does not match selected renderer",
                help=f"expected {renderer_id}, got {manifest.renderer.id}",
            )
        )
    if renderer_version is not None and manifest.renderer.version != renderer_version:
        diagnostics.append(
            Diagnostic(
                code=VIR_RENDERER_VERSION_MISMATCH,
                message="manifest renderer version does not match pinned version",
                help=f"expected {renderer_version}, got {manifest.renderer.version}",
            )
        )
    return diagnostics


def _asset_diff_help(actual: dict[str, str], expected: dict[str, str]) -> str:
    actual_keys = set(actual)
    expected_keys = set(expected)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    changed = sorted(key for key in actual_keys & expected_keys if actual[key] != expected[key])
    parts: list[str] = []
    if missing:
        parts.append(f"missing: {', '.join(missing)}")
    if extra:
        parts.append(f"extra: {', '.join(extra)}")
    if changed:
        parts.append(f"changed: {', '.join(changed)}")
    return "; ".join(parts) if parts else "asset hash ordering differs"


def _require_sha256(value: str, field: str) -> None:
    if not value.startswith(_SHA256_PREFIX):
        raise ValueError(f"{field} must start with {_SHA256_PREFIX!r}")
    payload = value.removeprefix(_SHA256_PREFIX)
    if len(payload) != 64:
        raise ValueError(f"{field} must contain 64 hex characters")
    int(payload, 16)


def _require_phash(value: str) -> None:
    if not value.startswith(_PHASH_PREFIX):
        raise ValueError(f"perceptual_hash must start with {_PHASH_PREFIX!r}")
    parts = value.removeprefix(_PHASH_PREFIX).split("-")
    if not parts or any(len(part) != 16 for part in parts):
        raise ValueError("perceptual_hash must contain one or more 64-bit frame hashes")
    for part in parts:
        int(part, 16)


def _created_at() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


__all__ = [
    "BuildManifest",
    "RendererManifest",
    "VIR_ASSET_HASH_MISMATCH",
    "VIR_RENDERER_VERSION_MISMATCH",
    "VIR_SOURCE_HASH_MISMATCH",
    "build_manifest",
    "manifest_json",
    "validate_reproducibility",
    "write_manifest",
]
