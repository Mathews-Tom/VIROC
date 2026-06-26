# VIROC codebase showcase

Video IR. Open compiler. Pluggable renderers.

This example is a compiler proof for the VIROC repo itself. It now runs as a 7-scene user journey: repo context and video goal, `viroc init`, authored `storyboard.vidir.yaml`, VIR validation, Concrete IR resolve, top-three adapter fan-out, and reproducibility artifacts. The acceptance surface is still deterministic compile output across Manim, HTML, and Remotion; render proof stays env-gated and diagnostic-backed.

## Scene arc

| Scene | Claim | Code anchors |
|---|---|---|
| `entry_point` | Users start from repo context and a video goal, not renderer code. | `examples/viroc-codebase/storyboard.vidir.yaml`, `docs/overview.md`, `src/viroc/cli/init.py` |
| `project_scaffold` | `viroc init` creates `viroc.yaml` and `storyboard.vidir.yaml`. | `examples/viroc-codebase/viroc.yaml`, `src/viroc/cli/init.py` |
| `authored_input` | Authored files load into typed Semantic IR. | `src/viroc/ir/io.py`, `src/viroc/ir/semantic.py`, `src/viroc/cli/_common.py` |
| `validation_boundary` | VIR1/VIR2/VIR3/VIR4/VIR5 checks fail early before render. | `src/viroc/validators/schema.py`, `src/viroc/validators/timing.py`, `src/viroc/validators/layout.py`, `src/viroc/adapters/html/render.py`, `src/viroc/adapters/remotion/render.py` |
| `resolver_boundary` | The resolver fixes layout, timing, and animation into Concrete IR. | `src/viroc/compiler/pipeline.py`, `src/viroc/compiler/resolve_layout.py`, `src/viroc/compiler/resolve_time.py`, `src/viroc/ir/concrete.py` |
| `adapter_fanout` | One Concrete IR lowers through the registry to the top three adapters and a chosen backend renders artifacts. | `src/viroc/adapters/registry.py`, `src/viroc/cli/compile.py`, `src/viroc/adapters/manim`, `src/viroc/adapters/html`, `src/viroc/adapters/remotion` |
| `proof_artifacts` | Sources, stable hashes, `build.json`, render pHash, and `gallery.json` prove reproducibility. | `src/viroc/core/manifest.py`, `src/viroc/cli/render.py`, `examples/viroc-codebase/expected/gallery.json` |

## Inspectable artifacts

Committed generated source now lives under `expected/generated/`, so the example can be inspected on GitHub without rebuilding locally. The committed local preview render is `expected/preview/manim/viroc-codebase.mp4`, with matching captions at `expected/preview/manim/captions.srt` and a manifest snapshot at `expected/preview/manim/build.json`.

| Backend | Committed source root | Entry file | Source hash | Render reference |
|---|---|---|---|---|
| `manim` | `expected/generated/manim/` | `expected/generated/manim/scene.py` | `sha256:d1c9e648d5fd5a1cc7cec34fd4bfc19c85975fde6154a2530574beb6c4f0b5c3` | preview video at `expected/preview/manim/viroc-codebase.mp4`; perceptual baseline at `expected/manim/render.json` |
| `html` | `expected/generated/html/` | `expected/generated/html/scene.html` | `sha256:fb9409d4ef3231483252ba3531158be4ad666c86acbe9b7129a2debba1587132` | perceptual baseline at `expected/html/render.json` |
| `remotion` | `expected/generated/remotion/` | `expected/generated/remotion/package.json` | `sha256:e52bf848307409f59740099c3bc4be00b6bf3381a12151cd05f58dcef9501eea` | env-gated render; skip when the Remotion CLI probe fails |

The machine-readable companion for this scene arc, committed source roots, and preview paths is `expected/gallery.json`.
