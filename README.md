# VIROC - Video Intermediate Representation & Open Compiler

Typed storyboards. Validated before they render.

VIROC is an open-source toolchain that turns a typed, validatable storyboard (VidIR) into technical-explainer videos. It type-checks and validates the storyboard — layout, timing, references — before rendering, then compiles it deterministically into an animation backend's source code. Technical videos become reviewable in a PR, testable in CI, and reproducible by build. Built for the cases where being correct matters more than being cinematic: architecture, ML concepts, algorithms.

## Guided authoring flow

The M17 authoring path starts before `storyboard.vidir.yaml`:

```text
viroc ingest /path/to/topic-brief.yaml
viroc plan /path/to/project-root
viroc check /path/to/project-root
```

- `viroc ingest` normalizes a topic / repo / document-set request into `authoring-brief.yaml` and scaffolds the target project root.
- `viroc plan` turns that brief into `script.md`, `scene-plan.yaml`, and a starter `storyboard.vidir.yaml`.
- `viroc plan` protects an already-edited `storyboard.vidir.yaml`; pass `--force` to replace a modified storyboard with a regenerated starter copy.
- `viroc check` still validates only the emitted VidIR; the script and scene plan remain authoring artifacts, not hidden compiler inputs.
- `viroc plan --live` uses the optional Claude-backed planner path. When the Anthropic SDK or credentials are absent, it fails loudly instead of falling back silently.
