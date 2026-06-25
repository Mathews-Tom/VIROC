"""Build manifest provenance and VIR7 reproducibility checks."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from viroc.core.manifest import (
    VIR_ASSET_HASH_MISMATCH,
    VIR_RENDERER_VERSION_MISMATCH,
    VIR_SOURCE_HASH_MISMATCH,
    BuildManifest,
    build_manifest,
    manifest_json,
    validate_reproducibility,
)

_SOURCE_HASH = "sha256:" + "a" * 64
_ASSET_HASH = "sha256:" + "b" * 64
_OTHER_HASH = "sha256:" + "c" * 64
_PHASH = "phash:0123456789abcdef"
_CREATED_AT = datetime(2026, 6, 24, tzinfo=UTC)


def _manifest() -> BuildManifest:
    return build_manifest(
        project="rag-overview",
        source_hash=_SOURCE_HASH,
        asset_hashes={"assets/doc.svg": _ASSET_HASH},
        renderer_id="manim",
        renderer_version="0.20.1",
        perceptual_hash=_PHASH,
        duration_seconds=91.4,
        created_at=_CREATED_AT,
    )


def test_manifest_schema_matches_overview_fields() -> None:
    manifest = _manifest()

    assert manifest.project == "rag-overview"
    assert manifest.viroc_version == "0.1.0"
    assert manifest.vidir_version == "0.1"
    assert manifest.source_hash == _SOURCE_HASH
    assert manifest.asset_hashes == {"assets/doc.svg": _ASSET_HASH}
    assert manifest.renderer.id == "manim"
    assert manifest.renderer.version == "0.20.1"
    assert manifest.perceptual_hash == _PHASH
    assert manifest.duration_seconds == 91.4
    assert manifest.created_at == _CREATED_AT


def test_manifest_json_is_stable_and_uses_utc_z_timestamp() -> None:
    first = manifest_json(_manifest())
    second = manifest_json(_manifest())

    assert first == second
    assert f'"source_hash":"{_SOURCE_HASH}"' in first
    assert f'"asset_hashes":{{"assets/doc.svg":"{_ASSET_HASH}"}}' in first
    assert '"created_at":"2026-06-24T00:00:00Z"' in first


def test_manifest_rejects_unknown_fields() -> None:
    data = _manifest().model_dump(mode="json")
    data["unexpected"] = True

    with pytest.raises(ValidationError):
        BuildManifest.model_validate(data)


def test_validate_reproducibility_accepts_matching_provenance() -> None:
    assert validate_reproducibility(
        _manifest(),
        source_hash=_SOURCE_HASH,
        asset_hashes={"assets/doc.svg": _ASSET_HASH},
        renderer_id="manim",
        renderer_version="0.20.1",
    ) == []


def test_validate_reproducibility_reports_vir7xxx_mismatches() -> None:
    diagnostics = validate_reproducibility(
        _manifest(),
        source_hash=_OTHER_HASH,
        asset_hashes={"assets/doc.svg": _OTHER_HASH},
        renderer_id="manim",
        renderer_version="0.19.0",
    )

    assert [diagnostic.code for diagnostic in diagnostics] == [
        VIR_SOURCE_HASH_MISMATCH,
        VIR_ASSET_HASH_MISMATCH,
        VIR_RENDERER_VERSION_MISMATCH,
    ]
    assert diagnostics[0].code == "VIR7001"
    assert diagnostics[1].code == "VIR7002"
    assert diagnostics[2].code == "VIR7003"


def test_build_manifest_rejects_invalid_hashes() -> None:
    with pytest.raises(ValueError, match="source_hash"):
        build_manifest(
            project="rag-overview",
            source_hash="sha256:not-hex",
            asset_hashes={},
            renderer_id="manim",
            renderer_version="0.20.1",
            perceptual_hash=_PHASH,
            duration_seconds=1.0,
        )
