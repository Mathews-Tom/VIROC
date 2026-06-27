"""Out-of-tree cloud rendering orchestrator (doc §4, Option A).

Cloud rendering is a deployment pattern over the existing env-gated ``render()``,
not a new backend (``RESULTS.md``: cloud rendering = NO-GO as a core target). It
preserves the ADR-0002 boundary because it lives entirely to the *right* of emit:

    local:  compile_source(ir, emit) -> CompiledSource (+ source_hash)   # deterministic
    cache:  CASCache keyed on source_hash -> reuse identical renders      # I4.2
    ship:   hand the CompiledSource to a worker
    worker: worker.render(compiled)  -> RenderResult (+ perceptual hash)  # env-gated
    verify: perceptual hash vs baseline                                   # ADR-0002

This module lives **outside** ``src/viroc`` and the core package needs no change
(I4.1). The deterministic compile is a separate, credential-clean module
(``compile_step.py``). The remote worker is credential-gated and lazily imports its
HTTP client, so importing this module pulls in nothing requiring network/creds, and
the compile path imports neither this module nor any worker (I4.3).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> Any:
    """Load a sibling experiment module by path (experiments is not a package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_compile = _load("cloud_compile_step", _HERE / "compile_step.py")
compile_source = _compile.compile_source


@dataclass(frozen=True, slots=True)
class RenderResult:
    """A finished render: a video reference and its render-side perceptual hash."""

    video_ref: str
    perceptual_hash: str
    worker: str


@dataclass(frozen=True, slots=True)
class Outcome:
    """The orchestration result: cache reuse + perceptual verification status."""

    source_hash: str
    reused: bool
    verified: bool
    result: RenderResult


@runtime_checkable
class RenderWorker(Protocol):
    """A render worker runs ``adapter.render`` for a CompiledSource (env-gated)."""

    def render(self, compiled: Any) -> RenderResult: ...


def _identity_render(source: str) -> bytes:
    """Default local stand-in: treat the emitted source bytes as the render output."""
    return source.encode("utf-8")


def _stub_perceptual_hash(frames: bytes) -> str:
    """Stand-in for a DCT pHash of rendered frames (ADR-0002 render-side).

    Deterministic *here* only because the local stub does not actually rasterize;
    a production worker computes this from real frames and it is perceptual, not
    bit-exact. The orchestrator treats it purely as an opaque comparison key.
    """
    return f"phash:{sha256(frames).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class LocalWorker:
    """Default dependency-light worker: renders locally, no network, no creds.

    ``render_fn`` maps source text to rendered frame bytes; the default is an
    identity stand-in so the orchestrator is runnable end to end. Production passes
    a real ``adapter.render`` here.
    """

    name: str = "local"
    render_fn: Callable[[str], bytes] | None = None

    def render(self, compiled: Any) -> RenderResult:
        render = self.render_fn or _identity_render
        frames = render(compiled.source)
        return RenderResult(
            video_ref=f"local:{compiled.source_hash}",
            perceptual_hash=_stub_perceptual_hash(frames),
            worker=self.name,
        )


@dataclass(frozen=True, slots=True)
class RemoteWorker:
    """Optional credential-gated worker that dispatches render to a remote endpoint.

    Constructed from ``$VIROC_CLOUD_ENDPOINT`` + ``$VIROC_CLOUD_TOKEN`` via
    :meth:`from_env`, which returns ``None`` when credentials are absent so callers
    fall back to the local worker cleanly. The HTTP client is imported lazily inside
    :meth:`render`, never at module import, keeping the compile path credential-clean.
    """

    endpoint: str
    token: str
    name: str = "remote"

    @classmethod
    def from_env(cls) -> RemoteWorker | None:
        endpoint = os.environ.get("VIROC_CLOUD_ENDPOINT")
        token = os.environ.get("VIROC_CLOUD_TOKEN")
        if not endpoint or not token:
            return None
        return cls(endpoint=endpoint, token=token)

    def render(self, compiled: Any) -> RenderResult:
        from urllib import request  # lazy: network only at dispatch, never at import

        payload = json.dumps(
            {"source": compiled.source, "source_hash": compiled.source_hash}
        ).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req) as resp:  # endpoint is operator-provided
            body = json.loads(resp.read())
        return RenderResult(
            video_ref=body["video_ref"],
            perceptual_hash=body["perceptual_hash"],
            worker=self.name,
        )


def default_worker() -> RenderWorker:
    """Remote worker when credentials are present, else the local default."""
    return RemoteWorker.from_env() or LocalWorker()


class CASCache:
    """Content-addressed render cache keyed on ``source_hash`` (I4.2).

    Identical deterministic source ⇒ identical ``source_hash`` ⇒ reuse the cached
    render, never re-render. This is the main payoff of cloud rendering and it leans
    directly on the byte-deterministic emit (ADR-0002).
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _entry(self, source_hash: str) -> Path:
        return self.root / f"{source_hash.replace(':', '_')}.json"

    def get(self, source_hash: str) -> RenderResult | None:
        entry = self._entry(source_hash)
        if not entry.exists():
            return None
        return RenderResult(**json.loads(entry.read_text()))

    def put(self, source_hash: str, result: RenderResult) -> None:
        self._entry(source_hash).write_text(json.dumps(asdict(result), sort_keys=True))


def orchestrate(
    ir: Any,
    emit_fn: Any,
    *,
    worker: RenderWorker,
    cache: CASCache,
    baseline_phash: str,
) -> Outcome:
    """Compile locally, reuse-or-render via the worker, verify against baseline (I4.1)."""
    compiled = compile_source(ir, emit_fn)
    cached = cache.get(compiled.source_hash)
    if cached is not None:
        return Outcome(
            source_hash=compiled.source_hash,
            reused=True,
            verified=cached.perceptual_hash == baseline_phash,
            result=cached,
        )
    result = worker.render(compiled)
    cache.put(compiled.source_hash, result)
    return Outcome(
        source_hash=compiled.source_hash,
        reused=False,
        verified=result.perceptual_hash == baseline_phash,
        result=result,
    )


__all__ = [
    "CASCache",
    "LocalWorker",
    "Outcome",
    "RemoteWorker",
    "RenderResult",
    "RenderWorker",
    "compile_source",
    "default_worker",
    "orchestrate",
]
