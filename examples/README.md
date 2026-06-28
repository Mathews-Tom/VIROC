# VIROC examples

Three examples, one shape. Each walks the guided concept-to-video flow — `ingest -> plan -> critique -> compile -> render` — with committed, regenerable artifacts, and states an explicit top-three (Manim / HTML / Remotion) parity story. Read them in order: `rag-pipeline` to learn the flow, `showcase-composition` to see the richer grammar and its degradation policy, `viroc-codebase` for the flagship.

| Example | Role | Grammar | Tagline |
|---|---|---|---|
| [`rag-pipeline`](rag-pipeline/) | Linear-flow onboarding | `pipeline` | Linear pipeline grammar. Floor-only primitives. Full native parity on all top three. |
| [`showcase-composition`](showcase-composition/) | Grammar + degradation proof | `showcase` | Showcase grammar. Non-row composition. Above-floor primitives with explicit Manim degradation. |
| [`viroc-codebase`](viroc-codebase/) | Flagship guided flow | `showcase` | Topic to verified video. Typed IR. Portable renderers. |

`pipeline` stays the boring left-to-right linear grammar; richer composition lives only in the `showcase` grammar — never as `pipeline` special-casing.

## Shared conventions

Every example carries the same shape, verified by `tests/integration/test_examples_gallery.py`:

- **Guided-flow provenance**, all committed and regenerable: `authoring-request.yaml` (the only hand-authored input) → `viroc ingest` → `authoring-brief.yaml` → `viroc plan` → `script.md`, `scene-plan.yaml`, `storyboard.vidir.yaml`. Re-running `ingest`/`plan` is idempotent and byte-stable.
- **Committed review surface** under `expected/review/` (`storyboard.md`, `script.md`, `scene-cards.json`, `captions.md`, `review-manifest.json`), produced by `viroc critique`.
- **Inspectable compile baselines**: committed `expected/generated/<backend>/` source, a per-backend `expected/<backend>/source.sha256`, and a machine-readable `expected/gallery.json`. A committed `expected/preview/manim/` render exists where one was rendered.
- **Explicit parity**: above-floor `code`/`formula` primitives render natively on HTML and Remotion and degrade deterministically to `rect` with a non-blocking `VIR5033` note on Manim — never silently omitted. Floor-only examples are full-native on all top three.

## Source-hash index

Every committed `source.sha256` is reproduced by a fresh deterministic `viroc compile`:

| Example | `manim` | `html` | `remotion` | `static_storyboard` |
|---|---|---|---|---|
| `rag-pipeline` | `6be1007` | `7b09d44` | `ee3c919` | — |
| `showcase-composition` | `efd0d36` | `0f1330c` | `998c623` | `8185915` |
| `viroc-codebase` | `8ffe9c0` | `8af1ecb` | `edc8bf7` | — |

Hashes are abbreviated; the full `sha256:` values live in each example's `expected/<backend>/source.sha256` and `expected/gallery.json`. On Manim, `showcase-composition` and `viroc-codebase` emit `VIR5033` degradation notes for `code`/`formula` and still exit 0; `rag-pipeline` is floor-only and emits none.
