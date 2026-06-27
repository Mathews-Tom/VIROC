"""Determinism, content-addressed caching, and credential-boundary checks for the
out-of-tree cloud orchestrator.

Outside the gated tree (`pyproject.toml` excludes `experiments/` from the default
pytest testpaths); `uv run pytest -q` never collects this. Run it explicitly:

    uv run pytest experiments/adapters -q

Everything here uses only stdlib + the viroc package and always runs. The remote
worker is credential-gated, so the only "external" dependency (a cloud endpoint) is
never exercised — `RemoteWorker.from_env()` returns ``None`` without credentials and
the orchestrator falls back to the local worker.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_sample = _load("adapters_sample", _HERE.parent / "_sample.py")
_lottie = _load("lottie_export", _HERE.parent / "lottie" / "export.py")
_orch = _load("cloud_orchestrator", _HERE / "orchestrator.py")

# Third-party network / credential SDKs the compile path must never pull in. Stdlib
# socket/ssl/urllib are excluded: pydantic imports them transitively, so their
# presence is not evidence of network/credential intent — a provider SDK would be.
_NETWORK_SDK_ROOTS = {
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
    "boto3",
    "botocore",
    "anthropic",
    "openai",
    "google",
    "googleapiclient",
    "azure",
    "paramiko",
}


def test_compile_step_is_byte_deterministic() -> None:
    """The compile step is a pure function of the Concrete IR (ADR-0002, I4.1)."""
    ir = _sample.sample_concrete_ir()
    first = _orch.compile_source(ir, _lottie.export_json)
    second = _orch.compile_source(ir, _lottie.export_json)
    assert first.source == second.source
    assert first.source_hash == second.source_hash
    assert first.source_hash.startswith("sha256:")


def test_cache_reuses_renders_keyed_on_source_hash(tmp_path: Path) -> None:
    """Identical source ⇒ identical source_hash ⇒ cached render reused, not re-run (I4.2)."""

    class CountingWorker:
        def __init__(self) -> None:
            self.calls = 0

        def render(self, compiled: object) -> object:
            self.calls += 1
            return _orch.RenderResult(
                video_ref=f"counting:{compiled.source_hash}",  # type: ignore[attr-defined]
                perceptual_hash="phash:fixed",
                worker="counting",
            )

    ir = _sample.sample_concrete_ir()
    cache = _orch.CASCache(tmp_path / "cas")
    worker = CountingWorker()

    first = _orch.orchestrate(ir, _lottie.export_json, worker=worker, cache=cache, baseline_phash="phash:fixed")
    second = _orch.orchestrate(ir, _lottie.export_json, worker=worker, cache=cache, baseline_phash="phash:fixed")
    assert first.reused is False and second.reused is True
    assert worker.calls == 1  # the second run reused the cache, never re-rendered
    assert second.result.perceptual_hash == "phash:fixed"

    # A different deterministic source hashes differently and misses the cache.
    third = _orch.orchestrate(
        ir, lambda _ir: "a-different-source", worker=worker, cache=cache, baseline_phash="phash:fixed"
    )
    assert third.reused is False and worker.calls == 2
    assert third.source_hash != first.source_hash


def test_orchestrate_verifies_against_the_manifest_baseline(tmp_path: Path) -> None:
    """Render outcome is perceptually verified against a baseline hash (ADR-0002)."""
    ir = _sample.sample_concrete_ir()
    worker = _orch.LocalWorker()
    compiled = _orch.compile_source(ir, _lottie.export_json)
    baseline = worker.render(compiled).perceptual_hash

    ok = _orch.orchestrate(
        ir, _lottie.export_json, worker=worker, cache=_orch.CASCache(tmp_path / "ok"), baseline_phash=baseline
    )
    assert ok.verified is True

    bad = _orch.orchestrate(
        ir, _lottie.export_json, worker=worker, cache=_orch.CASCache(tmp_path / "bad"), baseline_phash="phash:wrong"
    )
    assert bad.verified is False


def test_compile_path_imports_no_network_or_credentials() -> None:
    """I4.3: loading the compile path pulls in no provider SDK and no worker module."""
    probe = (
        "import importlib.util, json, sys\n"
        "from pathlib import Path\n"
        f"here = Path({str(_HERE.parent)!r})\n"
        "def load(name, p):\n"
        "    spec = importlib.util.spec_from_file_location(name, p)\n"
        "    m = importlib.util.module_from_spec(spec); sys.modules[name] = m\n"
        "    spec.loader.exec_module(m); return m\n"
        "load('cloud_compile_step', here / 'cloud' / 'compile_step.py')\n"
        "load('lottie_export', here / 'lottie' / 'export.py')\n"
        f"roots = {sorted(_NETWORK_SDK_ROOTS)!r}\n"
        "hit = sorted(m for m in sys.modules if m.split('.')[0] in set(roots))\n"
        "print(json.dumps({'sdks': hit, 'orchestrator_loaded': 'cloud_orchestrator' in sys.modules}))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report["sdks"] == [], f"compile path imported network/credential SDKs: {report['sdks']}"
    assert report["orchestrator_loaded"] is False  # compile never imports the worker layer


def test_remote_worker_skips_cleanly_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without credentials the remote worker is unavailable and local is the default."""
    monkeypatch.delenv("VIROC_CLOUD_ENDPOINT", raising=False)
    monkeypatch.delenv("VIROC_CLOUD_TOKEN", raising=False)
    assert _orch.RemoteWorker.from_env() is None
    assert isinstance(_orch.default_worker(), _orch.LocalWorker)
