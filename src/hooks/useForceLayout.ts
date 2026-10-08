import type { InvestigationNode, InvestigationEdge } from '../types';

interface PositionedNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/**
 * Computes a force-directed graph layout.
 *
 * This is a dependency-free implementation using Coulomb repulsion,
 * Hooke attraction along edges, a gentle centering force, and
 * velocity damping.  Runs synchronously for `iterations` steps and
 * returns the final { x, y } for every node.
 *
 * Parameters are tuned for ~20-50 nodes with ~30-80 edges — the
 * typical scale of a single investigation case.
 */
export function computeForceLayout(
  nodes: InvestigationNode[],
  edges: InvestigationEdge[],
  width: number,
  height: number,
  iterations: number = 350,
): Map<string, { x: number; y: number }> {
  if (nodes.length === 0) return new Map();

  // Build a quick adjacency lookup for counting connections (used for sizing)
  const connectionCount = new Map<string, number>();
  for (const e of edges) {
    connectionCount.set(e.source, (connectionCount.get(e.source) ?? 0) + 1);
    connectionCount.set(e.target, (connectionCount.get(e.target) ?? 0) + 1);
  }

  // Initialise positions in a loose circle so the first frame isn't a mess.
  const pos = new Map<string, PositionedNode>();
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.32;

  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    const r = radius + (Math.random() - 0.5) * 40;
    pos.set(node.id, {
      id: node.id,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      vx: 0,
      vy: 0,
    });
  });

  // Pre-build edge list as [sourcePos, targetPos] for inner loop perf
  const edgeList: [string, string][] = edges
    .filter(e => pos.has(e.source) && pos.has(e.target))
    .map(e => [e.source, e.target]);

  const nodeIds = nodes.map(n => n.id);
  const repulsionStrength = 6000;
  const attractionStrength = 0.008;
  const idealLength = 160;
  const centerStrength = 0.0015;
  const damping = 0.55;

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = 1 - iter / iterations; // cooling

    // --- Repulsion (all pairs) ---
    for (let i = 0; i < nodeIds.length; i++) {
      const a = pos.get(nodeIds[i])!;
      for (let j = i + 1; j < nodeIds.length; j++) {
        const b = pos.get(nodeIds[j])!;
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) dist = 1;
        const force = (repulsionStrength * alpha) / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // --- Attraction along edges ---
    for (const [srcId, tgtId] of edgeList) {
      const a = pos.get(srcId)!;
      const b = pos.get(tgtId)!;
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) dist = 1;
      const force = (dist - idealLength) * attractionStrength * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // --- Centering force ---
    for (const [, p] of pos) {
      p.vx += (cx - p.x) * centerStrength * alpha;
      p.vy += (cy - p.y) * centerStrength * alpha;
    }

    // --- Apply velocity with damping + bounds ---
    const pad = 60;
    for (const [, p] of pos) {
      p.vx *= damping;
      p.vy *= damping;
      p.x += p.vx;
      p.y += p.vy;
      p.x = Math.max(pad, Math.min(width - pad, p.x));
      p.y = Math.max(pad, Math.min(height - pad, p.y));
    }
  }

  const result = new Map<string, { x: number; y: number }>();
  for (const [id, p] of pos) {
    result.set(id, { x: p.x, y: p.y });
  }
  return result;
}
