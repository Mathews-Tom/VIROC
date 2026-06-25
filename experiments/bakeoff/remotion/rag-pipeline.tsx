// Remotion Skills (agent -> React) -- bake-off approach 2, topic: rag-pipeline.
// The intermediate the engineer edits is a React/TSX composition: readable, but
// not mechanically checkable. Node positions, timings, and arrows are imperative
// TypeScript; a dangling reference or overlapping box is a runtime/visual bug,
// not a validation error.
import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type Node = { id: string; label: string; color: string };
type Edge = { from: string; to: string; color: string };

const NODES: Node[] = [
  { id: "documents", label: "Documents", color: "#3b82f6" },
  { id: "chunks", label: "Chunks", color: "#14b8a6" },
  { id: "embedder", label: "Embedding Model", color: "#a855f7" },
  { id: "vector_db", label: "Vector DB", color: "#22c55e" },
  { id: "llm", label: "LLM", color: "#a855f7" },
];

const EDGES: Edge[] = [
  { from: "documents", to: "chunks", color: "#60a5fa" },
  { from: "chunks", to: "embedder", color: "#34d399" },
  { from: "embedder", to: "vector_db", color: "#4ade80" },
  { from: "vector_db", to: "llm", color: "#8b949e" },
];

const BOX_W = 220;
const BOX_H = 96;
const GAP = 60;
const TITLE = "How Retrieval-Augmented Generation Works";
const NARRATION =
  "Documents are chunked, embedded, stored in a vector database, and retrieved to ground the LLM.";

const xOf = (index: number, total: number, width: number): number => {
  const rowWidth = total * BOX_W + (total - 1) * GAP;
  return (width - rowWidth) / 2 + index * (BOX_W + GAP);
};

export const RagPipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const rowY = height / 2 - BOX_H / 2;
  const indexOf = Object.fromEntries(NODES.map((n, i) => [n.id, i]));

  return (
    <AbsoluteFill style={{ backgroundColor: "#0e1116", fontFamily: "Inter, sans-serif" }}>
      <div style={{ color: "#e6edf3", fontSize: 34, textAlign: "center", marginTop: 64 }}>
        {TITLE}
      </div>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        {EDGES.map((edge, i) => {
          const a = indexOf[edge.from];
          const b = indexOf[edge.to];
          const x1 = xOf(a, NODES.length, width) + BOX_W;
          const x2 = xOf(b, NODES.length, width);
          const y = rowY + BOX_H / 2;
          const reveal = interpolate(frame, [20 + i * 8, 30 + i * 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <line
              key={edge.from + edge.to}
              x1={x1}
              y1={y}
              x2={x1 + (x2 - x1) * reveal}
              y2={y}
              stroke={edge.color}
              strokeWidth={3}
              markerEnd="url(#arrow)"
            />
          );
        })}
      </svg>
      {NODES.map((node, i) => {
        const enter = spring({ frame: frame - i * 6, fps, config: { damping: 18 } });
        const x = xOf(i, NODES.length, width);
        return (
          <div
            key={node.id}
            style={{
              position: "absolute",
              left: x,
              top: rowY + (1 - enter) * 24,
              width: BOX_W,
              height: BOX_H,
              opacity: enter,
              borderRadius: 12,
              border: `2px solid ${node.color}`,
              backgroundColor: `${node.color}2e`,
              color: "#e6edf3",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              fontSize: 18,
              padding: 8,
              boxSizing: "border-box",
            }}
          >
            {node.label}
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          bottom: 96,
          width: "100%",
          textAlign: "center",
          color: "#8b949e",
          fontSize: 18,
          opacity: interpolate(frame, [70, 85], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        {NARRATION}
      </div>
    </AbsoluteFill>
  );
};
