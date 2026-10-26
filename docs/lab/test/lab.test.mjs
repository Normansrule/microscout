// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Regression tests for the Flight Lab simulation (run: node --test docs/lab/test/lab.test.mjs).
// They check that the simulator and controllers behave as they did when the lab was written.
// Passing says nothing about how a real MicroScout will fly.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildCourse, castRay, COURSES, sanitizeSpec } from "../js/world.js";
import { Quad } from "../js/physics.js";
import { Mission, CONTROLLERS, PilotController, lqrGains } from "../js/control.js";
import { Policy, OBS_DIM } from "../js/policy.js";
import { Trainer, DEFAULT_TRAIN } from "../js/rl.js";
import { toEuler } from "../js/math.js";

function fly(kind, courseName, opts = {}, T = 25) {
  const c = buildCourse(courseName, 1);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], -1.0]);
  q.thrust = [1, 1, 1, 1].map(() => (q.mass * 9.81) / 4);
  const m = new Mission(c);
  const ctl = CONTROLLERS[kind].make(q, m, opts);
  const dt = 0.002;
  while (q.t < T && !m.done) { const prev = [...q.pos]; q.step(ctl.update(dt), dt); m.update(prev, q.pos); }
  return { done: m.done, t: q.t, impact: q.maxImpact, q };
}

test("every course builds and its rays hit something inside the room", () => {
  for (const [name] of COURSES) {
    const c = buildCourse(name, 3, true);
    assert.ok(c.waypoints.length > 0, name);
    const d = castRay(c, [0, 0, -1], [0, 0, 1], 4);     // straight down from 1 m
    assert.ok(Math.abs(d - 1) < 0.05, `${name}: floor at ${d}`);
  }
});

test("LQR gains for the double integrator are positive and stable", () => {
  const [kp, kd] = lqrGains(4, 1, 0.3);
  assert.ok(kp > 0 && kd > 0);
  assert.ok(Math.abs(kp - 3.53) < 0.05 && Math.abs(kd - 3.19) < 0.05, `K = ${kp}, ${kd}`);
});

for (const kind of ["pid", "lqr", "mpc"]) {
  test(`${kind} flies the gate slalom without touching anything`, () => {
    const r = fly(kind, "gates");
    assert.ok(r.done, `${kind} did not finish (t = ${r.t})`);
    assert.ok(r.impact < 0.05, `${kind} hit something at ${r.impact} m/s`);
  });
}

test("MPC gets through the forest without a hit (seed 1)", () => {
  const r = fly("mpc", "forest");
  assert.ok(r.done && r.impact < 0.05, `done ${r.done}, impact ${r.impact}`);
});

test("bundled policies load and the gate policy finishes the gate slalom", () => {
  for (const name of ["gates", "forest", "window"]) {
    const j = JSON.parse(readFileSync(new URL(`../policies/${name}-cem-linear.json`, import.meta.url)));
    const p = Policy.fromJSON(j);
    assert.equal(p.net.sizes[0], OBS_DIM);
    assert.ok(Array.from(p.net.params).every(Number.isFinite), name);
  }
  const j = JSON.parse(readFileSync(new URL("../policies/gates-cem-linear.json", import.meta.url)));
  const r = fly("learned", "gates", { policy: Policy.fromJSON(j), actionMode: j.config?.actionMode ?? "velocity" });
  assert.ok(r.done && r.impact < 0.3, `done ${r.done}, impact ${r.impact}`);
});

