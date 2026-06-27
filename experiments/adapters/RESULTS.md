# Future/export adapter feasibility — results

Applies the M21 feasibility bar (see `README.md`) to every future renderer target
named in `.docs/viroc-draft.md` §4.3. Every decision below is backed by a
capability map against the shared sample Concrete IR (`_sample.py`) and an
analysis of the target against the ADR-0002 determinism boundary. Targets with a
dependency-light deterministic emit additionally carry a runnable prototype and a
byte-stability test.

## Targets (`.docs/viroc-draft.md` §4.3)

| # | Future target | Probe dir | Class |
|---|---|---|---|
| 1 | Lottie export backend | `lottie/` | export format |
| 2 | Rive export backend | `rive/` | export format |
| 3 | WebGPU backend | `webgpu/` | render platform |
| 4 | native vector backend | `webgpu/` | render platform |
| 5 | cloud rendering backend | `cloud/` | render platform |
| 6 | interactive web export backend | `interactive_web/` | render platform |

`.docs/viroc-draft.md` §4.3 lists "Rive/Lottie export" as one entry and §5.6
treats Rive and Lottie as distinct ecosystems; they are split here because they
have opposite export feasibility (one open JSON format, one closed binary
runtime). "WebGPU" and "native vector" are both render-platform targets evaluated
together in `webgpu/` because they collapse onto the same boundary question.

## Method

* **Capability map.** Each probe lowers the shared sample Concrete IR
  (`_sample.py`), which exercises the full vocabulary: all six primitives
  (`text`, `rect`, `icon`, `arrow`, `code`, `formula`), all five keyframe kinds
  (`fade_in`, `draw`, `move`, `highlight`, `fade_out`), every easing, and a timed
  caption. A primitive/keyframe is scored:
  * **native** — lowers directly to a first-class construct in the target;
  * **degrade** — lowers to the portable rect/text floor with a recorded note
    (matches the production `VIR5033` degradation policy);
  * **drop** — no faithful or floor lowering exists;
  * **n/a** — the target is not a source-emit target, so the question is moot.
* **Determinism check.** For GO-class targets the prototype is lowered twice and
  the bytes compared; the emit must be a pure function of the Concrete IR.
* **Boundary check.** For render-platform targets the analysis asks whether the
  target lives left of emit (must be deterministic, dependency-light) or right of
  emit (already env-gated by ADR-0002, no core change required).

## Decision legend

`DECISION: <target> = GO | NO-GO` lines below are machine-greppable. GO means the
target preserves the deterministic emit boundary and is dependency-light enough to
become a follow-on milestone candidate; NO-GO means it does not (and why).

<!-- Export-format decisions (PR-1) appended below. -->
<!-- Render-platform decisions (PR-2) appended below. -->
<!-- Follow-on milestone candidates (PR-3) appended below. -->
