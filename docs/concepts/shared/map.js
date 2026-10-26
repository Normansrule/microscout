// SPDX-License-Identifier: MIT
// Draws the synthetic follow-me scene from data.js as SVG strings. Each concept passes its own palette and
// decides what to show; the geometry is shared so the three mockups describe the same moment.

import { SNAPSHOT as S } from "./data.js";

/** World (m, x east / y north) to screen (px) for a view centred on c, `scale` px per metre. */
export function view(w, h, c, scale) {
  return { w, h, X: (p) => w / 2 + (p[0] - c[0]) * scale, Y: (p) => h / 2 - (p[1] - c[1]) * scale, scale };
}

export const pathD = (v, pts) => pts.map((p, i) => `${i ? "L" : "M"}${v.X(p).toFixed(1)} ${v.Y(p).toFixed(1)}`).join(" ");

/** A synthetic cliff-top coastline: land below/right of the curve, sea above/left. */
export function coast(v) {
  const pts = [];
  for (let x = -90; x <= 90; x += 4) pts.push([x, 14 + 0.004 * x * x + 3.2 * Math.sin(x / 9) + 1.4 * Math.sin(x / 3.1)]);
  const sea = `${pathD(v, pts)} L${v.X([90, 200]).toFixed(1)} ${v.Y([90, 200]).toFixed(1)} L${v.X([-90, 200]).toFixed(1)} ${v.Y([-90, 200]).toFixed(1)} Z`;
  return { line: pathD(v, pts), sea };
}

/** Second ticks along a path, perpendicular, for a chart-like time scale. */
export function ticks(v, pts, every = 5, len = 5) {
  const out = [];
  for (let i = every; i < pts.length - 1; i += every) {
    const a = pts[i - 1], b = pts[i + 1];
    const dx = v.X(b) - v.X(a), dy = v.Y(b) - v.Y(a), n = Math.hypot(dx, dy) || 1;
    const x = v.X(pts[i]), y = v.Y(pts[i]);
    out.push(`M${(x - (dy / n) * len).toFixed(1)} ${(y + (dx / n) * len).toFixed(1)} L${(x + (dy / n) * len).toFixed(1)} ${(y - (dx / n) * len).toFixed(1)}`);
  }
  return out.join(" ");
}

/** A ToF cone from the drone along a bearing (deg from north) with a range (m). */
export function cone(v, from, bearing, range, half = 13.5) {
  const r = (d) => (d * Math.PI) / 180;
  const p1 = [from[0] + range * Math.sin(r(bearing - half)), from[1] + range * Math.cos(r(bearing - half))];
  const p2 = [from[0] + range * Math.sin(r(bearing + half)), from[1] + range * Math.cos(r(bearing + half))];
  return `M${v.X(from)} ${v.Y(from)} L${v.X(p1)} ${v.Y(p1)} L${v.X(p2)} ${v.Y(p2)} Z`;
}

/** A small arrowhead (triangle) at p pointing along bearing deg. */
export function arrow(v, p, bearing, size = 9) {
  const r = (bearing * Math.PI) / 180;
  const x = v.X(p), y = v.Y(p);
  const f = [Math.sin(r), -Math.cos(r)], s = [Math.cos(r), Math.sin(r)];
  return `M${(x + f[0] * size).toFixed(1)} ${(y + f[1] * size).toFixed(1)} L${(x - f[0] * size * 0.7 + s[0] * size * 0.7).toFixed(1)} ${(y - f[1] * size * 0.7 + s[1] * size * 0.7).toFixed(1)} L${(x - f[0] * size * 0.3).toFixed(1)} ${(y - f[1] * size * 0.3).toFixed(1)} L${(x - f[0] * size * 0.7 - s[0] * size * 0.7).toFixed(1)} ${(y - f[1] * size * 0.7 - s[1] * size * 0.7).toFixed(1)} Z`;
}

export { S };
