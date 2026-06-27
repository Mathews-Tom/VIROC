# Lottie export — capability map

**Class:** export format (not a full timeline renderer).
**Probe:** `export.py` lowers the shared sample Concrete IR (`../_sample.py`) to a
Lottie-subset JSON document; `test_lottie_export.py` proves byte-determinism and
locks the capability map.

## Why Lottie is a clean export target

Lottie is an open, documented JSON schema (Bodymovin export of After Effects;
`.docs/viroc-draft.md` §5.6). Because the artifact is JSON, the lowering is a pure
function of the Concrete IR serialized with `viroc.core.canonical_json` — the same
byte-deterministic discipline as the production adapters' `source_hash`
(ADR-0002). No external tool, font measurement, or credential is needed to emit
the bytes; rendering/playback stays to the right of the emit boundary.

## Primitive map

| Concrete IR primitive | Lottie lowering | Score |
|---|---|---|
| `rect` | shape layer (`ty:4`) with `rc` + `fl` | native |
| `arrow` | shape layer with 2-point `sh` path + `st` stroke | native |
| `text` | text layer (`ty:5`), player-resolved font, no glyph baking | native* |
| `icon` | rect floor + recorded note (no semantic icon in Lottie) | degrade |
| `code` | rect floor + recorded note (no code/syntax construct) | degrade |
| `formula` | rect floor + recorded note (LaTeX needs a baked raster asset) | degrade |

\* `text` is native only if the player resolves the named font. VIROC emits no
baked glyph outlines, which keeps emit deterministic but pushes font resolution to
render — consistent with the determinism boundary.

## Keyframe / easing map

| Concrete IR keyframe | Lottie lowering | Score |
|---|---|---|
| `fade_in` / `fade_out` | layer transform opacity keyframes (`ks.o`) | native |
| `move` | position keyframes (`ks.p`) | native† |
| `draw` | Trim Paths modifier (`tm`) on the shape group | native |
| `highlight` | scale pulse (`ks.s`) + recorded note (no native property) | degrade |
| Easing `linear` / `ease_in_out` | cubic-bezier handles | native |
| Easing `spring` | degraded to `ease_in_out` bezier + recorded note | degrade |

\† Concrete IR keyframes carry only `(kind, window, easing)`, never a positional
delta. The `move` vector is therefore an adapter-chosen deterministic enter offset
(`_MOVE_ENTER_DX`), not IR data — a real finding, not a Lottie limitation.

## Captions

Lottie has no subtitle track. Captions lower to an SRT sidecar exactly as the
production adapters do, so no caption data is lost.

## Decision

**GO** as an export format. The floor lowers natively, above-floor content
degrades explicitly (mirrors the `VIR5033` policy), and the emit is
byte-deterministic and dependency-light (stdlib + Concrete IR). Promote to a
follow-on milestone candidate. It does **not** become a full timeline renderer:
`code`/`formula`/`icon` fidelity and font baking are out of scope and would only
be revisited behind an optional, deterministic asset-baking step.
