# Bake-off rubric

The one question the de-risking gate asks (overview.md §7):

> For **editing, validating, and re-rendering**, which intermediate do you want
> to live in — hand-written Manim, a Remotion (React) composition, or VidIR?

This rubric fixes *how* that question is scored, before any scores are filled in
(scores live in `RESULTS.md`). It compares the three intermediates produced for
the five topics in `manim/`, `remotion/`, and `vidir/`.

## What is being compared

The **intermediate the engineer edits and lives in** — not the final pixels.
"Quality of the rendered video" is explicitly *not* an axis: the visual language
is held constant across approaches so the comparison is about the artifact you
maintain, not aesthetics (this mirrors VIROC's stance that validation, not
prettiness, is the product — overview.md §3.3).

## The three axes

### Axis 1 — Edit

How local and how *safe* is a representative structural change? The fixed change
scenario, applied to `rag-pipeline`:

> Insert a `reranker` node between `vector_db` and `llm`, retargeting the edge.

Scored on: number of distinct edit sites, whether re-layout is manual, and
whether a mistake (typo, dangling reference) is caught or silently shipped.

### Axis 2 — Validate

Which defects can be caught **mechanically, before rendering**? The fixed probe:
introduce a dangling edge endpoint (a reference to an entity that is not
declared) and observe whether the toolchain flags it pre-render. This is the
class of check VIROC claims framework code structurally cannot offer
(overview.md §2, §3.3).

### Axis 3 — Re-render

Is the rendered **source reproducible**? The fixed probe: produce the backend
source twice from the same input and compare bytes. VIROC's determinism contract
guarantees a byte-stable compile (a `source_hash` reproducibility key); the
question is which intermediate actually delivers it (overview.md §3.2).

## Scoring scale

Each approach scores **0–5 per axis** (5 = best), with a one-line justification
grounded in an observed measurement or run, not opinion:

| Score | Meaning |
|---|---|
| 5 | Best-in-class; the property holds by construction |
| 3 | Workable; the property is partial or costs discipline |
| 1 | Poor; the property is absent and failures are silent |

## GO threshold

The milestone's binary gate is "≥ 3 of 5 senior engineers pick VidIR." This
rubric operationalizes that judgment so it is reproducible:

> **GO** iff **VidIR ranks first on at least 2 of the 3 axes _and_ is last on
> none.** Otherwise **NO-GO**, and the project halts (overview.md §7).

Rationale: an intermediate that wins edit-safety, validatability, and
reproducibility is precisely the one a senior engineer chooses to live in;
winning a clear majority of axes without losing any is the measurable form of
that preference. A single decision is then recorded in `RESULTS.md`
(`DECISION: GO` or `DECISION: NO-GO`) and in `.docs/adr/0000-bakeoff-go-no-go.md`.
