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
| `static_storyboard` | `sha256:fb29449e63cb28bb3a6aeb2123eca74bc686670c812e606e16c19b3b8f6a3ed5` |
| `html` | `sha256:0db65853affcd155da0bce37bc0a9487e4d29348e4f6870fe606c5203c6c480c` |
| `remotion` | `sha256:719cd7c3030b076b0a0ee06016cbeed2bf3b1874d2b31694d957cfa318b927a2` |

## Unsupported backends fail explicitly

Manim supports only `rect`/`text`/`arrow`, not `code`/`formula`. Compiling this
example on Manim does not silently degrade — it fails with explicit `VIR5031`
renderer-compatibility diagnostics, one per unsupported object:

```bash
uv run viroc compile examples/showcase-composition --backend manim   # exit 1, VIR5031
```

Closing that gap (Manim parity for the richer primitive set, or an explicit
deterministic degradation policy) is M20, not M19.
