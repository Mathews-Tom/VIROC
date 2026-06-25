# Grammar Authoring

A **grammar** maps one semantic pattern (e.g. `pipeline`) to a layout + animation template that reads well. Grammars are where domain taste — "a RAG flow looks *like this*" — is encoded, and they are the unit in which VIROC accumulates value (`overview.md` §8). This document specifies the plugin contract; the normative Protocol, registry, and the v1 `pipeline` grammar land with the grammar milestone.

## What a grammar owns

A grammar owns three things for its pattern (`design.md` §4):

1. **Expand** — turn semantic nodes/edges into a set of abstract objects (a `pipeline` becomes node-boxes + connecting arrows + labels).
2. **Layout** — place those objects without overlap, with balance, for *this* pattern. Template-driven, not a general constraint solver. See ADR-0003.
3. **Animate** — default entrance/transform/exit choreography for the pattern.

```
Semantic scene ─▶ expand() ─▶ abstract objects
               ─▶ layout()  ─▶ resolved boxes (Concrete IR fragment)
               ─▶ animate() ─▶ resolved keyframes
```

## The contract (shape)

```python
class Grammar(Protocol):
    id: str
    version: str
    def expand(self, scene: Scene, ir: SemanticIR) -> list[AbstractObject]: ...
    def layout(self, objects: list[AbstractObject], ctx: BuildContext) -> list[ResolvedObject]: ...
    def animate(self, objects: list[ResolvedObject], scene: Scene) -> list[Keyframe]: ...
```

Signatures are illustrative; the authoritative contract ships with the grammar milestone. Grammars register under their `id`; a scene selects one via its `grammar` field (`vidir-spec.md`).

## Rules

- **Template-per-pattern, not a global solver.** General "looks-good" graph layout is research-grade and open-ended; per-pattern templates are tractable. v1 ships exactly one grammar: `pipeline`. See ADR-0003.
- **Determinism.** `expand` and `layout` are pure and byte-stable across runs; the same scene yields the same boxes (verified by a golden digest).
- **Measurement lives in the Resolver.** If a grammar needs text/LaTeX measurement, it does it during `layout` — never in an adapter's `emit()`, which must stay environment-invariant. See ADR-0002.
- **No overlap, safe margins.** `layout` output has zero pairwise box overlap and stays within the safe frame; post-resolve validation enforces this (`VIR3xxx`).

## The v1 `pipeline` grammar

`pipeline` covers the five v1 topics (`rag-pipeline`, `transformer-attention`, `ci-cd-pipeline`, `microservices-topology`, `algorithm-bfs`) as variants of a single left-to-right flow (`overview.md` §9.4). Whether the template covers all five without per-example special-casing is an open question tracked in `design.md` §10; any special-casing is recorded there.

## Cross-references

- `design.md` §4 (grammar system), §3 P5–P6 (expand + layout), §10 (open questions).
- `vidir-spec.md` — the `grammar` field and scene shape a grammar consumes.
- `architecture.md` — where grammars sit in the pipeline.
