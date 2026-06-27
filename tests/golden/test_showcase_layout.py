"""Golden layout for the showcase composition fixture (M19, PR-2).

The milestone's acceptance, pinned against committed golden boxes: the showcase
fixture resolves to the expected resolved-object set across its grid, fan-out, and
comparison scenes, that layout is byte-stable (a digest recomputed in the same run
matches), that every box lies within the safe frame, and that no two boxes within
a scene overlap. The golden file ``showcase_composition_layout.json`` is the
canonical resolved layout; a change to expansion or a layout template must update
it deliberately, which is exactly the review signal a golden buys.

These are the *non-row* layouts that distinguish ``showcase`` from ``pipeline``:
the grid scene spans multiple rows and columns, the fan-out scene a hub column
plus a target column, and the comparison scene two paired columns — none is a
single row.
"""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from viroc.compiler.normalize import normalize
from viroc.core import BuildContext, BuildPaths, hash_data
from viroc.grammars import contains, overlaps
from viroc.grammars.showcase.expand import expand
from viroc.grammars.showcase.layout import layout, safe_frame
from viroc.ir import ResolvedObject, load_document
from viroc.validators import validate_schema

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE.parent / "fixtures" / "showcase-composition.vidir.yaml"
_GOLDEN = _HERE / "showcase_composition_layout.json"
_RESOLUTION = (1920, 1080)


def _ctx() -> BuildContext:
    root = Path("/tmp/viroc-showcase-golden-test")
    return BuildContext(paths=BuildPaths(project_root=root, out_dir=root / "dist"))


def _resolve() -> list[ResolvedObject]:
    """Load the showcase fixture and lay out every scene, in scene order."""
    ir, diagnostics = validate_schema(load_document(_FIXTURE))
    assert ir is not None
    assert diagnostics == []
    ir = normalize(ir)
    resolved: list[ResolvedObject] = []
    for scene in ir.scenes:
        resolved.extend(layout(expand(scene, ir), _RESOLUTION, _ctx()))
    return resolved


def _golden() -> list[dict[str, Any]]:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


def _scene_of(object_id: str) -> str:
    return object_id.split(".", 1)[0]


def test_layout_matches_golden_boxes() -> None:
    """The resolved layout equals the committed golden boxes, object for object."""
    resolved = [obj.model_dump() for obj in _resolve()]
    assert resolved == _golden()


def test_layout_digest_is_byte_stable() -> None:
    """Resolving twice yields the identical digest (the determinism guarantee)."""
    first = hash_data([obj.model_dump() for obj in _resolve()])
    second = hash_data([obj.model_dump() for obj in _resolve()])
    assert first == second
    assert first == hash_data(_golden())


def test_layout_has_no_overlapping_boxes_within_a_scene() -> None:
    """No two resolved boxes within the same scene share positive area."""
    by_scene: dict[str, list[ResolvedObject]] = defaultdict(list)
    for obj in _resolve():
        by_scene[_scene_of(obj.id)].append(obj)
    collisions = [
        (a.id, b.id)
        for scene_objects in by_scene.values()
        for a, b in combinations(scene_objects, 2)
        if overlaps(a.box, b.box)
    ]
    assert collisions == []


def test_layout_is_within_the_safe_frame() -> None:
    """Every resolved box lies within the safe frame inset from the resolution."""
    frame = safe_frame(_RESOLUTION)
    outside = [obj.id for obj in _resolve() if not contains(frame, obj.box)]
    assert outside == []


def test_each_scene_is_a_non_row_composition() -> None:
    """Every scene spans more than one row and column of primary boxes."""
    primaries: dict[str, list[ResolvedObject]] = defaultdict(list)
    for obj in _resolve():
        if obj.primitive != "arrow" and not obj.id.endswith(".title"):
            primaries[_scene_of(obj.id)].append(obj)
    for scene, objects in primaries.items():
        rows = {round(obj.box.y) for obj in objects}
        cols = {round(obj.box.x) for obj in objects}
        assert len(rows) >= 2, f"scene {scene!r} is a single row"
        assert len(cols) >= 2, f"scene {scene!r} is a single column"
