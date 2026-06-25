"""Compiler pipeline driver — phases P3 through P6 (design §3).

The full pipeline runs P1..P13; this module wires the pure post-parse phases in
order:

- **P3 normalize** — canonicalize the Semantic IR (stable ids, defaults).
- **P4 resolve + hash assets** — resolve every referenced asset and hash it,
  collecting VIR4xxx diagnostics for any that are missing or unreadable.
- **P5 grammar expansion + P6 layout resolve** — for each scene, expand it with
  its grammar and lay the abstract objects out into resolved boxes.

Ordering is the contract: normalize runs first, then asset resolution, then
layout over the normalized IR. Later phases (P7 timeline resolve, P8 Concrete IR
assembly) land in M7; once grammar expansion produces asset-bearing objects, the
asset references will be collected from them rather than supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from viroc.compiler.assets import ResolvedAsset, resolve_assets
from viroc.compiler.normalize import normalize
from viroc.compiler.resolve_layout import resolve_layout
from viroc.core import BuildContext, Diagnostic
from viroc.ir import ResolvedObject, SemanticIR


@dataclass(frozen=True, slots=True)
class CompileState:
    """The accumulated result of the pipeline phases run so far.

    ``ir`` is the normalized Semantic IR (P3); ``assets`` are the resolved,
    hashed assets (P4); ``objects`` are the resolved layout boxes for every scene
    (P5+P6); ``diagnostics`` aggregates every diagnostic emitted by the phases
    that have run.
    """

    ir: SemanticIR
    assets: list[ResolvedAsset] = field(default_factory=list[ResolvedAsset])
    objects: list[ResolvedObject] = field(default_factory=list[ResolvedObject])
    diagnostics: list[Diagnostic] = field(default_factory=list[Diagnostic])


def run_pipeline(
    ir: SemanticIR, ctx: BuildContext, *, asset_refs: Iterable[str] = ()
) -> CompileState:
    """Run phases P3 (normalize), P4 (assets), then P5+P6 (expand + layout).

    Returns a :class:`CompileState` carrying the normalized IR, the resolved
    assets and their VIR4xxx diagnostics, and the resolved layout boxes for every
    scene. Layout runs over the normalized IR so ids and references are canonical.
    Aggregation will grow as later phases land.
    """
    normalized = normalize(ir)
    resolved, diagnostics = resolve_assets(asset_refs, ctx)
    objects: list[ResolvedObject] = []
    for scene in normalized.scenes:
        objects.extend(resolve_layout(scene, normalized, ctx))
    return CompileState(
        ir=normalized, assets=resolved, objects=objects, diagnostics=diagnostics
    )
