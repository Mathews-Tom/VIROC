"""Integration coverage for the multi-adapter VIROC codebase showcase."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE = _ROOT / "examples" / "viroc-codebase"
_COMPILE_OUTPUTS = {
    "manim": _EXAMPLE / "build" / "generated" / "manim" / "scene.py",
    "html": _EXAMPLE / "build" / "generated" / "html" / "scene.html",
    "remotion": _EXAMPLE / "build" / "generated" / "remotion",
}
_EXPECTED_SOURCE_HASHES = {
    backend: (
        (_EXAMPLE / "expected" / backend / "source.sha256")
        .read_text(encoding="utf-8")
        .strip()
    )
    for backend in _COMPILE_OUTPUTS
}


def _clean_build() -> None:
    shutil.rmtree(_EXAMPLE / "build", ignore_errors=True)


@pytest.mark.integration
def test_viroc_codebase_showcase_check_and_compile(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_build()

    assert main(["check", str(_EXAMPLE)]) == 0
    assert capsys.readouterr().err == ""

    for backend, generated in _COMPILE_OUTPUTS.items():
        assert main(["compile", str(_EXAMPLE), "--backend", backend]) == 0
        compile_capture = capsys.readouterr()
        assert str(generated) in compile_capture.out
        assert f"source_hash: {_EXPECTED_SOURCE_HASHES[backend]}" in compile_capture.out
        assert generated.exists()
