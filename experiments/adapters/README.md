# M21 — Future/export adapter feasibility

> Feasibility gate, **not** a production adapter. Nothing here is imported by
> `viroc` or by the conformance suite, and nothing here adds a dependency to the
> core package (DEVELOPMENT_PLAN.md §4 M21; `.docs/viroc-draft.md` §4.3).

## Why this exists

`.docs/viroc-draft.md` §4.3 names five *future* renderer targets beyond the six
built-in adapters (Manim, HTML, Remotion, Motion Canvas, image-sequence, static
storyboard):

* native vector backend
* WebGPU backend
* Rive/Lottie export backend
* cloud rendering backend
* interactive web export backend

M21 turns each one into an explicit **GO / NO-GO** decision *against the same
determinism boundary as the production adapters* — it does not build any of them
as a production backend. The decisions are recorded in `RESULTS.md` and promoted
to `.docs/adr/0004-future-renderer-targets.md`.

## The bar every target is held to

ADR-0002 splits VIROC's guarantee at the emit boundary:

* **Compile/emit is byte-deterministic** — `Concrete IR + viroc version` lowers to
  byte-identical backend *source*, hashed as `source_hash`. No environment access
  left of "render".
* **Render is perceptually stable, never bit-exact** — it runs in a pinned,
  environment-gated step to the *right* of emit.

A target is a **GO** only if it preserves that boundary: a deterministic,
dependency-light *source* emit, with render execution kept env-gated. A target
that forces non-determinism into emit, requires SaaS credentials at compile time,
or demands a Concrete IR change to chase one renderer is a **NO-GO** (M21 out of
scope).

## Layout

```
experiments/adapters/
  _sample.py            # shared, deterministic sample Concrete IR (full vocabulary)
  RESULTS.md            # capability maps + one DECISION line per target
  lottie/               # export-format probe: Concrete IR -> Lottie JSON (prototype)
  rive/                 # export-format probe: Rive capability map + sketch
  webgpu/               # render-platform probe: WebGPU / native vector analysis
  cloud/                # render-platform probe: cloud rendering boundary analysis
  interactive_web/      # render-platform probe: interactive web export (prototype)
```

Each probe directory carries a `README.md` capability map. Probes with a
dependency-light deterministic emit (`lottie`, `interactive_web`) also ship a
runnable prototype module and a determinism test.

## Running the probes

These files live outside the gated tree (`pyproject.toml` excludes
`experiments/` from ruff, pyright, and the default `pytest` testpaths), so they
never affect `uv run pytest -q`. Run them explicitly:

```bash
# deterministic-export prototypes + their byte-stability tests
uv run pytest experiments/adapters -q
```

Tests that need an optional third-party validator (e.g. `python-lottie`) **skip
cleanly** when it is absent — no probe requires an external tool or credential to
prove byte-determinism.
