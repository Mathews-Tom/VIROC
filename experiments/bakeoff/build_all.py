#!/usr/bin/env python3
"""M1 bake-off build harness.

Discovers each topic from ``vidir/*.vidir.yaml``, requires all three
representations (hand-written Manim, Remotion TSX, VidIR storyboard), and emits
one renderable artifact per (approach, topic) into ``out/``:

* ``out/manim__<topic>.py``    -- the hand-written Manim, syntax-checked.
* ``out/remotion__<topic>.tsx``-- the Remotion composition, structurally checked.
* ``out/vidir__<topic>.py``    -- Manim lowered from the validated VidIR.

With all five topics present this writes exactly 15 files. The harness fails
loudly (non-zero exit) on any missing representation, schema/reference defect,
syntax error, or malformed Remotion source -- there are no silent skips.

This is throwaway experiment code (DEVELOPMENT_PLAN.md §4 M1); it is not the
compiler and is not imported by anything under ``src/viroc``.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vidir"))

import schema  # noqa: E402  (local throwaway module, path injected above)
import lower  # noqa: E402

APPROACHES = ("manim", "remotion", "vidir")
OUT = ROOT / "out"


class BuildError(RuntimeError):
    """A bake-off artifact could not be produced or validated."""


def discover_topics() -> list[str]:
    topics = sorted(p.name[: -len(".vidir.yaml")] for p in (ROOT / "vidir").glob("*.vidir.yaml"))
    if not topics:
        raise BuildError("no topics found: expected vidir/<topic>.vidir.yaml files")
    return topics


def require(path: Path, topic: str, approach: str) -> None:
    if not path.is_file():
        raise BuildError(f"{topic}: missing {approach} representation at {path}")


def check_manim_source(src: str, where: str) -> None:
    compile(src, where, "exec")  # raises SyntaxError on malformed Python
    if "(Scene)" not in src or "def construct" not in src:
        raise BuildError(f"{where}: not a renderable Manim Scene (no Scene/construct)")


def check_remotion_source(src: str, where: str) -> None:
    required = ("export const", "useCurrentFrame", "AbsoluteFill", 'from "remotion"')
    missing = [token for token in required if token not in src]
    if missing or not src.strip():
        raise BuildError(f"{where}: not a Remotion composition (missing {missing})")


def build_topic(topic: str) -> list[Path]:
    manim_src_path = ROOT / "manim" / f"{topic}.py"
    remotion_src_path = ROOT / "remotion" / f"{topic}.tsx"
    vidir_src_path = ROOT / "vidir" / f"{topic}.vidir.yaml"
    require(manim_src_path, topic, "manim")
    require(remotion_src_path, topic, "remotion")
    require(vidir_src_path, topic, "vidir")

    written: list[Path] = []

    manim_src = manim_src_path.read_text(encoding="utf-8")
    check_manim_source(manim_src, str(manim_src_path))
    out_manim = OUT / f"manim__{topic}.py"
    out_manim.write_text(manim_src, encoding="utf-8")
    written.append(out_manim)

    remotion_src = remotion_src_path.read_text(encoding="utf-8")
    check_remotion_source(remotion_src, str(remotion_src_path))
    out_remotion = OUT / f"remotion__{topic}.tsx"
    out_remotion.write_text(remotion_src, encoding="utf-8")
    written.append(out_remotion)

    ir = schema.load(vidir_src_path)  # schema + reference + grammar-fit validation
    lowered = lower.lower_storyboard(ir, topic)
    check_manim_source(lowered, f"vidir__{topic}.py")
    out_vidir = OUT / f"vidir__{topic}.py"
    out_vidir.write_text(lowered, encoding="utf-8")
    written.append(out_vidir)

    return written


def main() -> int:
    topics = discover_topics()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    written: list[Path] = []
    for topic in topics:
        produced = build_topic(topic)
        written.extend(produced)
        print(f"  {topic}: " + ", ".join(p.name for p in produced))

    expected = len(topics) * len(APPROACHES)
    actual = len(list(OUT.iterdir()))
    if actual != expected or len(written) != expected:
        raise BuildError(
            f"expected {expected} artifacts ({len(topics)} topics x {len(APPROACHES)} "
            f"approaches), wrote {len(written)} / found {actual} in {OUT}"
        )
    print(f"OK: {actual} artifacts written to {OUT.relative_to(ROOT.parent.parent)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, schema.VidirError, SyntaxError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
