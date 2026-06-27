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
* **native vector backend = NO-GO as an embedded renderer.** VIROC must not own a
  renderer. But its deterministic source emit *is* SVG, and that is now a
  first-class deliverable: see the **SVG export consolidation** remediation in
  `../svg/` (doc §3, Option A) — native vector is **GO as SVG export**, NO-GO as an
  embedded renderer.

Re-evaluate only if a future showcase needs GPU-only effects (shaders, particle
systems) that the SVG/canvas floor genuinely cannot express — at which point it
would extend interactive web, not become a separate emit target.

## I2.1 — GPU-only requirement inventory (executed)

Per `.docs/2026-06-27-no-go-renderer-remediation.md` §2, WebGPU flips to GO **only**
as a render mode inside interactive web, and **only if** I2.1 surfaces a concrete
GPU-only effect the SVG/canvas floor cannot meet. I2.1 inventories every planned
showcase against that bar:

| Source | Content | GPU-only effect? |
|---|---|---|
| Concrete IR vocabulary (`ir/concrete.py`) | primitives `text`/`rect`/`icon`/`arrow`/`code`/`formula`; keyframes `fade_in`/`draw`/`move`/`highlight`/`fade_out`; easings `linear`/`ease_in_out`/`spring` | none — diagram primitives + simple tweens |
| `tests/fixtures/rag-overview.vidir.yaml` | 5 entities, `pipeline` grammar, fade/draw/transform tweens | no |
| `tests/fixtures/showcase-composition.vidir.yaml` | 12 entities across 3 scenes (`panels`, fan-out, comparison), `showcase` grammar | no |
| `experiments/adapters/_sample.py` | full-vocabulary sample (9 objects, 10 keyframes, all easings) | no |

No showcase needs custom shaders, particle systems, or thousands of animated nodes.
Node counts are tiny (≤12), and the interactive-web SVG/canvas floor already covers
the **entire** keyframe vocabulary natively (`interactive_web/export.py`:
`unsupported_keyframes` is empty) at trivial frame cost. There is therefore no
motivating GPU-only use case — the I2.1 gate is **negative**.

## Decision (WebGPU) — confirmed by I2.1

WebGPU stays **NO-GO**. I2.1 found no GPU-only requirement, so the Option-A WebGPU
render mode is **not** built (it would be a renderer with no content to justify it,
and would worsen render determinism — ADR-0002). No WebGPU viewer mode is added;
the deterministic `interactive_web/` `timeline.json` emit is unchanged. Re-open I2.1
only when a concrete GPU-only effect appears, at which point it extends interactive
web (Option A), never a separate emit target (Option B stays rejected).
