# VIROC codebase showcase

Topic to verified video. Typed IR. Portable renderers.

This flagship example walks the **guided VIROC flow** end to end: a user starts from a concept (repo context, a document set, a topic brief), the guided planner derives a script and scene plan, that becomes editable VidIR, `viroc check` repairs it, a review surface is inspected, and one Concrete IR compiles deterministically across Manim, HTML, and Remotion before the reproducibility proof closes it out. It uses the richer `showcase` grammar (non-row grid, fan-out, and comparison compositions), not the single-row `pipeline` ceiling. The acceptance surface is deterministic compile output across the top three backends; render proof stays env-gated and diagnostic-backed.

## Scene arc (guided flow)

| Scene | Claim | Code anchors |
|---|---|---|
| `concept_input` | Start from a concept: a repo, a document set, and a topic brief. | `src/viroc/cli/ingest.py`, `src/viroc/cli/plan.py`, `docs/overview.md` |
| `script_and_scene_plan` | The guided planner derives a script, a scene plan, and an outline. | `src/viroc/authoring/planner.py`, `src/viroc/authoring/models.py`, `src/viroc/cli/plan.py` |
| `editable_vidir` | The approved outline becomes editable VidIR the user owns. | `src/viroc/authoring/io.py`, `src/viroc/ir/semantic.py`, `src/viroc/ir/io.py` |
| `validate_repair` | `viroc check` surfaces typed VIR diagnostics so the storyboard is repaired before render. | `src/viroc/cli/check.py`, `src/viroc/validators/schema.py`, `src/viroc/validators/timing.py`, `src/viroc/validators/layout.py` |
| `storyboard_review` | The review surface shows scene cards and the script before final render. | `src/viroc/cli/critique.py`, `src/viroc/adapters/static_storyboard`, `src/viroc/grammars/showcase` |
| `compile_fanout` | One Concrete IR compiles deterministically to Manim, HTML, and Remotion source. | `src/viroc/adapters/registry.py`, `src/viroc/cli/compile.py`, `src/viroc/adapters/manim`, `src/viroc/adapters/html`, `src/viroc/adapters/remotion` |
| `parity_proof` | Backends are compared and source hashes plus `build.json` close the reproducibility proof. | `src/viroc/core/manifest.py`, `src/viroc/cli/render.py`, `examples/viroc-codebase/expected/gallery.json` |

## Top-three parity

Every top-three backend renders the common visual floor (`rect`/`text`/`arrow`) natively. The richer `showcase` grammar also emits above-floor `code` and `formula` primitives: HTML and Remotion render them with full fidelity, while Manim renders each as its floor primitive (`rect`) — a deterministic degradation that keeps every object's placement and title and is surfaced as a non-blocking `VIR5033` note, never silently omitted. `viroc compile … --backend manim` therefore exits 0 and prints the degradation notes; `--backend html` and `--backend remotion` compile with no notes.

## Inspectable artifacts

Committed generated source now lives under `expected/generated/`, so the example can be inspected on GitHub without rebuilding locally. The committed local preview render is `expected/preview/manim/viroc-codebase.mp4`, with matching captions at `expected/preview/manim/captions.srt` and a manifest snapshot at `expected/preview/manim/build.json`.

| Backend | Committed source root | Entry file | Source hash | Render reference |
|---|---|---|---|---|
| `manim` | `expected/generated/manim/` | `expected/generated/manim/scene.py` | `sha256:0899d90d30b7d97b23404a4a186202cce300dfc3d614f68b6d7ec5bde1ad398b` | preview video at `expected/preview/manim/viroc-codebase.mp4`; perceptual baseline at `expected/manim/render.json` (code/formula degraded to rect) |
| `html` | `expected/generated/html/` | `expected/generated/html/scene.html` | `sha256:6ed01bc515acad379a17d71d4b4f1c1fb1da20311bbe9dbc019c0c0ef0a82991` | env-gated render; skip when no browser is available (full code/formula fidelity) |
| `remotion` | `expected/generated/remotion/` | `expected/generated/remotion/package.json` | `sha256:fd1432205913e634f68b90360cdac13a99e24354da04640e94843af7f3708250` | env-gated render; skip when the Remotion CLI probe fails (full code/formula fidelity) |

The machine-readable companion for this scene arc, committed source roots, and preview paths is `expected/gallery.json`.
