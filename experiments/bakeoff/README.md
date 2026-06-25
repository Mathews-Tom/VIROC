# M1 — De-risking bake-off

> Throwaway experiment. This is **not** the VIROC compiler and nothing here is
> reused by later milestones (DEVELOPMENT_PLAN.md §4 M1, overview.md §7).

## Why this exists

Top risk #1 (overview.md §5): *the IR isn't worth it — a senior engineer would
rather edit raw Manim than VidIR.* This experiment falsifies that cheaply by
building the same five technical-video topics **three ways** and asking which
intermediate is best to **edit, validate, and re-render**.

## The three approaches

| Dir | Approach | What the engineer edits |
|---|---|---|
| `manim/` | Hand-written Manim (LLM-assisted) | imperative Python per topic |
| `remotion/` | Remotion Skills (agent → React) | a React/TSX composition per topic |
| `vidir/` | Mocked VidIR + throwaway lowering | declarative YAML; one generic lowering |

## The five topics

`rag-pipeline`, `transformer-attention`, `ci-cd-pipeline`,
`microservices-topology`, `algorithm-bfs` — all expressed by the single
`pipeline` grammar (overview.md §9.4).

## Layout

```
experiments/bakeoff/
  build_all.py            # emits + statically validates 15 artifacts -> out/
  manim/<topic>.py        # hand-written Manim Scene per topic
  remotion/<topic>.tsx    # Remotion composition per topic
  vidir/<topic>.vidir.yaml # hand-authored Semantic IR per topic
  vidir/schema.py         # throwaway mocked VidIR (pydantic) + validation
  vidir/lower.py          # throwaway VidIR -> Manim lowering
  RUBRIC.md               # the three-axis comparison + GO threshold
  RESULTS.md              # scores + the single DECISION line
```

## Build (the automatable gate)

```bash
pip install -r experiments/bakeoff/requirements.txt   # pydantic + pyyaml
python experiments/bakeoff/build_all.py               # exits 0, writes out/
```

`build_all.py` discovers each topic from `vidir/*.vidir.yaml`, requires all three
representations to be present, validates the VidIR (schema + references), runs the
lowering, syntax-checks the Manim-family Python, structurally checks the Remotion
TSX, and writes one renderable artifact per (approach, topic) to `out/`. With all
five topics present it writes **15** files.

## Rendering to playable clips (environment-dependent)

Pixel rendering is intentionally out of the harness (overview.md §3.2: render is
perceptually stable, never part of the pure path). To render the Manim-family
artifacts once `manim` + `ffmpeg` are installed:

```bash
python experiments/bakeoff/build_all.py
manim -ql experiments/bakeoff/out/manim__rag-pipeline.py RagPipeline
manim -ql experiments/bakeoff/out/vidir__rag-pipeline.py RagPipeline
```

The Remotion artifacts render inside a Node + Remotion project (Remotion Skills /
`npx create-video`); that toolchain is deliberately kept outside this folder.
