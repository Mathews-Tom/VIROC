# VidIR — Semantic IR Specification

VidIR is the typed, renderer-neutral storyboard a human or an agent authors. It is the only layer outside the compiler that anyone edits. This document specifies its surface; the normative Pydantic models and schema validation land with the Semantic-IR milestone. Until then, treat `design.md` §2.2 as authoritative.

## Document shape

A storyboard is one YAML (or JSON) document with a version, video metadata, a flat entity list, and an ordered scene list.

```yaml
vidir_version: "0.1"
video:
  id: "rag-overview"
  title: "How Retrieval-Augmented Generation Works"
  resolution: { width: 1920, height: 1080 }
  fps: 30
  duration_target: 90
entities:
  - { id: documents, label: "Documents", type: data_source }
  - { id: chunks,    label: "Chunks",    type: intermediate }
scenes:
  - id: pipeline
    grammar: pipeline
    duration: 35s
    nodes: [documents, chunks]
    edges:
      - { from: documents, to: chunks, kind: split }
    narration: "Documents are chunked, embedded, and stored."
```

Full example: `overview.md` §9.1.

## Types

| Model | Holds |
|---|---|
| `VideoMeta` | `id`, `title`, `fps` (default 30), `resolution` (default 1920×1080), optional `duration_target` |
| `Entity` | `id`, `label`, `type` ∈ `EntityType` |
| `Edge` | `from` (authored key; bound to `from_`), `to`, `kind` ∈ `EdgeKind` (default `flow`) |
| `Beat` | `id`, `at` (absolute `"4s"` or relative `after(prev.end)`), `duration`, optional `narration` |
| `Scene` | `id`, `grammar`, `duration`, `nodes` (entity ids), `edges`, `beats`, optional `narration` |
| `SemanticIR` | `vidir_version`, `video`, `entities`, `scenes` |

- `EntityType` = `data_source | intermediate | model | storage | service | user`
- `EdgeKind` = `flow | split | transform | store | merge | compare`

The `from` field is a Python keyword, so the model aliases it (`Field(alias="from")`) and accepts both spellings on input; round-tripping is covered by a model test.

## Authoring rules

- The author declares *what* a scene means (`grammar`, `nodes`, `edges`) — never pixel positions, easing, or backend calls. The Resolver and adapter own those.
- Time is **absolute** (`"4s"`) or **simple relative** (`after(<id>.end)` plus fixed `±Ns` offsets). Anything needing a constraint solver is rejected with a timing diagnostic — it is out of v1 scope.
- Durations are `"<N>s"`; colors normalize to lowercase hex. No silent coercion of ambiguous values.

## Pre-validation (VIR1xxx)

Cheap, runs on the Semantic IR before any layout work (`design.md` §6):

- Schema: unknown fields, missing required ids.
- References: every edge endpoint must be a declared entity; an undeclared reference is `VIR1002` with a span and a "did you mean" suggestion (`overview.md` §9.2).
- Grammar fit: the scene's declared `grammar` must be registered; the scene must satisfy the grammar's minimum shape.

## Cross-references

- `design.md` §2.2 (models), §3 P1–P2 (load + schema-validate), §6 (validation).
- `grammar-authoring.md` — what a `grammar` value selects.
- `architecture.md` — where VidIR sits in the pipeline.
