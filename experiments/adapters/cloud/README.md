# Cloud rendering — boundary analysis

**Class:** render platform.
**Target:** `.docs/viroc-draft.md` §4.3 "cloud rendering backend".
**Probe:** documentation-only (cloud rendering is not a source-emit target, so
there is nothing to prototype deterministically; the analysis is the deliverable).

## Cloud rendering is already on the render side of the boundary

ADR-0002 splits the guarantee at emit: compile/emit is byte-deterministic and
local; **render is environment-dependent and perceptual**. "Cloud rendering" means
running an existing adapter's `render()` on remote infrastructure instead of the
local machine. That is purely a question of *where `render()` runs* — and `render()`
is already defined to be impure and env-gated:

```python
# src/viroc/adapters/__init__.py (RendererAdapter protocol)
def emit(self, ir: ConcreteIR, ctx: BuildContext) -> BuildArtifact:
    """Lower Concrete IR to byte-deterministic backend source without I/O."""

def render(self, source: BuildArtifact, ctx: BuildContext, *, captions=...) -> BuildArtifact:
    """Invoke the backend and return the rendered video artifact."""  # env-gated
```

A cloud renderer changes nothing left of `render()`: the same deterministic
`source` (and its `source_hash`) is produced locally, shipped, and rendered
remotely. Reproducibility is preserved because the manifest already records
renderer versions + perceptual hashes; a remote render is verified the same way as
a local one.

## Why it is not an M21 GO target

* **Not a renderer target.** It introduces no new Concrete IR primitive, no new
  emit, and no new adapter — it is an *orchestration layer* over the existing
  adapters' `render()`.
* **Requires SaaS credentials.** Any real cloud backend needs provider
  credentials and network access at render time — explicitly out of M21 scope, and
  it must never become a compile-time (left-of-emit) dependency.
* **Buildable out of tree, zero core dependency.** Because the emit boundary
  already isolates determinism, a cloud orchestrator can live entirely outside
  `viroc` (a CI job or service that calls `viroc compile` locally, then runs
  `render()` on a worker). The core package needs no change.

Conceptual orchestration sketch (out-of-tree, no core dependency):

```text
local:  viroc compile  -> source artifact (+ source_hash)   # deterministic
ship:   upload source artifact to a worker
worker: adapter.render(source, ctx)  -> video (+ perceptual hash)   # env-gated
verify: compare perceptual hash to baseline (existing manifest flow)
```

## Decision

**NO-GO** as a renderer/emit target. Cloud rendering is a deployment pattern over
the existing env-gated `render()`, not a new backend; it preserves the determinism
boundary precisely because it lives entirely to the right of it. If pursued, it
belongs in an out-of-tree orchestrator (CI/service), never as a core dependency or
a Concrete IR change.
