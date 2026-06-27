"""Local compile step of the out-of-tree cloud orchestrator (doc §4, I4.1/I4.3).

This is the **left-of-emit half** of cloud rendering: it runs a pure ``emit`` and
hashes the produced source into the manifest's ``source_hash``. It imports only
:mod:`viroc.core` + stdlib — nothing requiring network or credentials — so the
deterministic compile can run locally with zero provider dependency.

The credential boundary (I4.3) is proven by ``test_cloud_orchestrator.py``, which
loads *this* module (and the emit it drives) in a fresh subprocess and asserts no
network/credential package was imported. Credentials live only in the worker, never
here; this module is deliberately kept free of any cross-import to the worker /
remote modules so that property holds by construction.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from viroc.core import hash_bytes

# A pure emit: Concrete IR -> byte-deterministic backend source. Any GO'd adapter
# emit (e.g. lottie/export.export_json, interactive_web/export.export_json) fits.
EmitFn = Callable[[Any], str]


@dataclass(frozen=True, slots=True)
class CompiledSource:
    """The deterministic compile artifact shipped to a render worker."""

    source: str
    source_hash: str


def compile_source(ir: Any, emit_fn: EmitFn) -> CompiledSource:
    """Emit deterministic source and its ``source_hash`` (pure, no I/O, no creds).

    Mirrors ``viroc compile``: lower the Concrete IR with a pure adapter emit and
    hash the bytes. The digest is the true reproducibility key (ADR-0002) and the
    content-addressed cache key the orchestrator reuses across renders.
    """
    source = emit_fn(ir)
    return CompiledSource(source=source, source_hash=hash_bytes(source.encode("utf-8")))


__all__ = ["CompiledSource", "EmitFn", "compile_source"]
