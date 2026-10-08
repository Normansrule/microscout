// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Courses for the Flight Lab: rooms, obstacles, gates, ray casting (the drone's ToF sensors)
// and distance queries (for the MPC planner). World frame NED: x forward, y right, z down (z<0 is up).

import { clamp, rng } from "./math.js";

export const DRONE_RADIUS = 0.075;   // ducts: 95 mm motor-to-motor + 56 mm duct -> ~150 mm across (concept CAD)
export const TOF_RANGE = 4.0;        // VL53L1X / VL53L5CX long-distance mode (ST datasheets)

// Body-frame ray directions (FRD): an 8-ray forward fan like the VL53L5CX's columns (~45 deg wide),
// plus left, right, rear (VL53L1X satellites) and down (Flow deck).
export const RAYS = (() => {
  const r = [];
  for (let i = 0; i < 8; i++) {
    const a = ((i - 3.5) / 3.5) * (22.5 * Math.PI / 180);
    r.push({ name: `front${i}`, d: [Math.cos(a), Math.sin(a), 0] });
  }
  r.push({ name: "left", d: [0, -1, 0] }, { name: "right", d: [0, 1, 0] }, { name: "rear", d: [-1, 0, 0] }, { name: "down", d: [0, 0, 1] });
  return r;
})();

function gateBoxes(g) {
  // a square frame standing on legs; g: {c:[x,y,z] centre of the opening, yaw, w, h, t}
  const t = g.t || 0.06, hw = g.w / 2, hh = g.h / 2;
  const cy = Math.cos(g.yaw), sy = Math.sin(g.yaw);
  // only axis-aligned gates are supported (yaw 0 or 90 deg): build AABBs
  const along = Math.abs(sy) > 0.5;   // gate plane normal along y
  const mk = (u0, u1, z0, z1) => {
    const [x0, x1] = along ? [g.c[0] + u0, g.c[0] + u1] : [g.c[0] - t / 2, g.c[0] + t / 2];
    const [y0, y1] = along ? [g.c[1] - t / 2, g.c[1] + t / 2] : [g.c[1] + u0, g.c[1] + u1];
    return { type: "box", min: [Math.min(x0, x1), Math.min(y0, y1), Math.min(z0, z1)], max: [Math.max(x0, x1), Math.max(y0, y1), Math.max(z0, z1)], gate: true };
  };
  void cy;
  const top = g.c[2] - hh, bot = g.c[2] + hh;
  return [
    mk(-hw - t, hw + t, top - t, top),            // top bar
    mk(-hw - t, hw + t, bot, bot + t),            // bottom bar
    mk(-hw - t, -hw, top - t, 0),                 // left post to the floor
    mk(hw, hw + t, top - t, 0),                   // right post to the floor
  ];
}

