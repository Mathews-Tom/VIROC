# Showcase grammar — composition primitives

A proof example for the `showcase` grammar (M19). Where `examples/rag-pipeline`
and `examples/viroc-codebase` exercise the linear `pipeline` grammar, this
example exercises authored explainer composition: panels, code cards, callouts,
and evidence blocks arranged in non-row layouts.

`pipeline` stays the boring left-to-right flow grammar. `showcase` is a separate,
bounded grammar — it does not extend or special-case `pipeline`.

## Scenes

| Scene | Template | What it shows |
|---|---|---|
| `primitives` | grid | One of each composition kind in a 2x2 grid: a panel (`data_source`), a code card (`intermediate` → `code`), a callout (`user`), and an evidence block (`storage` → `formula`). |
| `fanout` | fan-out | A resolver service fanning out to three artifacts, hub column left, targets stacked right, connectors in the gap. |
| `comparison` | comparison | Two backend paths placed side by side, paired and connected row by row. |

Each composition kind lowers to a Concrete IR primitive: panels and callouts to
`rect`, code cards to `code`, evidence blocks to `formula`.

## Compile matrix

The composition compiles deterministically on every backend that supports the
`code` and `formula` primitives:

```bash
uv run viroc compile examples/showcase-composition --backend static_storyboard
uv run viroc compile examples/showcase-composition --backend html
uv run viroc compile examples/showcase-composition --backend remotion
```

Each prints a stable `source_hash:` matching the committed baseline under
`expected/<backend>/source.sha256`:

| Backend | `expected/<backend>/source.sha256` |
|---|---|
| `static_storyboard` | `sha256:1e7704642f264d78787c4fa841edd49dbe2143fe9f9415ad018b1f22ba4d4d82` |
| `html` | `sha256:0ca3acc173f0fa5cdcf696e6a6954bd6c9ad00ba9a928afcd49f861315d1e4ab` |
| `remotion` | `sha256:57fef780de372ff521a6342052d1acd331abf3580a168467b9573f6bd8c65b01` |

## Above-floor primitives degrade deterministically on Manim

Manim renders only the common floor (`rect`/`text`/`arrow`), not the above-floor
`code`/`formula` primitives. Compiling on Manim does not silently drop them and
does not hard-fail: each is rendered as its floor primitive (`rect`), keeping the
object's placement and title, and the degradation is surfaced as an explicit,
non-blocking `VIR5033` note — one per degraded object:

```bash
uv run viroc compile examples/showcase-composition --backend manim   # exit 0, VIR5033 notes
```

The parity policy is explicit (M20): every top-three backend renders the floor
natively, and above-floor primitives are either supported natively (HTML,
Remotion) or degraded deterministically with a diagnostic (Manim) — never
silently omitted. HTML and Remotion keep full `code`/`formula` fidelity.
