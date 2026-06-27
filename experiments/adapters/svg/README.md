# SVG export consolidation — capability map + prototype

**Class:** render platform (the "native vector" target, reframed).
**Probe:** prototype (`export.py`) + byte-stability test (`test_svg_export.py`) +
optional render-side rasterizer (`rasterize.py`).

Per `.docs/2026-06-27-no-go-renderer-remediation.md` §3, "native vector" stays
**NO-GO as an embedded renderer** (VIROC must not own a renderer; against the
compile-into-frameworks strategy) and is reframed as **SVG export consolidation**:
a first-class standalone `.svg` artifact with optional render-side rasterization.

## I3.1 — the distinct artifact (positive)

A standalone SVG is a *distinct* deliverable the existing targets do not produce:

| Target | Artifact | Needs to view |
|---|---|---|
| HTML adapter | HTML + CSS + JS page | a browser (layout + playback) |
| interactive web | `timeline.json` + JS viewer | a browser running JS |
| **SVG export** | a single `.svg` file | nothing — open / embed / print / rasterize |

A standalone SVG is self-contained (no HTML/JS), embeddable in docs, printable, and
**headless-rasterizable** to PNG/PDF without a browser. I3.1 therefore returns a
distinct artifact, so the consolidation is justified (not a duplicate of HTML /
interactive web).

## I3.3 — pure-SVG emit carries the floor, no Concrete IR change

`export.py` lowers the shared sample Concrete IR to a byte-deterministic SVG using
only the existing primitives — **no Concrete IR change** (I3.3). Capability map:

| Concrete IR feature | SVG lowering | Class |
|---|---|---|
| `rect` | `<rect>` | native |
| `arrow` | `<line>` + arrowhead `<marker>` | native |
| `text` | `<text>` (id glyph, no measurement) | native |
| `icon` / `code` / `formula` | `<rect>` floor + note | degrade (`VIR5033`) |
| `fade_in` / `fade_out` | `<animate>` opacity | native |
| `move` | `<animateTransform>` translate | native |
| `highlight` | `<animateTransform>` scale pulse | native |
| `draw` | `<animate>` stroke-dashoffset | native |
| `spring` easing | ease-in-out spline + note | degrade |
| caption | SRT sidecar | sidecar |

`code` could be native via `<foreignObject><pre>` (reusing the HTML adapter's
lowering), but `<foreignObject>` needs an HTML engine and is not headless-
rasterizable, so it stays off the dependency-light floor and degrades to a labeled
box like the Lottie / interactive-web probes.

## I3.2 — render-side rasterization (optional)

`rasterize.py` turns the SVG emit into PNG/PDF via `cairosvg` (package) or `resvg`
(CLI), gated by `check_environment()`. It is a **render-side** consumer of the
deterministic SVG source — never a core dependency. Without a rasterizer the SVG
emit is unaffected and `test_optional_rasterizer_produces_a_png` skips cleanly.

## Determinism

`export_svg(ir)` is a pure function of the Concrete IR — byte-stable across runs
(`test_export_is_byte_deterministic`), hashed by `source_hash(ir)`. Rasterized
pixels are verified perceptually, never bit-exact (ADR-0002).

## Decision

native vector = **NO-GO as an embedded renderer**, **GO as SVG export
consolidation** (standalone `.svg` emit deterministic; raster render-side, optional).

## Promotion checklist (to land in `src/viroc/adapters/svg/`)

This prototype satisfies the determinism + capability-map half; landing it in the
core requires the remaining production-adapter items from the remediation doc, as a
separate, independently-gated follow-on milestone (M21 is a feasibility gate, not a
production-adapter milestone — ADR-0004):

- [x] `emit()` pure; `source_for(ir)`/`export_svg(ir)` byte-identical across runs.
- [x] capability map (native floor; `icon`/`code`/`formula` -> rect via `VIR5033`).
- [x] optional rasterizer via `cairosvg`/`resvg`, `importorskip`-gated.
- [ ] golden `source_hash` fixture checked into `tests/golden/`.
- [ ] `CapabilityManifest` in `src/viroc/adapters/svg/` + `builtin_registry()`.
- [ ] passes `tests/golden/test_adapter_conformance.py`.
- [ ] captions lowered to the SRT sidecar like the other adapters.
