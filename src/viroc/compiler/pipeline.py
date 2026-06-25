"""Compiler pipeline driver — phases P3 and P4 (design §3).

The full pipeline runs P1..P13; this module wires the first two pure post-parse
phases in order:

- **P3 normalize** — canonicalize the Semantic IR (stable ids, defaults).
- **P4 resolve + hash assets** — resolve every referenced asset and hash it,
  collecting VIR4xxx diagnostics for any that are missing or unreadable.

Ordering is the contract: normalize runs before asset resolution. Later phases
(P5 grammar expansion, P6/P7 layout + timeline resolve, P8 Concrete IR assembly)
are added in M6/M7; once grammar expansion produces asset-bearing objects, the
asset references will be collected from them rather than supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from viroc.compiler.assets import ResolvedAsset, resolve_assets
from viroc.compiler.normalize import normalize
from viroc.core import BuildContext, Diagnostic
from viroc.ir import SemanticIR


@dataclass(frozen=True, slots=True)
class CompileState:
    """The accumulated result of the pipeline phases run so far.

    ``ir`` is the normalized Semantic IR (P3); ``assets`` are the resolved,
    hashed assets (P4); ``diagnostics`` aggregates every diagnostic emitted by
    the phases that have run.
    """

    ir: SemanticIR
    assets: list[ResolvedAsset] = field(default_factory=list[ResolvedAsset])
    diagnostics: list[Diagnostic] = field(default_factory=list[Diagnostic])


def run_pipeline(
    ir: SemanticIR, ctx: BuildContext, *, asset_refs: Iterable[str] = ()
) -> CompileState:
    """Run phases P3 (normalize) then P4 (resolve + hash assets), in order.

    Returns a :class:`CompileState` carrying the normalized IR, the resolved
    assets, and any VIR4xxx asset diagnostics. The normalize step is pure and
    contributes no diagnostics; aggregation will grow as later phases land.
    """
    normalized = normalize(ir)
    resolved, diagnostics = resolve_assets(asset_refs, ctx)
    return CompileState(ir=normalized, assets=resolved, diagnostics=diagnostics)
