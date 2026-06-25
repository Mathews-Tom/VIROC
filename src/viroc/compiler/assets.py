"""Asset resolution and hashing (pipeline phase P4).

Every asset a storyboard references must be resolved against the project root and
content-hashed, so its ``sha256:`` digest can land in the build manifest as part
of the reproducibility key (overview §9.3, design §3 P4). The hash is stable: the
same file always yields the same digest across runs and machines.

A reference that does not resolve is not silently skipped — a missing asset
becomes ``VIR4001`` and an unreadable one (a directory, a permission error)
becomes ``VIR4002``, so a broken render surfaces as a typed diagnostic rather
than a confusing downstream failure.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from viroc.core import BuildContext, Diagnostic, DiagnosticClass, code, hash_bytes

VIR_ASSET_MISSING = code(DiagnosticClass.ASSET, 1)
"""An asset reference does not resolve to an existing file."""

VIR_ASSET_UNREADABLE = code(DiagnosticClass.ASSET, 2)
"""An asset reference resolves but cannot be read (a directory, a bad mode)."""


@dataclass(frozen=True, slots=True)
class ResolvedAsset:
    """A resolved asset reference paired with its content digest.

    ``ref`` is the reference as authored; ``path`` is where it resolved; ``digest``
    is the ``sha256:`` hash of the file's bytes.
    """

    ref: str
    path: Path
    digest: str


def resolve_asset(ref: str, ctx: BuildContext) -> ResolvedAsset | Diagnostic:
    """Resolve one asset ``ref`` against the project root and hash its bytes.

    Returns a :class:`ResolvedAsset` on success, or a ``VIR4xxx`` diagnostic when
    the reference is missing (``VIR4001``) or unreadable (``VIR4002``).
    """
    path = ctx.paths.project_root / ref
    if not path.exists():
        return Diagnostic(
            code=VIR_ASSET_MISSING,
            message=f'asset "{ref}" not found',
            help=f"expected a file at {path}",
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        return Diagnostic(
            code=VIR_ASSET_UNREADABLE,
            message=f'asset "{ref}" is unreadable',
            help=f"{path}: {exc.strerror or exc}",
        )
    return ResolvedAsset(ref=ref, path=path, digest=hash_bytes(data))


def resolve_assets(
    refs: Iterable[str], ctx: BuildContext
) -> tuple[list[ResolvedAsset], list[Diagnostic]]:
    """Resolve and hash every reference, partitioning successes from diagnostics.

    Input order is preserved in both returned lists.
    """
    resolved: list[ResolvedAsset] = []
    diagnostics: list[Diagnostic] = []
    for ref in refs:
        outcome = resolve_asset(ref, ctx)
        if isinstance(outcome, Diagnostic):
            diagnostics.append(outcome)
        else:
            resolved.append(outcome)
    return resolved, diagnostics


def asset_hashes(resolved: Iterable[ResolvedAsset]) -> dict[str, str]:
    """Map each resolved asset's reference to its digest, for the manifest."""
    return {asset.ref: asset.digest for asset in resolved}
