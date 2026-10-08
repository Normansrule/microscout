// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Quick benchmark: PID, LQR and MPC on four courses, with wall-clock time. node docs/lab/test/bench.mjs
import { buildCourse } from "../js/world.js";
import { Quad } from "../js/physics.js";
import { Mission, CONTROLLERS, lqrGains } from "../js/control.js";

function fly(kind, course, T = 25, opts = {}) {
  const c = buildCourse(course, 1);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], -1.0]);
  q.thrust = [1, 1, 1, 1].map(() => q.mass * 9.81 / 4);
  const m = new Mission(c);
  const ctl = CONTROLLERS[kind].make(q, m, opts);
  const dt = 0.002;
  const t0 = performance.now();
  while (q.t < T && !m.done) { const prev = [...q.pos]; q.step(ctl.update(dt), dt); m.update(prev, q.pos); }
  return { done: m.done, i: m.i, t: q.t.toFixed(2), impact: q.maxImpact.toFixed(2), pos: q.pos.map((x) => x.toFixed(2)).join(","), ms: (performance.now() - t0).toFixed(0) };
}
console.log("LQR K", lqrGains(4, 1, 0.3));
for (const k of ["pid", "lqr", "mpc"]) for (const c of ["gates", "forest", "window", "hover"]) console.log(k, c, JSON.stringify(fly(k, c)));
