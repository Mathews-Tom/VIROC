"""Optional render-side rasterizer for the SVG export (doc §3, I3.2).

Headless rasterization (SVG -> PNG/PDF) is a **render-side** consumer of the
deterministic SVG emit: it runs an external tool gated by :func:`check_environment`,
exactly like every other ``render()``. Two interchangeable backends, both optional:

* ``cairosvg`` — a Python package (imported lazily; ``importorskip`` in the tests);
* ``resvg`` — a CLI on ``PATH``.

Neither is a core dependency. Without them, rasterization is unavailable and the SVG
source emit is unaffected — ``uv run pytest -q`` stays green. Rendered pixels are
verified perceptually, never bit-exact (ADR-0002).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path


def _cairosvg_available() -> bool:
    return importlib.util.find_spec("cairosvg") is not None


def check_environment() -> list[str]:
    """Return diagnostics for missing rasterization tools (empty == ready)."""
    if _cairosvg_available() or shutil.which("resvg") is not None:
        return []
    return ["no SVG rasterizer found (install the optional `cairosvg` package or the `resvg` CLI)"]


def rasterize_png(svg: str, out_path: Path) -> Path:
    """Rasterize SVG text to a PNG via cairosvg or resvg (render-side, env-gated)."""
    if _cairosvg_available():
        import cairosvg

        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_path))
        return out_path
    resvg = shutil.which("resvg")
    if resvg is not None:
        src = out_path.with_suffix(".svg")
        src.write_text(svg)
        subprocess.run([resvg, str(src), str(out_path)], check=True)
        return out_path
    raise RuntimeError("no SVG rasterizer available; install cairosvg or the resvg CLI")


def rasterize_pdf(svg: str, out_path: Path) -> Path:
    """Rasterize SVG text to a PDF via cairosvg (render-side, env-gated)."""
    if not _cairosvg_available():
        raise RuntimeError("PDF rasterization needs the optional `cairosvg` package")
    import cairosvg

    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(out_path))
    return out_path


__all__ = ["check_environment", "rasterize_pdf", "rasterize_png"]
