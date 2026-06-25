"""VIROC command-line surface.

The full command set (``init``, ``check``, ``compile``, ``render``, ``graph``,
``doctor``) is built once the compiler exists. For now this exposes the console
entrypoint declared in ``pyproject.toml`` so the toolchain has a runnable target.
"""

from __future__ import annotations

from viroc import __version__

__all__ = ["main"]


def main() -> int:
    """Entry point for the ``viroc`` console script.

    Prints the package version and exits successfully. Subcommands are added by
    the milestone that introduces the CLI.
    """
    print(f"viroc {__version__}")
    return 0
