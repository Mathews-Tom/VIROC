"""Feasibility remediation (doc §1, Option A): deterministic Lottie-preparation
harness for the Rive editor's Lottie import.

`.docs/2026-06-27-no-go-renderer-remediation.md` §1 keeps Rive **NO-GO as a direct
backend** (there is no open, deterministic ``.riv`` writer; a binary writer stays
gated on I1.1) and adopts **Option A**: reach Rive *through* the GO'd Lottie export
plus a render-side Rive-editor import. This module owns the **deterministic half**
of that path — it reuses the GO'd ``lottie/`` emit and packages it into a
reproducible Rive-import bundle, plus records the fidelity matrix of what Rive's
importer preserves. The ``.riv`` conversion itself is a render-side, external
editor step (right of the ADR-0002 emit boundary), exactly like render execution.

What this makes runnable:

* **I1.2** (validate the Lottie -> Rive import path): the prepared Lottie document
  is the exact byte-stable artifact you drag into the Rive editor, and
  :func:`fidelity_matrix` records which constructs survive import (grounded in
  Rive's documented Lottie import; see ``README.md``).
* **I1.3** (determinism of the import): the *preparation* is a pure function of the
  Concrete IR (byte-stable, proven by ``test_rive_import.py``); the editor import
  is render-side and verified perceptually, never bit-exact.

No new core dependency: this reads only :mod:`viroc` + stdlib. The Rive editor is
external and never imported here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from viroc.core import canonical_json
from viroc.ir import ConcreteIR

_HERE = Path(__file__).resolve().parent
_LOTTIE_EXPORT = _HERE.parent / "lottie" / "export.py"

BUNDLE_LOTTIE_NAME = "viroc-sample.lottie.json"
BUNDLE_MANIFEST_NAME = "rive-import-manifest.json"

# Rive importer outcome per Lottie construct VIROC's `lottie/` emit produces,
# grounded in Rive's documented Lottie import (rive.app/docs/editor importing
# assets, rive.app changelog "improved Lottie import"): the importer bakes the
# vector graphics + animation timeline into keyframe data. It does *not* add Rive
# bones / constraints / components (interactivity) — but VIROC's emit produces
# none of those, so nothing VIROC emits is lost beyond the baked-vs-procedural
# representation tradeoff. "baked" = preserved as baked keyframe data.
_RIVE_IMPORT_FIDELITY: dict[str, str] = {
    "shape_layer": "baked",  # rect / arrow -> baked vector shapes + transform keys
    "text_layer": "baked",  # text -> baked text run
    "opacity_anim": "baked",  # fade_in / fade_out -> baked opacity keys
    "position_anim": "baked",  # move -> baked position keys
    "scale_anim": "baked",  # highlight pulse -> baked scale keys
    "trim_anim": "baked",  # draw -> baked Trim Paths keys
}


def _load_lottie_export() -> ModuleType:
    """Load the GO'd Lottie export probe by path (experiments is not a package)."""
    spec = importlib.util.spec_from_file_location("viroc_lottie_export", _LOTTIE_EXPORT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lottie = _load_lottie_export()


def lottie_document(ir: ConcreteIR) -> dict[str, Any]:
    """Return the GO'd Lottie document VIROC owns deterministically (delegates)."""
    document, _ = _lottie.lower(ir)
    return document


def _animated_properties(layer: dict[str, Any]) -> list[str]:
    """Record which animatable transform/shape properties this layer carries keys for."""
    props: list[str] = []
    transform = layer.get("ks", {})
    if transform.get("o", {}).get("a") == 1:
        props.append("opacity_anim")
    if transform.get("p", {}).get("a") == 1:
        props.append("position_anim")
    if transform.get("s", {}).get("a") == 1:
        props.append("scale_anim")
    for shape in layer.get("shapes", []):
        for item in shape.get("it", []):
            if item.get("ty") == "tm":
                props.append("trim_anim")
    return props


def fidelity_matrix(ir: ConcreteIR) -> list[dict[str, Any]]:
    """Per-layer record of the Lottie construct -> Rive-import fidelity (pure).

    Walks the lowered Lottie document so the matrix is derived from the *actual*
    emitted bytes, not asserted in the abstract. Layer order follows the Lottie
    document (already deterministic), so the matrix is byte-stable.
    """
    document = lottie_document(ir)
    records: list[dict[str, Any]] = []
    for layer in document["layers"]:
        construct = "text_layer" if layer["ty"] == 5 else "shape_layer"
        constructs = [construct, *_animated_properties(layer)]
        records.append(
            {
                "object": layer["nm"],
                "lottie_constructs": constructs,
                "rive_import": [_RIVE_IMPORT_FIDELITY[c] for c in constructs],
            }
        )
    return records


def prepare_import_bundle(ir: ConcreteIR) -> dict[str, str]:
    """Return the deterministic {filename: content} Rive-import bundle.

    Two files: the byte-stable Lottie JSON to drag into the Rive editor, and an
    import manifest recording the fidelity matrix + the degradations the Lottie
    emit already applied upstream (so the import adds no surprise losses).
    """
    document, degradations = _lottie.lower(ir)
    manifest = {
        "name": "viroc-rive-import",
        "lottie_version": _lottie.LOTTIE_VERSION,
        "source_format": "lottie-json",
        "target": "rive-editor-import",
        "import_is": "render-side, external (Rive editor); verified perceptually",
        "fidelity": fidelity_matrix(ir),
        "upstream_degradations": degradations,
    }
    return {
        BUNDLE_LOTTIE_NAME: f"{canonical_json(document)}\n",
        BUNDLE_MANIFEST_NAME: f"{canonical_json(manifest)}\n",
    }


def export_json(ir: ConcreteIR) -> str:
    """Serialize the whole import bundle as canonical JSON (byte-deterministic)."""
    return f"{canonical_json(prepare_import_bundle(ir))}\n"


__all__ = [
    "BUNDLE_LOTTIE_NAME",
    "BUNDLE_MANIFEST_NAME",
    "export_json",
    "fidelity_matrix",
    "lottie_document",
    "prepare_import_bundle",
]
