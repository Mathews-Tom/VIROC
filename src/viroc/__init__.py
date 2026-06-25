"""VIROC: a typed, verifiable intermediate layer for technical video.

This is the importable root of the ``viroc`` package. Compiler subsystems are
introduced as the milestones that own them land; this module only exposes the
package version so the toolchain has a stable target to assert against.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
