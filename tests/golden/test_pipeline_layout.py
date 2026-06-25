"""Golden layout for the rag-pipeline scene (M6, PR-5).

The milestone's acceptance, pinned against committed golden boxes: the §9.1 RAG
storyboard resolves to the expected resolved-object set, that layout is byte-stable
(a digest recomputed in the same run matches), every box lies within the safe
frame, and no two boxes overlap. The golden file `rag_pipeline_layout.json` is the
canonical resolved layout; a change to expansion or the layout template must update
it deliberately, which is exactly the review signal a golden buys.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

from viroc.compiler.normalize import normalize
from viroc.compiler.resolve_layout import resolve_layout
from viroc.core import BuildContext, BuildPaths, hash_data
from viroc.grammars import contains, overlaps
from viroc.grammars.pipeline.layout import safe_frame
from viroc.ir import ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "rag-overview.vidir.yaml"
_GOLDEN = _HERE / "rag_pipeline_layout.json"
_RESOLUTION = (1920, 1080)


def _resolve() -> list[ResolvedObject]:
    """Load the rag fixture and run the full P2→P6 path to resolved boxes."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    ir = normalize(ir)
    root = Path("/tmp/viroc-golden-test")
    ctx = BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))
    return resolve_layout(ir.scenes[0], ir, ctx)


def _golden() -> list[dict[str, Any]]:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


def test_layout_matches_golden_boxes() -> None:
    """The resolved layout equals the committed golden boxes, object for object."""
    resolved = [obj.model_dump() for obj in _resolve()]
    assert resolved == _golden()


def test_layout_digest_is_byte_stable() -> None:
    """Resolving twice yields the identical digest (the determinism guarantee)."""
    first = hash_data([obj.model_dump() for obj in _resolve()])
    second = hash_data([obj.model_dump() for obj in _resolve()])
    assert first == second
    # And it matches the digest of the committed golden boxes.
    assert first == hash_data(_golden())


def test_layout_has_no_overlapping_boxes() -> None:
    """No two resolved boxes share positive area."""
    resolved = _resolve()
    collisions = [
        (a.id, b.id) for a, b in combinations(resolved, 2) if overlaps(a.box, b.box)
    ]
    assert collisions == []


def test_layout_is_within_the_safe_frame() -> None:
    """Every resolved box lies within the safe frame inset from the resolution."""
    frame = safe_frame(_RESOLUTION)
    outside = [obj.id for obj in _resolve() if not contains(frame, obj.box)]
    assert outside == []
