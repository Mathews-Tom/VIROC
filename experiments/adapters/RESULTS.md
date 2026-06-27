# Future/export adapter feasibility — results

Applies the M21 feasibility bar (see `README.md`) to every future renderer target
named in `.docs/viroc-draft.md` §4.3. Every decision below is backed by a
capability map against the shared sample Concrete IR (`_sample.py`) and an
analysis of the target against the ADR-0002 determinism boundary. Targets with a
dependency-light deterministic emit additionally carry a runnable prototype and a
byte-stability test.

## Targets (`.docs/viroc-draft.md` §4.3)

| # | Future target | Probe dir | Class |
|---|---|---|---|
| 1 | Lottie export backend | `lottie/` | export format |
| 2 | Rive export backend | `rive/` | export format |
| 3 | WebGPU backend | `webgpu/` | render platform |
| 4 | native vector backend | `webgpu/` (analysis), `svg/` (remediation) | render platform |
| 5 | cloud rendering backend | `cloud/` | render platform |
| 6 | interactive web export backend | `interactive_web/` | render platform |

`.docs/viroc-draft.md` §4.3 lists "Rive/Lottie export" as one entry and §5.6
treats Rive and Lottie as distinct ecosystems; they are split here because they
have opposite export feasibility (one open JSON format, one closed binary
runtime). "WebGPU" and "native vector" are both render-platform targets evaluated
together in `webgpu/` because they collapse onto the same boundary question.

## Method

* **Capability map.** Each probe lowers the shared sample Concrete IR
  (`_sample.py`), which exercises the full vocabulary: all six primitives
  (`text`, `rect`, `icon`, `arrow`, `code`, `formula`), all five keyframe kinds
  (`fade_in`, `draw`, `move`, `highlight`, `fade_out`), every easing, and a timed
  caption. A primitive/keyframe is scored:
  * **native** — lowers directly to a first-class construct in the target;
  * **degrade** — lowers to the portable rect/text floor with a recorded note
    (matches the production `VIR5033` degradation policy);
  * **drop** — no faithful or floor lowering exists;
  * **n/a** — the target is not a source-emit target, so the question is moot.
* **Determinism check.** For GO-class targets the prototype is lowered twice and
  the bytes compared; the emit must be a pure function of the Concrete IR.
* **Boundary check.** For render-platform targets the analysis asks whether the
  target lives left of emit (must be deterministic, dependency-light) or right of
  emit (already env-gated by ADR-0002, no core change required).

## Decision legend

`DECISION: <target> = GO | NO-GO` lines below are machine-greppable. GO means the
target preserves the deterministic emit boundary and is dependency-light enough to
become a follow-on milestone candidate; NO-GO means it does not (and why).

## Export-format feasibility (PR-1)

Probes: `lottie/` (prototype + test), `rive/` (capability map). Both evaluated as
*export formats*, not full timeline renderers, per acceptance criterion (2).

### Lottie

Open JSON schema -> the lowering is pure stdlib + Concrete IR, serialized with
`viroc.core.canonical_json` and proven byte-stable by `lottie/test_lottie_export.py`.
Floor maps natively (`rect`/`arrow` -> shape layers, `text` -> text layer,
`fade_*` -> opacity, `move` -> position, `draw` -> Trim Paths); above-floor content
degrades explicitly (`icon`/`code`/`formula` -> rect floor, `highlight` -> scale
pulse, `spring` -> ease-in-out) and captions go to an SRT sidecar. No new core
dependency. Full map: `lottie/README.md`.

DECISION: Lottie export = GO

### Rive

Closed binary `.riv`, authored in the Rive editor; no open, deterministic writer
exists, so a direct emit would force non-determinism or the closed toolchain across
the ADR-0002 boundary. The Rive visual model fits the floor, so the blocker is the
format/tooling, not the vocabulary. The deterministic route is GO'd Lottie export
plus a manual, render-side Rive-editor Lottie import. Full map: `rive/README.md`.

DECISION: Rive export = NO-GO

## Render-platform feasibility (PR-2)

Probes: `interactive_web/` (prototype + test), `webgpu/` (analysis, covers WebGPU
and native vector), `cloud/` (analysis). Each is judged on whether it has a
distinct, byte-deterministic *source* emit, or whether it lives to the right of the
ADR-0002 emit boundary (acceptance criterion 3).

### Interactive web export

A deterministic, dependency-light bundle: a canonical `timeline.json` plus a fixed
vanilla-JS/SVG viewer with a scrubber and play/pause. Byte-stability and full
native keyframe coverage are proven by `interactive_web/test_interactive_web_export.py`
(`unsupported_keyframes` is empty). Playback is browser-side (right of emit). No new
core dependency. Full map: `interactive_web/README.md`.

DECISION: interactive web export = GO

### WebGPU

A GPU API, not a source format. Either a runtime detail of the interactive web
bundle or a high-complexity WGSL+JS duplicate with worse render determinism that
pushes VIROC toward owning a renderer. No unique deterministic source emit. Full
analysis: `webgpu/README.md`.

DECISION: WebGPU backend = NO-GO

### native vector

Its only deterministic source emit is SVG, already owned by the HTML and
interactive-web targets. A "native" renderer would mean VIROC embedding one,
against the compile-into-frameworks strategy. Full analysis: `webgpu/README.md`.

DECISION: native vector backend = NO-GO

### cloud rendering

