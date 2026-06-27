"""Feasibility probe: lower the sample Concrete IR to an interactive web bundle.

`.docs/viroc-draft.md` §4.3 names an "interactive web export backend" as a future
target. Unlike the existing HTML adapter (which emits a page that plays a fixed
animation), interactive export adds *viewer-side* controls: a frame scrubber and
play/pause over the resolved storyboard.

The feasibility question is whether this preserves the ADR-0002 emit boundary. It
does: the bundle is pure *source* —

* `timeline.json`: the Concrete IR projected to a frame-addressable timeline
  (objects + per-object keyframe segments), serialized with
  :func:`viroc.core.canonical_json` so it is byte-identical across runs;
* `index.html`: a fixed, framework-free viewer that loads `timeline.json` and
  interpolates each frame in vanilla JS.

Both halves are deterministic functions of the Concrete IR / nothing. The only
environment-dependent part is the browser that *plays* the bundle — squarely to
the right of emit, exactly like render execution. No new dependency: the viewer is
vanilla JS + inline SVG.
"""

from __future__ import annotations

from typing import Any

from viroc.core import canonical_json
from viroc.ir import ConcreteIR

_BUNDLE_NAME = "viroc-interactive-sample"

# Keyframe kinds the vanilla-JS viewer interpolates natively; everything in the
# Concrete IR vocabulary is covered (this is general-purpose JS, not a fixed
# animation schema).
NATIVE_KEYFRAMES = frozenset({"fade_in", "fade_out", "move", "draw", "highlight"})


def unsupported_keyframes(ir: ConcreteIR) -> set[str]:
    """Keyframe kinds the vanilla-JS viewer cannot interpolate (empty for the floor)."""
    return {kf.kind for kf in ir.keyframes} - NATIVE_KEYFRAMES


def total_frames(ir: ConcreteIR) -> int:
    ends = [kf.end_f for kf in ir.keyframes] + [c.end_f for c in ir.captions]
    return max(ends) if ends else 0


def project_timeline(ir: ConcreteIR) -> dict[str, Any]:
    """Project Concrete IR onto a frame-addressable timeline document (pure)."""
    width, height = ir.resolution
    tracks: dict[str, list[dict[str, Any]]] = {}
    for kf in ir.keyframes:
        tracks.setdefault(kf.object_id, []).append(
            {
                "kind": kf.kind,
                "start_f": kf.start_f,
                "end_f": kf.end_f,
                "easing": kf.easing,
            }
        )
    objects = [
        {
            "id": obj.id,
            "primitive": obj.primitive,
            "box": {"x": obj.box.x, "y": obj.box.y, "w": obj.box.w, "h": obj.box.h},
            "z": obj.z,
            "style_ref": obj.style_ref,
            "segments": sorted(
                tracks.get(obj.id, []),
                key=lambda s: (s["start_f"], s["end_f"], s["kind"]),
            ),
        }
        for obj in ir.objects
    ]
    captions = [{"text": c.text, "start_f": c.start_f, "end_f": c.end_f} for c in ir.captions]
    return {
        "name": _BUNDLE_NAME,
        "fps": ir.fps,
        "duration_f": total_frames(ir),
        "resolution": {"w": width, "h": height},
        "objects": objects,
        "captions": captions,
    }


def degradations(ir: ConcreteIR) -> list[str]:
    """Record where the dependency-light viewer falls back to a floor rendering."""
    notes: list[str] = []
    for obj in ir.objects:
        if obj.primitive == "formula":
            notes.append(
                f'object "{obj.id}": primitive "formula" rendered as text '
                "(native math needs an optional KaTeX/MathJax bundle)"
            )
        elif obj.primitive == "icon":
            notes.append(
                f'object "{obj.id}": primitive "icon" rendered as a labeled box '
                "(native icons need an optional icon set)"
            )
    return notes


