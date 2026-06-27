"""Showcase grammar registration, binding, and Concrete IR assembly (M19, PR-3)."""

from __future__ import annotations

from pathlib import Path

from viroc.compiler.pipeline import CompileState, run_pipeline
from viroc.core import BuildContext, BuildPaths, Diagnostic, hash_data
from viroc.grammars import Grammar, get, register_builtins
from viroc.grammars.showcase import GRAMMAR_ID, GRAMMAR_VERSION
from viroc.grammars.showcase.grammar import showcase_grammar
from viroc.ir import load_document
from viroc.validators import pre_validate

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "showcase-composition.vidir.yaml"
_SUPPORTED_ANIMATIONS = {"fade_in", "draw", "highlight", "fade_out"}


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-showcase-grammar-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _compile() -> tuple[CompileState, list[Diagnostic]]:
    ir, diagnostics = pre_validate(load_document(_FIXTURE))
    assert ir is not None
    state = run_pipeline(ir, _ctx())
    return state, [*diagnostics, *state.diagnostics]


def test_register_builtins_registers_showcase_idempotently() -> None:
    """register_builtins registers showcase alongside pipeline, idempotently."""
    register_builtins()
    register_builtins()
    assert get(GRAMMAR_ID) is showcase_grammar


def test_showcase_grammar_identity_and_animation_surface() -> None:
    """The bound grammar reports its id/version and satisfies the full contract."""
    assert showcase_grammar.id == "showcase"
    assert showcase_grammar.version == GRAMMAR_VERSION
    assert isinstance(showcase_grammar, Grammar)


def test_showcase_fixture_compiles_without_diagnostics() -> None:
    """The showcase fixture passes pre-validation and the pure pipeline cleanly."""
    state, diagnostics = _compile()
    assert diagnostics == []
    assert state.exit_code == 0


def test_showcase_assembly_carries_code_and_formula_primitives() -> None:
    """Assembly lowers code cards to ``code`` and evidence blocks to ``formula``."""
    state, _ = _compile()
    primitives = {obj.primitive for obj in state.concrete.objects}
    assert {"code", "formula", "rect", "text"} <= primitives


def test_showcase_keyframes_stay_supported_and_in_span() -> None:
    """Keyframes use only top-three animations and lie within their scene span."""
    state, _ = _compile()
    kinds = {kf.kind for kf in state.concrete.keyframes}
    assert kinds
    assert kinds <= _SUPPORTED_ANIMATIONS
    for kf in state.concrete.keyframes:
        assert 0 <= kf.start_f <= kf.end_f


def test_showcase_assembly_is_deterministic() -> None:
    """Compiling the fixture twice yields the identical Concrete IR digest."""
    first = hash_data(_compile()[0].concrete.model_dump(mode="json"))
    second = hash_data(_compile()[0].concrete.model_dump(mode="json"))
    assert first == second
