# Interactive web export — capability map

**Class:** render platform (source-emit target).
**Probe:** `export.py` lowers the shared sample Concrete IR (`../_sample.py`) to a
deterministic interactive bundle; `test_interactive_web_export.py` proves
byte-determinism and full native keyframe coverage.

## Why interactive web preserves the emit boundary

The existing HTML adapter emits a page that *plays* a fixed animation. Interactive
export adds viewer-side controls — a frame **scrubber** and **play/pause** — over
the same resolved storyboard. The bundle is pure source:

* `timeline.json` — the Concrete IR projected to a frame-addressable timeline
  (objects + per-object keyframe segments), serialized with
  `viroc.core.canonical_json`, so it is byte-identical across runs;
* `index.html` — a fixed, framework-free viewer that loads `timeline.json` and
  interpolates every frame in vanilla JS + inline SVG.

Both halves are deterministic. The only environment-dependent part is the browser
that *plays* the bundle — to the right of the emit boundary, like render
execution. No new dependency (vanilla JS/SVG, no framework, no bundler).

## Primitive map

| Concrete IR primitive | Interactive web lowering | Score |
|---|---|---|
| `rect` / `arrow` | positioned SVG box | native |
| `text` | SVG `<text>` | native |
| `code` | `<pre>`/box (HTML adapter already supports `code`) | native |
| `formula` | text box in the dependency-light viewer | degrade* |
| `icon` | labeled box in the dependency-light viewer | degrade* |

\* `formula`/`icon` are native in the full HTML adapter family but degrade in this
*dependency-light* viewer (native math needs an optional KaTeX/MathJax bundle;
native icons need an optional icon set). The degrade keeps the prototype
zero-dependency; it is not a fundamental limit of the target.

## Keyframe / easing map

| Concrete IR keyframe | Interactive web lowering | Score |
|---|---|---|
| `fade_in` / `fade_out` | per-frame opacity | native |
| `move` | per-frame translate (deterministic enter offset) | native |
| `draw` | per-frame width reveal | native |
| `highlight` | per-frame scale/outline pulse | native |
| Easing `linear` / `ease_in_out` | linear / smoothstep | native |
| Easing `spring` | smoothstep (degraded; no spring solver bundled) | degrade |

`unsupported_keyframes(sample)` is empty: interactive web is general-purpose JS, so
it covers the **full** keyframe vocabulary natively — strictly more than Lottie's
fixed schema.

## Decision

**GO** as a follow-on milestone candidate. It is the most aligned future target:
a deterministic, dependency-light *source* emit that extends the HTML adapter with
viewer-side interactivity, with playback kept env-side. A production version would
make `formula`/`icon` native behind optional, deterministic asset steps.
