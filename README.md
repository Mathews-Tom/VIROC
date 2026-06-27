# VIROC - Video Intermediate Representation & Open Compiler

Typed storyboards. Validated before they render.

VIROC is an open-source toolchain that turns a typed, validatable storyboard (VidIR) into technical-explainer videos. It type-checks and validates the storyboard — layout, timing, references — before rendering, then compiles it deterministically into an animation backend's source code. Technical videos become reviewable in a PR, testable in CI, and reproducible by build. Built for the cases where being correct matters more than being cinematic: architecture, ML concepts, algorithms.

## Guided authoring flow

VIROC exposes a guided path from a topic to a render-ready plan, with review before render:

`ingest -> plan -> critique -> compile -> render`

```text
viroc ingest /path/to/topic-brief.yaml
viroc plan /path/to/project-root
viroc critique /path/to/project-root
viroc compile /path/to/project-root
viroc render /path/to/project-root
```

- `viroc ingest` normalizes a topic / repo / document-set request into `authoring-brief.yaml` and scaffolds the target project root.
- `viroc plan` turns that brief into `script.md`, `scene-plan.yaml`, and a starter `storyboard.vidir.yaml`, then hands off to `viroc critique`.
- `viroc plan` protects an already-edited `storyboard.vidir.yaml`; pass `--force` to replace a modified storyboard with a regenerated starter copy.
- `viroc critique` is the default pre-render review step: it compiles the storyboard and writes deterministic static-storyboard review artifacts (`storyboard.md`, `script.md`, `scene-cards.json`) plus a `review-manifest.json` under `build/review/`, so the script and scene structure are inspectable without browser or video tooling.
- `viroc critique` surfaces typed diagnostics on invalid VidIR and never leaves stale review artifacts behind; fresh artifacts are written only when validation succeeds.
- `viroc check` still validates only the emitted VidIR; the script and scene plan remain authoring artifacts, not hidden compiler inputs.
- `viroc plan --live` uses the optional Claude-backed planner path. When the Anthropic SDK or credentials are absent, it fails loudly instead of falling back silently.
