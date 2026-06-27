# Rive export — capability map

**Class:** export format (not a full timeline renderer).
**Probe:** documentation-only. Unlike Lottie there is **no** dependency-light,
deterministic emit path, so this probe records a capability map and a GO/NO-GO
rather than a prototype (DEVELOPMENT_PLAN.md §4 M21: "deterministic export
sketch/prototype *if dependency-light*").

## Why Rive has no direct deterministic emit path

Rive ships open-source *runtimes* and a GPU-accelerated vector renderer, but its
animations are authored in the closed Rive editor and delivered as a **binary
`.riv` file** (`.docs/viroc-draft.md` §5.6). The published, supported tooling
reads `.riv` for playback; it does not provide an open writer that turns an
arbitrary scene graph into a byte-stable `.riv`. Emitting `.riv` from Concrete IR
would mean either driving the closed editor (not a pure function; not
dependency-light) or reverse-engineering an unspecified binary container (fragile;
no determinism guarantee). Both violate the ADR-0002 emit boundary, which requires
a deterministic, dependency-light *source* emit.

## Capability map (conceptual)

Rive's vector/animation model *could* express the portable floor — its artboards,
shapes, and timelines cover `rect`/`arrow`/`text` and opacity/transform/trim-style
motion — so the limitation is the **format/tooling**, not the visual vocabulary:

| Concrete IR feature | Rive model fit | Emit path today |
|---|---|---|
| `rect` / `arrow` / `text` | artboard shapes / text run | no open writer |
| `icon` / `code` / `formula` | image asset / text run (no semantic construct) | no open writer |
| `fade_*` / `move` / `draw` | timeline interpolation / trim | no open writer |
| `highlight` / `spring` | state-machine / custom interpolation | no open writer |

The fit is plausible; the blocker is that there is no deterministic, open
serializer to produce the bytes.

## The only viable path: Lottie → Rive import

Rive's editor **imports Lottie**. The deterministic, dependency-light route to a
Rive asset is therefore:

```text
Concrete IR --(viroc, deterministic)--> Lottie JSON --(Rive editor, manual)--> .riv
```

VIROC owns the deterministic half (the Lottie export GO'd in `../lottie/`); the
`.riv` conversion is a manual, environment-side editor step — squarely to the
right of the emit boundary, exactly like render execution.

## Decision

**NO-GO** as a direct Rive export backend (no open, deterministic `.riv` writer;
would force non-determinism or the closed toolchain into emit). The Rive use case
is already covered by **GO Lottie export + manual Rive-editor import**. Re-evaluate
only if Rive ships a documented, open, deterministic text/JSON serialization that
VIROC can emit as source.

## Remediation (Option A) — implemented

Per `.docs/2026-06-27-no-go-renderer-remediation.md` §1, Rive stays **NO-GO as a
direct backend** (a binary `.riv` writer is Option B, gated on **I1.1** finding an
open, documented, stable `.riv` serialization — none exists today). The supported
answer is **Option A: Lottie -> Rive import**, and `prepare.py` now makes the
VIROC-side half runnable and byte-stable:

```bash
uv run pytest experiments/adapters/rive -q      # byte-determinism + fidelity
```

`prepare.prepare_import_bundle(ir)` returns a deterministic two-file bundle: the
GO'd Lottie JSON (byte-identical to the `../lottie/` emit) to drag into the Rive
editor, plus a `rive-import-manifest.json` recording the fidelity matrix and the
degradations the Lottie emit already applied upstream.

### I1.2 — Lottie -> Rive import procedure (reproducible)

The Rive editor's Lottie import has no public headless CLI; it is an external,
render-side step (Enterprise-gated as of 2025-12). The reproducible procedure:

1. `uv run python -c "import experiments.adapters.rive.prepare as p, experiments.adapters._sample as s; open('viroc-sample.lottie.json','w').write(p.prepare_import_bundle(s.sample_concrete_ir())['viroc-sample.lottie.json'])"`
   — or load `prepare.py` by path as the tests do — to materialize the byte-stable
   Lottie JSON.
2. Drag `viroc-sample.lottie.json` into the Rive editor (Assets panel -> drop onto
   an empty Artboard). The importer bakes the vector graphics + animation timeline
   into keyframe data.
3. Export the resulting `.riv`. Capture a perceptual-hash baseline of its playback
   (render-side verification, per ADR-0002 — never bit-exact).

If a custom importer is wired via `$VIROC_RIVE_IMPORT_CLI` (`<cli> <lottie.json>
<out.riv>`), `test_rive_editor_import_when_available` runs step 2 automatically;
otherwise it skips cleanly (the honest state today).

### I1.2 — fidelity matrix

Grounded in Rive's documented Lottie import (rive.app editor docs; changelog
"improved Lottie import"): the importer **bakes** vector graphics + the animation
timeline into keyframe data. It does not synthesize Rive bones / constraints /
components (interactivity) — but VIROC's emit produces none of those, so nothing
VIROC emits is lost beyond the baked-vs-procedural representation. The matrix below
is derived from the *actual* lowered Lottie bytes by `prepare.fidelity_matrix`:

| Lottie construct (from `../lottie/`) | Source feature | Rive import |
|---|---|---|
| shape layer (`ty=4`) | `rect` / `arrow` (+ degraded `icon`/`code`/`formula`) | baked |
| text layer (`ty=5`) | `text` | baked |
| `ks.o` opacity keys | `fade_in` / `fade_out` | baked |
| `ks.p` position keys | `move` | baked |
| `ks.s` scale keys | `highlight` (already a scale pulse) | baked |
| Trim Paths (`ty=tm`) keys | `draw` | baked |

Above-floor losses (`icon`/`code`/`formula` -> rect floor; `spring` ->
`ease_in_out`; caption -> SRT sidecar) all happen in the **Lottie emit**, recorded
in the manifest's `upstream_degradations`; the import itself adds no further drop
for the content VIROC emits. VIROC's emit uses only normal blending and neutral
fills, so the documented Plus/Add/Hard-Mix blend-mode import caveat does not apply.

### I1.3 — determinism of the import

The **preparation** is a pure function of the Concrete IR — byte-stable across runs
(`test_import_bundle_is_byte_deterministic`), so the artifact dragged into the
editor is reproducible. The **import** is render-side and external: it bakes the
already-baked timeline (it re-times nothing procedurally), so a perceptual-hash
baseline of the imported playback is stable within an ADR-0002 threshold — but it
is verified perceptually, never bit-exact, exactly like every other `render()`.

### Decision (unchanged, now evidenced)

Rive = **NO-GO as a backend** (Option B blocked on I1.1), **GO as a downstream of
the Lottie export** via the Option-A harness + import procedure above. Re-open only
if Rive ships an open, deterministic `.riv`/JSON serialization (I1.1 positive).
