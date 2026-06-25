// Remotion Skills (agent -> React) -- topic: ci-cd-pipeline.
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
  { id: "commit", label: "Commit", color: "#3b82f6" },
  { id: "build", label: "Build", color: "#f59e0b" },
  { id: "test", label: "Test", color: "#f59e0b" },
  { id: "package", label: "Package", color: "#14b8a6" },
  { id: "deploy", label: "Deploy", color: "#22c55e" },
];

const EDGES: Edge[] = [
  { from: "commit", to: "build", color: "#8b949e" },
  { from: "build", to: "test", color: "#8b949e" },
  { from: "test", to: "package", color: "#34d399" },
  { from: "package", to: "deploy", color: "#4ade80" },
];

const BOX_W = 220;
const BOX_H = 96;
const GAP = 60;
const TITLE = 'A CI/CD Pipeline';
const NARRATION =
  'A commit triggers a build; the build is tested, packaged, and deployed.';

const xOf = (index: number, total: number, width: number): number => {
  const rowWidth = total * BOX_W + (total - 1) * GAP;
  return (width - rowWidth) / 2 + index * (BOX_W + GAP);
};

export const CiCdPipeline: React.FC = () => {
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
          const adjacent = b - a === 1;
          if (adjacent) {
            return (
              <line
                key={edge.from + edge.to}
                x1={x1}
                y1={y}
                x2={x1 + (x2 - x1) * reveal}
                y2={y}
                stroke={edge.color}
                strokeWidth={3}
              />
            );
          }
          const dip = b > a ? BOX_H : -BOX_H;
          const midX = (xOf(a, NODES.length, width) + BOX_W / 2 + xOf(b, NODES.length, width) + BOX_W / 2) / 2;
          const d = `M ${xOf(a, NODES.length, width) + BOX_W / 2} ${y + BOX_H / 2} Q ${midX} ${y + BOX_H / 2 + dip} ${xOf(b, NODES.length, width) + BOX_W / 2} ${y + BOX_H / 2}`;
          return (
            <path
              key={edge.from + edge.to}
              d={d}
              fill="none"
              stroke={edge.color}
              strokeWidth={3}
              strokeDasharray={600}
              strokeDashoffset={600 * (1 - reveal)}
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
