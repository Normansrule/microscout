// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Flies every autopilot on many course layouts with the same rules as the Autopilot tab and writes
// docs/data/lab_controllers.json (used by tools/viz/lab_charts.py). Simulation only.
//   node docs/lab/test/compare.mjs [layouts=20]
import { readFileSync, writeFileSync } from "node:fs";
import { buildCourse } from "../js/world.js";
import { Quad } from "../js/physics.js";
import { Mission, CONTROLLERS } from "../js/control.js";
import { Policy } from "../js/policy.js";
import { toEuler } from "../js/math.js";

const N = +(process.argv[2] || 20);
const courses = ["gates", "forest", "window"];
const kinds = ["pid", "lqr", "mpc", "smpc", "learned"];
const policy = (c) => { const j = JSON.parse(readFileSync(new URL(`../policies/${c}-cem-linear.json`, import.meta.url))); const p = Policy.fromJSON(j); p.meta = j; return p; };

function run(kind, cname, seed) {
  const course = buildCourse(cname, seed, cname !== "gates");
  const q = new Quad(course);
  q.reset([course.start[0], course.start[1], -1.0]);
  q.thrust = [0, 1, 2, 3].map(() => (q.mass * 9.81) / 4);
  const m = new Mission(course);
  const opts = kind === "learned" ? (() => { const p = policy(cname); return { policy: p, actionMode: p.meta?.config?.actionMode || "velocity" }; })() : {};
  const ctl = CONTROLLERS[kind].make(q, m, opts);
  const dt = 0.002;
  for (;;) {
    const prev = [...q.pos];
    q.step(ctl.update(dt), dt);
    m.update(prev, q.pos);
    const [r, p] = toEuler(q.q);
    if (m.done) return { status: "done", t: q.t, hit: q.maxImpact };
    if (q.maxImpact > 1.5 || Math.max(Math.abs(r), Math.abs(p)) > 1.4 || (q.onGround && q.t > 1.5)) return { status: "crashed", t: q.t, hit: q.maxImpact };
    if (q.t > course.timeLimit) return { status: "timed out", t: q.t, hit: q.maxImpact };
  }
}

const out = { note: "Simulation with estimated parameters (docs/lab). Not a measurement.", layouts: N, results: {} };
for (const c of courses) {
  out.results[c] = {};
  for (const k of kinds) {
    const rs = [];
    for (let s = 1; s <= (c === "gates" ? 1 : N); s++) rs.push(run(k, c, 1000 + s));
    const ok = rs.filter((r) => r.status === "done");
    out.results[c][k] = {
      runs: rs.length, finished: ok.length / rs.length,
      meanTime: ok.length ? ok.reduce((a, r) => a + r.t, 0) / ok.length : null,
      touched: rs.filter((r) => r.hit > 0.05).length / rs.length,
      clean: rs.filter((r) => r.status === "done" && r.hit <= 0.05).length / rs.length,
    };
    console.log(c.padEnd(7), k.padEnd(8), JSON.stringify(out.results[c][k]));
  }
}
writeFileSync(new URL("../../data/lab_controllers.json", import.meta.url), JSON.stringify(out, null, 1));