export function buildCourse(name, seed = 1, randomize = false) {
  const R = rng(seed);
  const j = (s) => (randomize ? (R() - 0.5) * 2 * s : 0);
  const c = { name, room: [12, 6, 3.2], obstacles: [], gates: [], start: [-5, 0, 0], goal: null, timeLimit: 20, wind: [0, 0, 0] };
  if (name === "hover") {
    c.room = [8, 8, 3.2];
    c.start = [0, 0, 0];
    c.waypoints = [[0, 0, -1.2]];
    c.hold = true;
    c.timeLimit = 15;
  } else if (name === "gates") {
    const ys = [1.4, -1.4, 1.4, -1.2, 0];
    const xs = [-3, -1, 1, 3, 5];
    for (let i = 0; i < 5; i++) {
      const g = { c: [xs[i] + j(0.2), ys[i] + j(0.5), -1.2 + j(0.3)], yaw: 0, w: 0.9, h: 0.9 };
      c.gates.push(g);
    }
    c.waypoints = []; c.wpGate = [];
    c.gates.forEach((g, k) => {          // line up 0.7 m before each gate, then aim 0.5 m past it
      c.waypoints.push([g.c[0] - 0.7, g.c[1], g.c[2]], [g.c[0] + 0.5, g.c[1], g.c[2]]);
      c.wpGate.push(-1, k);
    });
    c.timeLimit = 25;
  } else if (name === "forest") {
    const n = 14;
    let tries = 0;
    while (c.obstacles.filter((o) => o.type === "cyl").length < n && tries++ < 500) {
      const x = -3.2 + R() * 6.4, y = -2.6 + R() * 5.2, r = 0.12 + R() * 0.18;
      if (c.obstacles.some((o) => o.type === "cyl" && Math.hypot(o.c[0] - x, o.c[1] - y) < o.r + r + 0.55)) continue;
      c.obstacles.push({ type: "cyl", c: [x, y], r, h: 3.2 });
    }
    c.goal = [5, j(1.5), -1.2];
    c.waypoints = [c.goal];
  } else if (name === "window") {
    const wy = j(1.6), wz = -1.3 + j(0.5);
    const hw = 0.38;
    const x0 = 0, x1 = 0.15, W = c.room[1] / 2, H = c.room[2];
    c.obstacles.push(
      { type: "box", min: [x0, -W, -H], max: [x1, wy - hw, 0] },
      { type: "box", min: [x0, wy + hw, -H], max: [x1, W, 0] },
      { type: "box", min: [x0, wy - hw, -H], max: [x1, wy + hw, wz - hw] },
      { type: "box", min: [x0, wy - hw, wz + hw], max: [x1, wy + hw, 0] },
    );
    c.window = { y: wy, z: wz, hw };
    c.goal = [5, j(1.5), -1.2];
    c.waypoints = [[-0.8, wy, wz], [1.0, wy, wz], c.goal];
  } else {          // "hangar": free flight with a few crates
    c.room = [14, 10, 4];
    c.start = [0, 0, 0];
    c.obstacles.push(
      { type: "box", min: [2, -3, -0.8], max: [3, -2, 0] },
      { type: "box", min: [-4, 2, -1.6], max: [-3, 3.5, 0] },
      { type: "cyl", c: [3, 3], r: 0.3, h: 4 },
      { type: "cyl", c: [-2, -3], r: 0.25, h: 4 },
    );
    c.gates.push({ c: [5, 0, -1.4], yaw: 0, w: 1.0, h: 1.0 }, { c: [-5, -2, -1.2], yaw: 0, w: 1.0, h: 1.0 });
    c.waypoints = [[0, 0, -1.2]];
    c.free = true;
    c.timeLimit = 1e9;
  }
  for (const g of c.gates) c.obstacles.push(...gateBoxes(g));
  return c;
}

export const COURSES = [
  ["gates", "Gate slalom", "Fly through five gates in order."],
  ["forest", "Pillar forest", "Reach the far wall through random pillars."],
  ["window", "Window wall", "Find the window in a wall and fly through it."],
  ["hover", "Hold in gusts", "Hold a point at 1.2 m while the wind gusts."],
  ["hangar", "Open hangar", "Free flight with crates, pillars and two gates."],
];

// ------------------------------------------------------------------ geometry
function rayBox(o, d, b) {
  let t0 = 0, t1 = Infinity;
  for (let i = 0; i < 3; i++) {
    if (Math.abs(d[i]) < 1e-12) { if (o[i] < b.min[i] || o[i] > b.max[i]) return Infinity; continue; }
    let ta = (b.min[i] - o[i]) / d[i], tb = (b.max[i] - o[i]) / d[i];
    if (ta > tb) { const s = ta; ta = tb; tb = s; }
    if (ta > t0) t0 = ta;
    if (tb < t1) t1 = tb;
    if (t0 > t1) return Infinity;
  }
  return t0 > 0 ? t0 : Infinity;
}
function rayCyl(o, d, c) {
  const ox = o[0] - c.c[0], oy = o[1] - c.c[1];
  const a = d[0] * d[0] + d[1] * d[1];
  if (a < 1e-12) return Infinity;
  const b = 2 * (ox * d[0] + oy * d[1]), cc = ox * ox + oy * oy - c.r * c.r;
  const disc = b * b - 4 * a * cc;
  if (disc < 0) return Infinity;
  const t = (-b - Math.sqrt(disc)) / (2 * a);
  if (t <= 0) return Infinity;
  const z = o[2] + d[2] * t;
  return z <= 0 && z >= -c.h ? t : Infinity;
}

