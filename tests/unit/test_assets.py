"""Asset resolution and hashing (M5).

Covers the design §3 P4 contract: a present asset hashes to a stable ``sha256:``
digest, a missing asset becomes ``VIR4001``, an unreadable one ``VIR4002``, and a
batch cleanly partitions successes from diagnostics.
"""

from __future__ import annotations

from pathlib import Path

from viroc.compiler.assets import (
    VIR_ASSET_MISSING,
    VIR_ASSET_UNREADABLE,
    ResolvedAsset,
    asset_hashes,
    resolve_asset,
    resolve_assets,
)
from viroc.core import BuildContext, BuildPaths, Diagnostic, hash_bytes


def _ctx(root: Path) -> BuildContext:
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def test_asset_codes_are_in_the_vir4_range() -> None:
    """The asset diagnostics live in the VIR4xxx (assets) range."""
    assert VIR_ASSET_MISSING == "VIR4001"
    assert VIR_ASSET_UNREADABLE == "VIR4002"


def test_present_asset_hashes_stably(tmp_path: Path) -> None:
    """A present asset resolves to a sha256 digest of its bytes, stable across calls."""
    content = b"\x89PNG fake bytes"
    (tmp_path / "logo.png").write_bytes(content)
    ctx = _ctx(tmp_path)

    first = resolve_asset("logo.png", ctx)
    second = resolve_asset("logo.png", ctx)

    assert isinstance(first, ResolvedAsset)
    assert isinstance(second, ResolvedAsset)
    assert first.ref == "logo.png"
    assert first.path == tmp_path / "logo.png"
    assert first.digest == hash_bytes(content)
    assert first.digest.startswith("sha256:")
    assert first.digest == second.digest


def test_missing_asset_is_vir4001(tmp_path: Path) -> None:
    """An asset reference with no file behind it yields VIR4001."""
    outcome = resolve_asset("missing.png", _ctx(tmp_path))
    assert isinstance(outcome, Diagnostic)
    assert outcome.code == VIR_ASSET_MISSING
    assert outcome.help is not None and "missing.png" in outcome.help


def test_unreadable_asset_is_vir4002(tmp_path: Path) -> None:
    """A reference that resolves to a directory cannot be read: VIR4002."""
    (tmp_path / "assets").mkdir()
    outcome = resolve_asset("assets", _ctx(tmp_path))
    assert isinstance(outcome, Diagnostic)
    assert outcome.code == VIR_ASSET_UNREADABLE


def test_resolve_assets_partitions_and_preserves_order(tmp_path: Path) -> None:
    """A batch keeps successes and diagnostics separate, in input order."""
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "b.png").write_bytes(b"b")
    ctx = _ctx(tmp_path)

    resolved, diagnostics = resolve_assets(["a.png", "gone.png", "b.png"], ctx)

    assert [asset.ref for asset in resolved] == ["a.png", "b.png"]
    assert [diag.code for diag in diagnostics] == [VIR_ASSET_MISSING]


def test_asset_hashes_maps_ref_to_digest(tmp_path: Path) -> None:
    """asset_hashes projects resolved assets into the manifest mapping."""
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "b.png").write_bytes(b"b")
    resolved, _ = resolve_assets(["a.png", "b.png"], _ctx(tmp_path))

    mapping = asset_hashes(resolved)

    assert mapping == {"a.png": hash_bytes(b"a"), "b.png": hash_bytes(b"b")}
