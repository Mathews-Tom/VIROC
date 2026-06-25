"""Smoke test: the ``viroc`` package imports and exposes a version string.

This is the minimal automated assertion surface later milestones build on.
"""

from __future__ import annotations

import viroc


def test_package_imports() -> None:
    assert isinstance(viroc.__version__, str)
    assert viroc.__version__


def test_version_is_exported() -> None:
    assert "__version__" in viroc.__all__