test("pilot: take off to about 1.2 m, back flip, recover without a hit", () => {
  const c = buildCourse("hangar", 1);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], 0], 0);
  const p = new PilotController(q);
  p.mode = "sport";
  p.arm();
  const dt = 0.002, sticks = { roll: 0, pitch: 0, yaw: 0, throttle: 0.5 };
  const run = (T) => { const end = q.t + T; while (q.t < end) { p.setSticks(sticks, q.t); q.step(p.update(dt), dt); } };
  run(3);
  assert.ok(Math.abs(q.height - 1.2) < 0.1, `height after take-off ${q.height}`);
  p.flip("back");
  let maxTilt = 0;
  const end = q.t + 2.5;
  while (q.t < end) { p.setSticks(sticks, q.t); q.step(p.update(dt), dt); const [r, pt] = toEuler(q.q); maxTilt = Math.max(maxTilt, Math.abs(r), Math.abs(pt)); }
  assert.ok(maxTilt > 2.5, `never went past ${maxTilt} rad - no flip`);
  assert.ok(q.height > 0.4 && q.maxImpact < 0.05, `height ${q.height}, impact ${q.maxImpact}`);
  assert.ok(p.msgs.includes("flip complete"), p.msgs.join(" / "));
});

test("pilot: losing the radio holds position, then lands", () => {
  const c = buildCourse("hangar", 1);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], 0], 0);
  const p = new PilotController(q);
  p.arm();
  const dt = 0.002;
  while (q.t < 3) { p.setSticks({ roll: 0, pitch: 0, yaw: 0, throttle: 0.5 }, q.t); q.step(p.update(dt), dt); }
  while (q.t < 14) q.step(p.update(dt), dt);         // no more stick packets
  assert.ok(q.height < 0.1, `still at ${q.height} m`);
  assert.ok(q.maxImpact < 1.0, `landed at ${q.maxImpact} m/s`);
});

test("CEM from the PD prior improves the validation return on the gate slalom", () => {
  const t = new Trainer({ ...DEFAULT_TRAIN, trainer: "cem", init: "pd", population: 16, randomize: false, seed: 3 });
  const first = t.iterate();
  let last = first;
  for (let i = 0; i < 7; i++) last = t.iterate();
  assert.ok(Number.isFinite(last.stats.val));
  assert.ok(t.best.ret >= first.stats.val, `best ${t.best.ret} < first ${first.stats.val}`);
  assert.ok(last.stats.success > 0 || t.best.ret > 50, `no progress: ${JSON.stringify(last.stats)}`);
});

test("sensor-only MPC: builds its map from ToF hits and gets through the gate slalom", () => {
  const r = fly("smpc", "gates");
  assert.ok(r.done && r.impact < 0.05, `done ${r.done}, impact ${r.impact}`);
});

test("sensor-only MPC plans from its ToF hit map, not the course's obstacle list", () => {
  const c = buildCourse("forest", 2, true);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], -1.0]);
  const m = new Mission(c);
  const ctl = CONTROLLERS.smpc.make(q, m, {});
  for (let i = 0; i < 1500; i++) q.step(ctl.update(0.002), 0.002);
  assert.ok(ctl.map.n > 0, "no ToF hits recorded");
  // Far from anything the rays have hit, its clearance is just height above the floor (capped at one map cell),
  // even inside a pillar it has not seen.
  const unseen = c.obstacles.find((o) => o.type !== "box" && ctl.map.near([o.c[0], o.c[1], -1]) >= ctl.map.cell);
  if (unseen) assert.ok(ctl.clearanceAt([unseen.c[0], unseen.c[1], -1]) > 0, "it knew about an unseen pillar");
});

test("course editor: specs are clamped, the take-off spot stays clear, and MPC flies the result", () => {
  const sp = sanitizeSpec({ pillars: [[-5, 0, 0.2], [99, 0, 9], [0, 1.5, 0.2]], crates: [], gates: [[2, -0.5, -1.2]], goal: [5, 0, -1.2] });
  assert.equal(sp.pillars.length, 2, "pillar on the take-off spot should be dropped");
  assert.ok(sp.pillars.every(([x, , r]) => Math.abs(x) <= 5.8 && r <= 0.5));
  const c = buildCourse("custom", 1, false, sp);
  assert.equal(c.gates.length, 1);
  assert.equal(c.waypoints.length, 3);          // line up, through the gate, goal
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], -1.0]);
  q.thrust = [1, 1, 1, 1].map(() => (q.mass * 9.81) / 4);
  const m = new Mission(c);
  const ctl = CONTROLLERS.mpc.make(q, m, {});
  while (q.t < 30 && !m.done) { const prev = [...q.pos]; q.step(ctl.update(0.002), 0.002); m.update(prev, q.pos); }
  assert.ok(m.done && m.gatesPassed === 1 && q.maxImpact < 0.05, `done ${m.done}, gates ${m.gatesPassed}, impact ${q.maxImpact}`);
});

