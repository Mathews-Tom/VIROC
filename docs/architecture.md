# VIROC — Architecture

Implementation-facing companion to `design.md`. `design.md` is the normative reference; this document orients a contributor to the package layout and the boundaries each milestone fills in. Sections marked _(forthcoming)_ are scaffolds whose detail lands with the milestone that owns the code.

## The spine

VIROC compiles a hand-authored **Semantic IR (VidIR)** through a layout/timing **Resolver** into a **Concrete IR**, validates it, lowers it to backend source, and renders. The primary artifact is the typed, diffable storyboard; the video is a build output.

```
Semantic IR ──▶ normalize ──▶ grammar expand ──▶ resolve (layout + time)
            ──▶ Concrete IR ──▶ validate ──▶ adapter emit ──▶ render ──▶ artifacts
```

Phases left of *render* are a pure function; render is the only environment-dependent stage. See `design.md` §1, §3.

## The two boundaries that matter

- **Semantic IR ↔ Concrete IR** — portability lives above, visual fidelity below. The Resolver is the lowering between them and is where the hard work (layout + timing) lives. See ADR-0001.
- **Compile ↔ render** — the compile is byte-deterministic and the real reproducibility guarantee (`source_hash`); the render is only perceptually stable. No environment access leaks left of *render*. See ADR-0002 and `overview.md` §3.2.

## Package layout

```
src/viroc/
  core/        # ids, hashing, diagnostics, build context
  ir/          # semantic.py (VidIR), concrete.py, io
  compiler/    # normalize, assets, resolve_layout, resolve_time, pipeline
  grammars/    # plugin contract + registry
    pipeline/  # the one v1 grammar: expand, layout, animate
  adapters/    # renderer adapter contract
    manim/     # emit (pure), render (impure), templates
  validators/  # schema (pre), layout + timing (post)
  cli/         # init, check, compile, render, graph, doctor
tests/
  unit/ integration/ golden/
```

This mirrors `design.md` §7. Each subpackage is an importable namespace today; behavior arrives with its milestone.

## Diagnostics

A single compiler-grade diagnostic surface (code + span + `help:`) with stable `VIRxxxx` code ranges (`design.md` §5.2, `overview.md` §9.2). The registry and renderer are introduced with the core-primitives milestone.

## Determinism contract

`Semantic IR + config + viroc version + grammar version` → **byte-identical** generated source; pinned-environment render → **perceptually stable** pixels, verified by perceptual hash, never bit-exact. See ADR-0002.

## Cross-references

- `overview.md` — product framing, risks, v1 scope.
- `design.md` — normative architecture, the two-level IR, the pipeline, the adapter contract, validation.
- `vidir-spec.md` — the Semantic IR surface authors write.
- `grammar-authoring.md` — the grammar plugin contract.
