"""Verify the full ``viroc`` package namespace imports and the CLI entrypoint runs."""

from __future__ import annotations

import importlib

import pytest

SUBPACKAGES = [
    "viroc.core",
    "viroc.ir",
    "viroc.compiler",
    "viroc.grammars",
    "viroc.grammars.pipeline",
    "viroc.adapters",
    "viroc.adapters.manim",
    "viroc.validators",
    "viroc.cli",
]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    module = importlib.import_module(name)
    assert module.__name__ == name


def test_cli_entrypoint_runs() -> None:
    from viroc.cli import main

    assert main() == 0