// ------------------------------------------------------------------ electrical limits, recorder (G3 additions)
import { impact } from "../js/physics.js";
import { Recording, COLUMNS } from "../js/recorder.js";

function fullThrottle(env, T) {
  const c = buildCourse("hangar", 1);
  const q = new Quad(c, undefined, env);
  q.reset([c.start[0], c.start[1], -1.5]);
  let peak = 0;
  while (q.t < T) { q.step([1, 1, 1, 1], 0.002); if (q.t > 0.2) peak = Math.max(peak, q.bat.current); }
  return { q, peak };
}

test("firmware current limit holds the battery at its setting; without it full throttle draws more", () => {
  // On a freshly charged pack the model draws about 30 A at full throttle (sag lowers the thrust it can make),
  // so a 25 A setting is used to exercise the limiter.
  const lim = fullThrottle({ currentLimit: 25 }, 0.6), free = fullThrottle({ currentLimit: 0 }, 0.6);
  assert.ok(lim.peak <= 25.5, `limited peak ${lim.peak} A`);
  assert.ok(lim.q.limiting && lim.q.limitTime > 0.3, "limit never engaged");
  assert.ok(free.peak > 28, `unlimited peak only ${free.peak} A`);
});

test("hardware cut-off: trips on a flat pack under load, not on a full one", () => {
  const flat = fullThrottle({ batterySoc: 0.02, currentLimit: 0 }, 1.5);
  assert.ok(flat.q.cutoff, `no cut-off, filtered ${flat.q.vFilt} V`);
  assert.ok(flat.q.alerts.some((a) => a.kind === "cutoff"));
  assert.ok(flat.q.cmd.every((c) => c === 0), "motors still commanded after the cut-off");
  const full = fullThrottle({ currentLimit: 0 }, 1.5);
  assert.ok(!full.q.cutoff, "a full pack tripped the cut-off");
  const off = fullThrottle({ batterySoc: 0.02, currentLimit: 0, hwCutoff: false }, 1.5);
  assert.ok(!off.q.cutoff, "cut-off tripped while disabled");
});

test("impact estimate: E = m v^2 / 2 and a = v^2 / (2 d)", () => {
  const r = impact(0.0862, 3, 0.005);
  assert.ok(Math.abs(r.energy_j - 0.3879) < 1e-3, `${r.energy_j} J`);
  assert.ok(Math.abs(r.g - 91.74) < 0.1, `${r.g} g`);
});

test("recorder: 50 Hz rows, CSV columns, interpolated poses", () => {
  const c = buildCourse("hangar", 1);
  const q = new Quad(c);
  q.reset([c.start[0], c.start[1], -1.0]);
  q.thrust = [1, 1, 1, 1].map(() => (q.mass * 9.81) / 4);
  const r = new Recording("test");
  const u = (q.mass * 9.81) / 4 / q.tMax();
  while (q.t < 2) { q.step([u, u, u, u], 0.002); r.sample(q); }
  assert.ok(Math.abs(r.rows.length - 100) <= 1, `${r.rows.length} rows in 2 s`);
  const lines = r.toCSV().trim().split("\n");
  assert.equal(lines[2], COLUMNS.join(","));
  assert.equal(lines[3].split(",").length, COLUMNS.length);
  const p = r.poseAt(1.0);
  assert.ok(p && Math.abs(p.pos[0] - c.start[0]) < 0.05 && Math.abs(Math.hypot(...p.q) - 1) < 1e-9);
  const st = r.stats();
  assert.ok(st.maxCurrent > 2 && st.maxCurrent < 10, `hover current ${st.maxCurrent} A`);
});