_VIEWER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>VIROC interactive export (feasibility probe)</title>
<style>
  body { margin: 0; background: #0b1020; color: #e5e7eb; font-family: system-ui, sans-serif; }
  #stage { display: block; width: 100%; height: auto; background: #0b1020; }
  #controls { display: flex; gap: 12px; align-items: center; padding: 12px; }
  #scrub { flex: 1; }
  .obj { fill: #334155; stroke: #94a3b8; stroke-width: 2; }
  .lbl { fill: #e5e7eb; font: 28px system-ui, sans-serif; }
</style>
</head>
<body>
<svg id="stage" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid meet"></svg>
<div id="controls">
  <button id="play" type="button">Play</button>
  <input id="scrub" type="range" min="0" value="0" step="1" />
  <span id="frame">0</span>
</div>
<script>
const SVGNS = "http://www.w3.org/2000/svg";
let timeline = null, frame = 0, playing = false, raf = null;

function easeFrac(seg, f) {
  const span = Math.max(1, seg.end_f - seg.start_f);
  let t = (f - seg.start_f) / span;
  t = Math.max(0, Math.min(1, t));
  if (seg.easing === "linear") return t;
  return t * t * (3 - 2 * t); // smoothstep for ease_in_out / spring (degraded)
}

function stateFor(obj, f) {
  let opacity = 1, dx = 0, scale = 1, drawn = 1;
  for (const seg of obj.segments) {
    const k = easeFrac(seg, f);
    const active = f >= seg.start_f;
    if (seg.kind === "fade_in") opacity = active ? k : 0;
    else if (seg.kind === "fade_out") opacity = active ? 1 - k : 1;
    else if (seg.kind === "move") dx = active ? (1 - k) * -40 : -40;
    else if (seg.kind === "draw") drawn = active ? k : 0;
    else if (seg.kind === "highlight") scale = active ? 1 + 0.1 * Math.sin(k * Math.PI) : 1;
  }
  return { opacity, dx, scale, drawn };
}

function render(f) {
  const stage = document.getElementById("stage");
  stage.innerHTML = "";
  const objs = [...timeline.objects].sort((a, b) => a.z - b.z);
  for (const obj of objs) {
    const st = stateFor(obj, f);
    const g = document.createElementNS(SVGNS, "g");
    g.setAttribute("opacity", st.opacity.toFixed(3));
    const cx = obj.box.x + obj.box.w / 2 + st.dx;
    const cy = obj.box.y + obj.box.h / 2;
    g.setAttribute("transform", `translate(${cx} ${cy}) scale(${st.scale.toFixed(3)})`);
    if (obj.primitive === "text") {
      const t = document.createElementNS(SVGNS, "text");
      t.setAttribute("class", "lbl");
      t.setAttribute("text-anchor", "middle");
      t.textContent = obj.id;
      g.appendChild(t);
    } else {
      const r = document.createElementNS(SVGNS, "rect");
      r.setAttribute("class", "obj");
      r.setAttribute("x", (-obj.box.w / 2).toFixed(1));
      r.setAttribute("y", (-obj.box.h / 2).toFixed(1));
      r.setAttribute("width", (obj.box.w * st.drawn).toFixed(1));
      r.setAttribute("height", obj.box.h.toFixed(1));
      g.appendChild(r);
    }
    stage.appendChild(g);
  }
  document.getElementById("frame").textContent = String(f);
  document.getElementById("scrub").value = String(f);
}

function tick() {
  if (!playing) return;
  frame = (frame + 1) % (timeline.duration_f + 1);
  render(frame);
  raf = requestAnimationFrame(tick);
}

async function main() {
  timeline = await (await fetch("timeline.json")).json();
  document.getElementById("scrub").max = String(timeline.duration_f);
  document.getElementById("scrub").addEventListener("input", (e) => {
    playing = false; frame = Number(e.target.value); render(frame);
  });
  document.getElementById("play").addEventListener("click", () => {
    playing = !playing;
    document.getElementById("play").textContent = playing ? "Pause" : "Play";
    if (playing) tick(); else if (raf) cancelAnimationFrame(raf);
  });
  render(0);
}
main();
</script>
</body>
</html>
"""


def viewer_html() -> str:
    """Return the fixed, framework-free viewer (deterministic)."""
    return _VIEWER_HTML


def export_bundle(ir: ConcreteIR) -> dict[str, str]:
    """Return the deterministic {filename: content} interactive web bundle."""
    return {
        "index.html": viewer_html(),
        "timeline.json": f"{canonical_json(project_timeline(ir))}\n",
    }


def export_json(ir: ConcreteIR) -> str:
    """Serialize the whole bundle as canonical JSON for a single stable digest."""
    return f"{canonical_json(export_bundle(ir))}\n"


__all__ = [
    "NATIVE_KEYFRAMES",
    "degradations",
    "export_bundle",
    "export_json",
    "project_timeline",
    "total_frames",
    "unsupported_keyframes",
    "viewer_html",
]
