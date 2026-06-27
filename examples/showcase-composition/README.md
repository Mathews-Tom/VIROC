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

## Unsupported backends fail explicitly

Manim supports only `rect`/`text`/`arrow`, not `code`/`formula`. Compiling this
example on Manim does not silently degrade — it fails with explicit `VIR5031`
renderer-compatibility diagnostics, one per unsupported object:

```bash
uv run viroc compile examples/showcase-composition --backend manim   # exit 1, VIR5031
```

Closing that gap (Manim parity for the richer primitive set, or an explicit
deterministic degradation policy) is M20, not M19.
