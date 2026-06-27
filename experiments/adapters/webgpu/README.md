# WebGPU / native vector — boundary analysis

**Class:** render platform.
**Targets covered:** `.docs/viroc-draft.md` §4.3 "WebGPU backend" **and** "native
vector backend" — both collapse onto the same boundary question, so they are
evaluated together here.
**Probe:** documentation-only (no dependency-light deterministic *source* emit to
prototype; the analysis is the deliverable).

## The boundary question

ADR-0002 requires every backend to emit a deterministic, dependency-light
*source* artifact; pixels are produced in an env-gated render step. The test for a
new render-platform target is therefore: **is there a distinct, byte-deterministic
source emit that this target uniquely needs?**

## WebGPU

WebGPU is a *GPU API*, not a source format. There are two ways it could enter
VIROC, and neither is a clean new emit target:

| Path | What VIROC would emit | Verdict |
|---|---|---|
| (a) Runtime over an existing export | nothing new — WebGPU is the browser's renderer for the **interactive web** bundle | not a new target; it is a runtime detail of `../interactive_web/` |
| (b) Dedicated WebGPU backend | WGSL shaders + a JS harness as source | deterministic *source* is possible, but… |

Path (b) emitting WGSL+JS *could* be byte-deterministic, but it:

* **duplicates** the interactive-web target at a large complexity premium, for
  content (boxes, arrows, text, simple tweens) that needs no GPU compute;
* pushes render even **further** into environment variance — GPU drivers, adapter
  limits, and float precision differ per machine, widening the perceptual gap
  ADR-0002 already accepts;
* moves VIROC toward *owning a renderer*, against §4.3 ("compile into renderer
  frameworks; do not compete with them").

Conceptual emit shape, for the record:

```text
Concrete IR --(deterministic)--> { scene.wgsl, harness.js, geometry.json }
            --(GPU, env-gated)--> pixels   # even more env-variable than canvas
```

## Native vector backend

"Native vector" means a platform vector renderer (Skia/Cairo/native canvas). Its
*source* emit is a vector scene description — which for the web is **SVG**, already
owned by the HTML adapter, and the interactive-web bundle already emits inline
SVG. So a native-vector target is either:

* SVG output (already covered, no new deterministic target), or
* VIROC shipping/embedding a native renderer (against the compile-into-frameworks
  strategy, and not dependency-light).

There is no distinct deterministic emit that native-vector uniquely requires.

## Decision

* **WebGPU backend = NO-GO.** Either a runtime detail of interactive web (path a)
  or a high-complexity duplicate with worse render determinism (path b). No unique
  deterministic source emit; nudges VIROC into owning a renderer.
* **native vector backend = NO-GO.** Its deterministic source emit is SVG, already
  covered by the HTML / interactive-web targets.

Re-evaluate only if a future showcase needs GPU-only effects (shaders, particle
systems) that the SVG/canvas floor genuinely cannot express — at which point it
would extend interactive web, not become a separate emit target.
