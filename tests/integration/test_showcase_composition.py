"""Integration coverage for the showcase-composition grammar proof example."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "showcase-composition"
_README = (_EXAMPLE / "README.md").read_text(encoding="utf-8")
_SUPPORTED_BACKENDS = ("static_storyboard", "html", "remotion")
_COMPILE_OUTPUTS = {
    "static_storyboard": _EXAMPLE / "build" / "generated" / "static_storyboard",
    "html": _EXAMPLE / "build" / "generated" / "html" / "scene.html",
    "remotion": _EXAMPLE / "build" / "generated" / "remotion",
}
_EXPECTED_SOURCE_HASHES = {
    backend: (_EXAMPLE / "expected" / backend / "source.sha256")
    .read_text(encoding="utf-8")
    .strip()
    for backend in _SUPPORTED_BACKENDS
}


def _clean_build() -> None:
    shutil.rmtree(_EXAMPLE / "build", ignore_errors=True)


@pytest.mark.integration
def test_showcase_check_passes_with_no_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The example passes pre-validation with no diagnostic output."""
    assert main(["check", str(_EXAMPLE)]) == 0
    assert capsys.readouterr().err == ""


@pytest.mark.integration
@pytest.mark.parametrize("backend", _SUPPORTED_BACKENDS)
def test_showcase_compiles_with_stable_hash(
    backend: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each supporting backend compiles to exit 0 with its committed source hash."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
    captured = capsys.readouterr()
    generated = _COMPILE_OUTPUTS[backend]
    assert str(generated) in captured.out
    assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in captured.out
    assert generated.exists()
    assert _EXPECTED_SOURCE_HASHES[backend] in _README


@pytest.mark.integration
def test_showcase_on_manim_fails_with_explicit_capability_diagnostic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Manim cannot render code/formula, so it fails with VIR5031, not a downgrade."""
    _clean_build()
    assert main(["compile", str(_EXAMPLE), "--backend", "manim"]) == 1
    err = capsys.readouterr().err
    assert "VIR5031" in err
    assert 'does not support primitive "code"' in err
    assert 'does not support primitive "formula"' in err
    assert not (_EXAMPLE / "build" / "generated" / "manim").exists()