/** Distance along unit direction d (world) from point o to the nearest surface, capped at range. */
export function castRay(course, o, d, range = TOF_RANGE) {
  let best = range;
  const [L, W, H] = course.room;
  const planes = [[0, L / 2], [0, -L / 2], [1, W / 2], [1, -W / 2], [2, 0], [2, -H]];
  for (const [ax, v] of planes) {
    if (Math.abs(d[ax]) < 1e-12) continue;
    const t = (v - o[ax]) / d[ax];
    if (t > 0 && t < best) best = t;
  }
  for (const ob of course.obstacles) {
    const t = ob.type === "box" ? rayBox(o, d, ob) : rayCyl(o, d, ob);
    if (t < best) best = t;
  }
  return best;
}

/** Signed clearance from point p to the nearest obstacle or room surface (m). */
export function clearance(course, p) {
  const [L, W, H] = course.room;
  let best = Math.min(L / 2 - Math.abs(p[0]), W / 2 - Math.abs(p[1]), -p[2], H + p[2]);
  for (const ob of course.obstacles) {
    let d;
    if (ob.type === "box") {
      let s = 0, inside = true, maxin = -Infinity;
      for (let i = 0; i < 3; i++) {
        const lo = ob.min[i] - p[i], hi = p[i] - ob.max[i];
        const e = Math.max(lo, hi);
        if (e > 0) { s += e * e; inside = false; }
        maxin = Math.max(maxin, e);
      }
      d = inside ? maxin : Math.sqrt(s);
    } else {
      const r2 = Math.hypot(p[0] - ob.c[0], p[1] - ob.c[1]) - ob.r;
      const above = -ob.h - p[2];
      d = above > 0 ? Math.hypot(Math.max(r2, 0), above) : r2;
    }
    if (d < best) best = d;
  }
  return best;
}

/** Push a sphere out of obstacles; returns the impact speed of the worst contact (0 if none). */
export function resolveCollisions(course, pos, vel, radius = DRONE_RADIUS, restitution = 0.25) {
  let impact = 0;
  for (const ob of course.obstacles) {
    let n = null, pen = 0;
    if (ob.type === "box") {
      const q = [clamp(pos[0], ob.min[0], ob.max[0]), clamp(pos[1], ob.min[1], ob.max[1]), clamp(pos[2], ob.min[2], ob.max[2])];
      const dx = pos[0] - q[0], dy = pos[1] - q[1], dz = pos[2] - q[2];
      const dist = Math.hypot(dx, dy, dz);
      if (dist < radius) {
        if (dist > 1e-9) { n = [dx / dist, dy / dist, dz / dist]; pen = radius - dist; }
        else {      // centre inside the box: push out along the smallest overlap
          let bi = 0, bv = Infinity, bs = 1;
          for (let i = 0; i < 3; i++) {
            const a = pos[i] - ob.min[i], b = ob.max[i] - pos[i];
            if (a < bv) { bv = a; bi = i; bs = -1; }
            if (b < bv) { bv = b; bi = i; bs = 1; }
          }
          n = [0, 0, 0]; n[bi] = bs; pen = bv + radius;
        }
      }
    } else if (pos[2] > -ob.h - radius) {
      const dx = pos[0] - ob.c[0], dy = pos[1] - ob.c[1];
      const dist = Math.hypot(dx, dy);
      if (dist < ob.r + radius && dist > 1e-9) { n = [dx / dist, dy / dist, 0]; pen = ob.r + radius - dist; }
    }
    if (n) {
      for (let i = 0; i < 3; i++) pos[i] += n[i] * pen;
      const vn = vel[0] * n[0] + vel[1] * n[1] + vel[2] * n[2];
      if (vn < 0) {
        impact = Math.max(impact, -vn);
        for (let i = 0; i < 3; i++) vel[i] -= (1 + restitution) * vn * n[i];
        for (let i = 0; i < 3; i++) vel[i] *= 0.7;     // ducts scrape along the surface
      }
    }
  }
  return impact;
}

/** Did the segment a->b pass through gate g's opening? */
export function passedGate(g, a, b) {
  if (a[0] < g.c[0] && b[0] >= g.c[0]) {
    const t = (g.c[0] - a[0]) / (b[0] - a[0]);
    const y = a[1] + t * (b[1] - a[1]), z = a[2] + t * (b[2] - a[2]);
    return Math.abs(y - g.c[1]) < g.w / 2 && Math.abs(z - g.c[2]) < g.h / 2;
  }
  return false;
}
