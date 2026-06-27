"""Canonical sample Concrete IR shared by every future-adapter feasibility probe.

The feasibility prototypes under ``experiments/adapters/`` all lower the *same*
fully-resolved storyboard so their capability maps are comparable apples-to-apples.
The sample is built from the real :mod:`viroc.ir` types (not a mock), so a probe
that lowers it is exercising the production Concrete IR vocabulary:

* every drawable primitive — ``text``, ``rect``, ``icon``, ``arrow``, ``code``,
  ``formula`` (the last three sit *above* the portable common floor);
* every keyframe kind — ``fade_in``, ``draw``, ``move``, ``highlight``,
  ``fade_out`` — and every easing;
* a timed caption (lowered to SRT by production adapters).

This module performs no I/O and reads no environment: it is import-safe and the
returned value is identical on every call, which is what lets the probes assert
byte-deterministic export.
"""

from __future__ import annotations

from viroc.ir import Box, Caption, ConcreteIR, Keyframe, ResolvedObject

FPS = 30
RESOLUTION = (1920, 1080)


def sample_concrete_ir() -> ConcreteIR:
    """Return the shared, deterministic Concrete IR every probe lowers."""
    objects = [
        ResolvedObject(
            id="title",
            primitive="text",
            box=Box(x=80.0, y=48.0, w=1760.0, h=120.0),
            z=0,
            style_ref="label",
        ),
        ResolvedObject(
            id="ingest",
            primitive="rect",
            box=Box(x=120.0, y=300.0, w=360.0, h=200.0),
            z=1,
            style_ref="node.data_source",
        ),
        ResolvedObject(
            id="retriever",
            primitive="rect",
            box=Box(x=780.0, y=300.0, w=360.0, h=200.0),
            z=1,
            style_ref="node.process",
        ),
        ResolvedObject(
            id="model",
            primitive="rect",
            box=Box(x=1440.0, y=300.0, w=360.0, h=200.0),
            z=1,
            style_ref="node.model",
        ),
        ResolvedObject(
            id="ingest_to_retriever",
            primitive="arrow",
            box=Box(x=480.0, y=395.0, w=300.0, h=10.0),
            z=2,
            style_ref="edge.default",
        ),
        ResolvedObject(
            id="retriever_to_model",
            primitive="arrow",
            box=Box(x=1140.0, y=395.0, w=300.0, h=10.0),
            z=2,
            style_ref="edge.lookup",
        ),
        ResolvedObject(
            id="store_icon",
            primitive="icon",
            box=Box(x=250.0, y=560.0, w=100.0, h=100.0),
            z=1,
            style_ref="node.storage",
        ),
        ResolvedObject(
            id="snippet",
            primitive="code",
            box=Box(x=700.0, y=620.0, w=520.0, h=260.0),
            z=1,
            style_ref="label",
        ),
        ResolvedObject(
            id="score",
            primitive="formula",
            box=Box(x=1440.0, y=620.0, w=360.0, h=140.0),
            z=1,
            style_ref="label",
        ),
    ]
    keyframes = [
        Keyframe(object_id="title", kind="fade_in", start_f=0, end_f=15, easing="ease_in_out"),
        Keyframe(object_id="ingest", kind="fade_in", start_f=15, end_f=30, easing="linear"),
        Keyframe(
            object_id="ingest_to_retriever",
            kind="draw",
            start_f=30,
            end_f=45,
            easing="linear",
        ),
        Keyframe(object_id="retriever", kind="fade_in", start_f=45, end_f=60, easing="spring"),
        Keyframe(object_id="store_icon", kind="move", start_f=60, end_f=80, easing="ease_in_out"),
        Keyframe(
            object_id="retriever_to_model",
            kind="draw",
            start_f=80,
            end_f=95,
            easing="linear",
        ),
        Keyframe(object_id="model", kind="highlight", start_f=95, end_f=120, easing="ease_in_out"),
        Keyframe(object_id="snippet", kind="fade_in", start_f=95, end_f=110, easing="linear"),
        Keyframe(object_id="score", kind="fade_in", start_f=110, end_f=125, easing="linear"),
        Keyframe(object_id="title", kind="fade_out", start_f=150, end_f=165, easing="ease_in_out"),
    ]
    captions = [
        Caption(text="Documents are ingested, retrieved, then scored by the model.", start_f=0, end_f=150),
    ]
    return ConcreteIR(
        fps=FPS,
        resolution=RESOLUTION,
        objects=objects,
        keyframes=keyframes,
        captions=captions,
    )


__all__ = ["FPS", "RESOLUTION", "sample_concrete_ir"]