Runs an existing adapter's env-gated `render()` on remote infra; sits entirely to
the right of the emit boundary. No new Concrete IR primitive, emit, or adapter;
needs SaaS credentials at render time (out of scope); buildable out of tree with
zero core dependency. Full analysis: `cloud/README.md`.

DECISION: cloud rendering backend = NO-GO

## Follow-on milestone candidates (PR-3)

Only the two GO targets preserve the byte-deterministic emit boundary, so only
they are proposed as follow-on milestones (recorded in ADR-0004,
`.docs/adr/0004-future-renderer-targets.md`, an untracked local design record). No
NO-GO target is promoted.

* **Lottie export adapter** — promote `lottie/` to a production `lottie` adapter
  under `src/viroc/adapters/`: register it in the builtin registry, give it a
  `CapabilityManifest` (floor native; `icon`/`code`/`formula` degraded via the
  `VIR5033` policy), add it to the shared conformance suite with a golden source
  hash, and emit the SRT caption sidecar. Optional `python-lottie` validation
  stays a dev-only check. No new core runtime dependency.
* **Interactive web export adapter** — promote `interactive_web/` to a production
  adapter that extends the HTML family with viewer-side controls (scrubber,
  play/pause). Emit stays the deterministic timeline JSON + fixed viewer;
  `formula`/`icon` become native behind optional, deterministic asset steps
  (KaTeX/icon set) rather than the dependency-light floor. Playback stays
  env-side.

Each candidate is a separate, independently-gated milestone; this ADR authorizes
the candidates, not their implementation.

## Summary

| §4.3 future target | Decision | Follow-on milestone candidate |
|---|---|---|
| Lottie export | GO | yes — `lottie` production adapter |
| Rive export | NO-GO | no (covered by Lottie + editor import) |
| interactive web export | GO | yes — interactive web production adapter |
| WebGPU backend | NO-GO | no |
| native vector backend | NO-GO (embedded) | SVG export consolidation (see remediation + `svg/`) |
| cloud rendering backend | NO-GO | no (out-of-tree orchestration only) |

## NO-GO remediation outcomes

Per-target follow-on to the NO-GO decisions, executing the investigation tasks and
boundary-preserving Option-A remediations in
`.docs/2026-06-27-no-go-renderer-remediation.md`. Each outcome preserves the
ADR-0002 emit boundary, adds no required core dependency, and makes no Concrete IR
change. Greppable status lines: `REMEDIATION: <target> = <status>`.

### Rive export (doc §1, Option A)

I1.2 / I1.3 executed. `rive/prepare.py` is a deterministic Lottie-preparation
harness over the GO'd `lottie/` emit: `prepare_import_bundle(ir)` yields the
byte-stable Lottie JSON to import plus a fidelity manifest, proven byte-stable by
`rive/test_rive_import.py`. The fidelity matrix (grounded in Rive's documented
Lottie import) records every emitted construct as **baked** at import; above-floor
losses live in the Lottie emit upstream, not the import. The Rive-editor import is
render-side/external (Enterprise-gated, no headless CLI), verified perceptually.
A binary `.riv` writer stays gated on I1.1 (no open serialization exists). Full
record: `rive/README.md`.

REMEDIATION: Rive export = NO-GO backend; GO via Lottie + render-side editor import (harness implemented)

### cloud rendering (doc §4, Option A)

I4.1 / I4.2 / I4.3 executed. `cloud/` is an out-of-tree orchestrator (outside
`src/viroc`, zero core change): `compile_step.py` runs the local deterministic
compile (`source_hash`), `orchestrator.py` adds a `CASCache` keyed on `source_hash`
(identical source ⇒ reuse, never re-render), a pluggable `RenderWorker` (`LocalWorker`
default; credential-gated `RemoteWorker.from_env()` that returns `None` without
`$VIROC_CLOUD_ENDPOINT`/`$VIROC_CLOUD_TOKEN`), and a perceptual verify against a
baseline. `test_cloud_orchestrator.py` proves compile determinism, content-addressed
reuse, and — via a fresh subprocess — that the compile path imports no provider SDK
and never loads the worker layer (I4.3). The HTTP client is imported lazily at
dispatch only. Full record: `cloud/README.md`.

REMEDIATION: cloud rendering = NO-GO core backend; GO as out-of-tree orchestrator (implemented, zero core change)

### native vector / SVG export (doc §3, Option A)

I3.1 / I3.2 / I3.3 executed. I3.1 is positive: a standalone `.svg` is a distinct
artifact (self-contained, no HTML/JS, headless-rasterizable) that the HTML and
interactive-web targets do not deliver. `svg/export.py` lowers the sample Concrete
IR to a byte-deterministic SMIL-animated standalone SVG (floor native, above-floor
degraded via the `VIR5033` policy, every keyframe -> one animation, no Concrete IR
change — I3.3), proven byte-stable by `svg/test_svg_export.py`. `svg/rasterize.py`
adds optional render-side rasterization to PNG/PDF via `cairosvg`/`resvg`, gated by
`check_environment()` and skipping cleanly when absent (I3.2). It stays in
`experiments/` (the M21 feasibility gate ships no production adapters); the
remaining promotion-checklist items to land it in `src/viroc/adapters/svg/` are
tracked in `svg/README.md`. Full record: `svg/README.md`.

REMEDIATION: native vector = NO-GO embedded renderer; GO as SVG export consolidation (deterministic emit + optional render-side raster implemented)
