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
