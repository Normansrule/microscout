// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Flight controllers for the Flight Lab. The inner loops (attitude -> body rate -> air-mode mixer)
// port the SDK's reference controller (software/microscout_sdk/src/microscout/sim/fc.py); every
// outer controller below only decides a desired acceleration, so they compare like for like.
//   PID cascade  - the reference controller (position -> velocity -> acceleration)
//   LQR          - optimal gains for a double-integrator model, solved here by Riccati iteration
//   MPC (MPPI)   - sampling model-predictive control that knows the obstacle map
//   Learned      - a neural-network policy trained by reinforcement learning (rl.js); it only
//                  sees its own ToF rays, the target direction and its velocity
//   Pilot        - free flight with beginner / sport / acro modes, flips and the safety rules

import { G, clamp, wrapPi, qmul, qconj, qrot, toEuler, fromEuler, quatFromAxes, cross3, norm3, rng } from "./math.js";
import { clearance, passedGate, DRONE_RADIUS, RAYS, TOF_RANGE } from "./world.js";
import { observe, actionToAccel, actionToVel } from "./policy.js";

export const DEFAULT_GAINS = {
  rate_kp: [40, 40, 25], rate_ki: [60, 60, 30], rate_kd: [0.006, 0.006, 0], rate_i_limit: 8,
  att_kp: [8, 8, 4], vel_kp: [3, 3, 4], vel_ki: [1, 1, 2], pos_kp: [1.2, 1.2, 1.5],
  max_tilt_deg: 35, max_rate_dps: 1000, max_speed_ms: 2.0, max_climb_ms: 1.5,
};

function inv4(m) {   // Gauss-Jordan inverse of a 4x4 (array of rows)
  const a = m.map((r, i) => [...r, ...[0, 1, 2, 3].map((j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < 4; c++) {
    let p = c;
    for (let r = c + 1; r < 4; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
    [a[c], a[p]] = [a[p], a[c]];
    const d = a[c][c];
    for (let k = 0; k < 8; k++) a[c][k] /= d;
    for (let r = 0; r < 4; r++) if (r !== c) { const f = a[r][c]; for (let k = 0; k < 8; k++) a[r][k] -= f * a[c][k]; }
  }
  return a.map((r) => r.slice(4));
}

/** Inner loops shared by every controller. */
export class Core {
  constructor(quad, gains = DEFAULT_GAINS) {
    this.quad = quad;
    this.g = { ...DEFAULT_GAINS, ...gains };
    this.M = inv4([[1, 1, 1, 1], ...quad.Atau]);
    this.reset();
  }
  reset() { this.iRate = [0, 0, 0]; this.iVel = [0, 0, 0]; this.prevW = [...this.quad.w]; }

  mix(F, tau) {
    const tmax = this.quad.tMax();
    const M = this.M;
    const tt = (tq) => [0, 1, 2, 3].map((i) => M[i][1] * tq[0] + M[i][2] * tq[1] + M[i][3] * tq[2]);
    let t = tt(tau), span = Math.max(...t) - Math.min(...t);
    if (span > tmax) {           // keep roll/pitch authority, drop yaw first
      t = tt([tau[0], tau[1], 0]); span = Math.max(...t) - Math.min(...t);
      if (span > tmax) t = t.map((x) => (x * tmax) / span);
    }
    const lo = -Math.min(...t), hi = tmax - Math.max(...t);
    const base = clamp(F / 4, lo, hi);    // air mode
    return t.map((x) => clamp((base + x) / tmax, 0, 1));
  }

  rateLoop(wsp, dt) {
    const w = this.quad.w, g = this.g, I = this.quad.I, out = [0, 0, 0];
    for (let i = 0; i < 3; i++) {
      const e = wsp[i] - w[i];
      this.iRate[i] = clamp(this.iRate[i] + e * dt, -g.rate_i_limit, g.rate_i_limit);
      const dw = (w[i] - this.prevW[i]) / dt;
      out[i] = I[i] * (g.rate_kp[i] * e + g.rate_ki[i] * this.iRate[i] - g.rate_kd[i] * dw);
    }
    this.prevW = [...w];
    return out;
  }

  attToRate(qsp) {
    let qe = qmul(qconj(this.quad.q), qsp);
    if (qe[0] < 0) qe = qe.map((x) => -x);
    const lim = (this.g.max_rate_dps * Math.PI) / 180;
    return [1, 2, 3].map((i) => clamp(2 * this.g.att_kp[i - 1] * qe[i], -lim, lim));
  }

  /** Desired world acceleration (NED) + yaw -> {qsp, F (N)} with the tilt limit. */
  accelToAtt(a, yaw, maxTiltDeg = this.g.max_tilt_deg) {
    const m = this.quad.mass;
    const maxH = G * Math.tan((maxTiltDeg * Math.PI) / 180);
    const h = Math.hypot(a[0], a[1]);
    const ad = h > maxH ? [a[0] * maxH / h, a[1] * maxH / h, a[2]] : [...a];
    ad[2] = clamp(ad[2], -8, 0.8 * G);
    const tw = [m * ad[0], m * ad[1], m * (ad[2] - G)];
    const n = norm3(tw) || 1e-6;
    const zb = [-tw[0] / n, -tw[1] / n, -tw[2] / n];
    const xc = [Math.cos(yaw), Math.sin(yaw), 0];
    let yb = cross3(zb, xc); const ny = norm3(yb) || 1e-6; yb = yb.map((x) => x / ny);
    const xb = cross3(yb, zb);
    const R = qrot(this.quad.q);
    const F = -(tw[0] * R[2] + tw[1] * R[5] + tw[2] * R[8]);
    return { qsp: quatFromAxes(xb, yb, zb), F: Math.max(F, 0) };
  }

  velLoop(vsp, dt) {
    const v = this.quad.vel, g = this.g;
    return [0, 1, 2].map((i) => {
      const e = vsp[i] - v[i];
      this.iVel[i] = clamp(this.iVel[i] + e * dt, -2, 2);
      return g.vel_kp[i] * e + g.vel_ki[i] * this.iVel[i];
    });
  }

  /** Full inner cascade from a desired acceleration. */
  fromAccel(a, yaw, dt) {
    const { qsp, F } = this.accelToAtt(a, yaw);
    return this.mix(F, this.rateLoop(this.attToRate(qsp), dt));
  }
}

/** Waypoints, gates and progress shared by every autonomous controller and the RL reward. */
export class Mission {
  constructor(course) { this.course = course; this.reset(); }
  reset() { this.i = 0; this.done = false; this.gatesPassed = 0; this.events = []; }
  get target() { const w = this.course.waypoints; return w[Math.min(this.i, w.length - 1)]; }
  update(prev, pos) {
    if (this.done || this.course.hold) return 0;
    const wps = this.course.waypoints;
    let bonus = 0;
    const gi = this.course.wpGate ? this.course.wpGate[this.i] : -1;
    if (gi >= 0) {
      const g = this.course.gates[gi];
      if (passedGate(g, prev, pos)) { this.i++; this.gatesPassed++; bonus = 1; this.events.push("gate"); }
      else if (pos[0] > g.c[0] + 0.3) { this.i--; }            // missed the opening: go back and line up again
    } else {
      const t = this.target;
      const r = this.i === wps.length - 1 ? 0.45 : 0.3;
      const passX = this.course.name === "window" && this.i === 1 && pos[0] > t[0];
      if (Math.hypot(pos[0] - t[0], pos[1] - t[1], pos[2] - t[2]) < r || passX) { this.i++; bonus = 1; }
    }
    if (this.i >= wps.length) this.done = true;
    return bonus;
  }
}

function headingTo(quad, t, yawPrev, dt) {
  const dx = t[0] - quad.pos[0], dy = t[1] - quad.pos[1];
  const want = Math.hypot(dx, dy) > 0.4 ? Math.atan2(dy, dx) : yawPrev;
  const max = Math.PI * dt;      // 180 deg/s
  return wrapPi(yawPrev + clamp(wrapPi(want - yawPrev), -max, max));
}

/** Reference cascade (the SDK controller): position -> velocity -> acceleration. */
export class PIDController {
  constructor(quad, mission, opts = {}) {
    this.name = "PID cascade"; this.quad = quad; this.mission = mission; this.core = new Core(quad, opts.gains);
    this.outerDt = 0.02; this.acc = [0, 0, 0]; this.tOuter = 1e9; this.yaw = toEuler(quad.q)[2];
  }
  outer(dt) {
    const g = this.core.g, q = this.quad, t = this.mission.target;
    const v = [0, 1, 2].map((i) => g.pos_kp[i] * (t[i] - q.pos[i]));
    const hs = Math.hypot(v[0], v[1]);
    if (hs > g.max_speed_ms) { v[0] *= g.max_speed_ms / hs; v[1] *= g.max_speed_ms / hs; }
    v[2] = clamp(v[2], -g.max_climb_ms, g.max_climb_ms);
    return this.core.velLoop(v, dt);
  }
  update(dt) {
    this.tOuter += dt;
    this.yaw = headingTo(this.quad, this.mission.target, this.yaw, dt);
    if (this.tOuter >= this.outerDt) { this.acc = this.outer(this.tOuter); this.tOuter = 0; }
    return this.core.fromAccel(this.acc, this.yaw, dt);
  }
}

/** Discrete LQR for a double integrator (per axis): returns [kp, kd]. */
export function lqrGains(qp, qv, r, dt = 0.02) {
  const A = [[1, dt], [0, 1]], B = [dt * dt / 2, dt];
  let P = [[qp, 0], [0, qv]], K = [0, 0];
  for (let it = 0; it < 5000; it++) {
    const PA = [[P[0][0] * A[0][0] + P[0][1] * A[1][0], P[0][0] * A[0][1] + P[0][1] * A[1][1]],
                [P[1][0] * A[0][0] + P[1][1] * A[1][0], P[1][0] * A[0][1] + P[1][1] * A[1][1]]];
    const BtPA = [B[0] * PA[0][0] + B[1] * PA[1][0], B[0] * PA[0][1] + B[1] * PA[1][1]];
    const PB = [P[0][0] * B[0] + P[0][1] * B[1], P[1][0] * B[0] + P[1][1] * B[1]];
    const s = r + B[0] * PB[0] + B[1] * PB[1];
    K = [BtPA[0] / s, BtPA[1] / s];
    const AtPA = [[A[0][0] * PA[0][0] + A[1][0] * PA[1][0], A[0][0] * PA[0][1] + A[1][0] * PA[1][1]],
                  [A[0][1] * PA[0][0] + A[1][1] * PA[1][0], A[0][1] * PA[0][1] + A[1][1] * PA[1][1]]];
    const Pn = [[qp + AtPA[0][0] - BtPA[0] * K[0], AtPA[0][1] - BtPA[0] * K[1]],
                [AtPA[1][0] - BtPA[1] * K[0], qv + AtPA[1][1] - BtPA[1] * K[1]]];
    const diff = Math.abs(Pn[0][0] - P[0][0]) + Math.abs(Pn[0][1] - P[0][1]) + Math.abs(Pn[1][1] - P[1][1]);
    P = Pn;
    if (diff < 1e-12 * (1 + Math.abs(P[0][0]))) break;
  }
  return K;
}

export class LQRController extends PIDController {
  constructor(quad, mission, opts = {}) {
    super(quad, mission, opts);
    this.name = "LQR";
    this.qp = opts.qp ?? 4; this.qv = opts.qv ?? 1; this.r = opts.r ?? 0.3;
    this.K = lqrGains(this.qp, this.qv, this.r, this.outerDt);
    this.Kz = lqrGains(this.qp * 2, this.qv, this.r, this.outerDt);
  }
  outer() {
    const q = this.quad, t = this.mission.target;
    let e = [t[0] - q.pos[0], t[1] - q.pos[1], t[2] - q.pos[2]];
    const h = Math.hypot(e[0], e[1]);
    if (h > 1.2) { e[0] *= 1.2 / h; e[1] *= 1.2 / h; }      // carrot: limit the reference step
    e[2] = clamp(e[2], -1, 1);
    return [0, 1, 2].map((i) => { const K = i === 2 ? this.Kz : this.K; return K[0] * e[i] - K[1] * q.vel[i]; });
  }
}

/** Model-predictive path integral control over a point-mass model with the obstacle map. */
export class MPCController extends PIDController {
  constructor(quad, mission, opts = {}) {
    super(quad, mission, opts);
    this.name = "MPC (MPPI)";
    this.N = opts.horizon ?? 16; this.K = opts.samples ?? 64; this.h = 0.05; this.sigma = opts.sigma ?? 5; this.lambda = 1.0;
    this.outerDt = opts.period ?? 0.04;
    this.U = Array.from({ length: this.N }, () => [0, 0, 0]);
    this.rand = rng(opts.seed ?? 3);
    this.vmax = opts.vmax ?? 2.5;
    this.lastSamples = [];
  }
  cost(p, v, u, t) {
    const d = Math.hypot(p[0] - t[0], p[1] - t[1], p[2] - t[2]);
    let c = d < 2 ? d * d : 4 * d - 4;
    const sp = Math.hypot(v[0], v[1], v[2]);
    if (sp > this.vmax) c += 4 * (sp - this.vmax) ** 2;
    c += 0.01 * (u[0] * u[0] + u[1] * u[1] + u[2] * u[2]);
    const cl = clearance(this.mission.course, p) - DRONE_RADIUS;
    if (cl < 0.35) c += 120 * (0.35 - cl) ** 2;
    if (cl < 0) c += 400;
    return c;
  }
  outer() {
    const q = this.quad, t = this.mission.target, N = this.N, K = this.K, h = this.h;
    const amax = 7;
    const costs = new Float64Array(K), noise = [];
    const keep = [];
    for (let k = 0; k < K; k++) {
      const p = [...q.pos], v = [...q.vel], eps = [];
      let c = 0;
      const traj = k < 12 ? [] : null;
      for (let n = 0; n < N; n++) {
        const e = k === 0 ? [0, 0, 0] : [this.rand.normal() * this.sigma, this.rand.normal() * this.sigma, this.rand.normal() * this.sigma * 0.5];
        eps.push(e);
        const u = [0, 1, 2].map((i) => clamp(this.U[n][i] + e[i], -amax, amax));
        for (let i = 0; i < 3; i++) { v[i] += u[i] * h; p[i] += v[i] * h; }
        c += this.cost(p, v, u, t);
        if (traj) traj.push([...p]);
      }
      costs[k] = c; noise.push(eps);
      if (traj) keep.push(traj);
    }
    let min = Infinity; for (const c of costs) min = Math.min(min, c);
    let wsum = 0; const w = new Float64Array(K);
    for (let k = 0; k < K; k++) { w[k] = Math.exp(-(costs[k] - min) / this.lambda / Math.max(1, min * 0.05)); wsum += w[k]; }
    for (let n = 0; n < N; n++) for (let i = 0; i < 3; i++) {
      let s = 0; for (let k = 0; k < K; k++) s += w[k] * noise[k][n][i];
      this.U[n][i] = clamp(this.U[n][i] + s / wsum, -amax, amax);
    }
    const u0 = [...this.U[0]];
    this.U.push(this.U.shift().map(() => 0));          // warm start: shift the plan
    this.U[N - 1] = [...this.U[N - 2]];
    this.lastSamples = keep;
    return u0;
  }
}

/** A trained neural-network (or linear) policy from rl.js; optionally residual on top of PID. */
export class LearnedController extends PIDController {
  constructor(quad, mission, opts = {}) {
    super(quad, mission, opts);
    this.name = opts.residual ? "PID + learned residual" : "Learned policy";
    this.policy = opts.policy; this.residual = !!opts.residual; this.outerDt = 0.04;
    this.actionMode = opts.actionMode || "velocity";
  }
  /** Turn a policy action into a desired acceleration (velocity mode runs it through the velocity loop). */
  actionAccel(act, dt) {
    if (this.residual) {
      const a = actionToAccel(act, this.yaw, 3), base = super.outer(dt);
      return [base[0] + a[0], base[1] + a[1], base[2] + a[2]];
    }
    if (this.actionMode === "accel") return actionToAccel(act, this.yaw, 7);
    return this.core.velLoop(actionToVel(act, this.yaw), dt);
  }
  outer(dt) {
    const act = this.policy.act(observe(this.quad, this.mission, this.yaw));
    this.lastAction = act;
    return this.actionAccel(act, dt);
  }
}

/**
 * Free-pilot flight controller: the SDK's beginner / sport / acro modes, one-button flips and the
 * safety rules (low-battery landing, radio-loss hover then land, altitude ceiling, obstacle stop).
 */
export class PilotController {
  constructor(quad, opts = {}) {
    this.name = "Pilot"; this.quad = quad; this.core = new Core(quad, opts.gains); this.g = this.core.g;
    this.mode = "beginner"; this.armed = false; this.sticks = { roll: 0, pitch: 0, yaw: 0, throttle: 0.5 };
    this.stickT = 0; this.yawSp = toEuler(quad.q)[2]; this.posSp = [...quad.pos]; this.task = null; this.ts = {};
    this.msgs = []; this.ceiling = opts.ceiling ?? 3.0; this.lowBatT = 0; this.linkLost = false; this.holdT = null;
  }
  say(m) { if (this.msgs[this.msgs.length - 1] !== m) this.msgs.push(m); if (this.msgs.length > 30) this.msgs.shift(); }
  arm() {
    const [r, p] = toEuler(this.quad.q);
    if (Math.max(Math.abs(r), Math.abs(p)) > 0.44) return this.say("arming refused: not level");
    if (this.quad.bat.voltage / 2 < 3.5) return this.say("arming refused: battery low");
    this.armed = true; this.posSp = [...this.quad.pos]; this.yawSp = toEuler(this.quad.q)[2]; this.core.reset();
    this.task = "takeoff"; this.posSp[2] = -1.2; this.say("armed - taking off to 1.2 m");
  }
  disarm(msg = "disarmed") { this.armed = false; this.task = null; this.say(msg); }
  setSticks(s, t) { this.sticks = s; this.stickT = t; if (this.linkLost) { this.linkLost = false; this.holdT = null; this.say("link restored"); } }
  flip(dir = "back") {
    if (!this.armed) return this.say("flip refused: not armed");
    if (this.quad.height < 1.0) return this.say("flip refused: climb above 1 m first");
    const F = { back: [1, 1], front: [1, -1], right: [0, 1], left: [0, -1] }[dir];
    this.task = "flip"; this.ts = { axis: F[0], sign: F[1], phase: "climb", t0: this.quad.t, angle: 0, h0: this.quad.height };
    this.say(`${dir} flip`);
  }
  land() { if (this.armed) { this.task = "land"; this.ts = { t0: this.quad.t }; this.say("landing"); } }

  obstacleFilter(v) {
    if (this.mode !== "beginner") return v;
    const tof = this.quad.tof(), R = qrot(this.quad.q);
    const dirs = [];
    RAYS.forEach((r, i) => { if (r.name !== "down" && tof[i] < 0.4 + DRONE_RADIUS) dirs.push(r.d); });
    for (const d of dirs) {
      const dw = [R[0] * d[0] + R[1] * d[1] + R[2] * d[2], R[3] * d[0] + R[4] * d[1] + R[5] * d[2], 0];
      const n = Math.hypot(dw[0], dw[1]); if (n < 1e-6) continue;
      dw[0] /= n; dw[1] /= n;
      const toward = v[0] * dw[0] + v[1] * dw[1];
      if (toward > 0) { v[0] -= toward * dw[0]; v[1] -= toward * dw[1]; this.say("obstacle stop"); }
    }
    return v;
  }

  safety(dt) {
    const q = this.quad;
    if (q.height > this.ceiling + 0.3 && this.mode !== "acro" && this.task !== "flip") { this.posSp[2] = -this.ceiling; this.say("altitude ceiling"); }
    this.lowBatT = q.bat.voltage / 2 < 3.4 ? this.lowBatT + dt : 0;
    if (this.lowBatT > 2 && this.task !== "land") { this.say("low battery: auto-land"); this.land(); }
    if (!this.linkLost && q.t - this.stickT > 0.5 && this.task == null) {
      this.linkLost = true; this.holdT = q.t; this.posSp = [...q.pos]; this.say("radio link lost: hover");
    }
    if (this.linkLost && this.holdT != null && q.t - this.holdT > 3 && this.task !== "land") { this.say("link lost: landing"); this.land(); }
  }

  update(dt) {
    const q = this.quad, c = this.core, g = this.g;
    if (!this.armed) return [0, 0, 0, 0];
    this.safety(dt);
    const yaw = toEuler(q.q)[2];
    let rate = null, F = null;
    const s = this.sticks, ts = this.ts;
    const R = qrot(q.q);
    if (this.task === "flip") {
      if (ts.phase === "climb") {
        const a = c.velLoop([0, 0, -2.5], dt); ({ qsp: this._q, F } = c.accelToAtt(a, this.yawSp)); rate = c.attToRate(this._q);
        if (q.t - ts.t0 > 0.22) ts.phase = "rotate";
      } else if (ts.phase === "rotate") {
        rate = [0, 0, 0]; rate[ts.axis] = (ts.sign * g.max_rate_dps * Math.PI) / 180; F = 0.45 * q.mass * G;
        ts.angle += Math.abs(q.w[ts.axis]) * dt;
        if (ts.angle > (320 * Math.PI) / 180) { ts.phase = "recover"; this.posSp = [q.pos[0], q.pos[1], -Math.max(ts.h0, q.height)]; c.iVel = [0, 0, 0]; }
      } else {
        const v = [0, 0, clamp(g.pos_kp[2] * (this.posSp[2] - q.pos[2]), -1.5, 1.5)];
        const a = c.velLoop(v, dt); ({ qsp: this._q, F } = c.accelToAtt(a, this.yawSp)); rate = c.attToRate(this._q);
        const tilt = Math.acos(clamp(R[8], -1, 1)) * 180 / Math.PI;
        if (tilt < 8 && Math.abs(q.vel[2]) < 0.6) { this.task = null; this.posSp = [...q.pos]; this.say("flip complete"); }
      }
    } else if (this.task === "land") {
      const v = [this.posSp[0] - q.pos[0], this.posSp[1] - q.pos[1], q.height > 0.3 ? 0.5 : 0.25];
      const a = c.velLoop(v, dt); ({ qsp: this._q, F } = c.accelToAtt(a, this.yawSp)); rate = c.attToRate(this._q);
      if (q.onGround && q.t - (this.ts.t0 || 0) > 0.3) { this.disarm("landed"); return [0, 0, 0, 0]; }
    } else if (this.task === "takeoff" || this.linkLost) {
      const v = [0, 1, 2].map((i) => g.pos_kp[i] * (this.posSp[i] - q.pos[i]));
      const a = c.velLoop(v, dt); ({ qsp: this._q, F } = c.accelToAtt(a, this.yawSp)); rate = c.attToRate(this._q);
      if (this.task === "takeoff" && Math.abs(this.posSp[2] - q.pos[2]) < 0.08) { this.task = null; this.say("hovering - fly with the sticks"); }
    } else if (this.mode === "acro") {
      rate = [s.roll, -s.pitch, s.yaw].map((x) => (x * g.max_rate_dps * Math.PI) / 180);
      F = s.throttle * 4 * q.tMax();
    } else if (this.mode === "sport") {
      const tilt = (g.max_tilt_deg * Math.PI) / 180;
      this.yawSp = wrapPi(this.yawSp + s.yaw * Math.PI * dt);
      const qsp = fromEuler(s.roll * tilt, -s.pitch * tilt, this.yawSp);
      const vz = -(s.throttle - 0.5) * 2 * g.max_climb_ms;
      const az = c.velLoop([q.vel[0], q.vel[1], vz], dt)[2];
      F = (q.mass * (G - az)) / Math.max(R[8], 0.3);
      rate = c.attToRate(qsp);
      this.posSp = [...q.pos];
    } else {          // beginner: sticks are velocities in the heading frame
      const cy = Math.cos(yaw), sy = Math.sin(yaw);
      const fwd = s.pitch * g.max_speed_ms, rgt = s.roll * g.max_speed_ms;
      let v = [cy * fwd - sy * rgt, sy * fwd + cy * rgt, -(s.throttle - 0.5) * 2 * g.max_climb_ms];
      v = this.obstacleFilter(v);
      this.yawSp = wrapPi(this.yawSp + s.yaw * (Math.PI / 2) * dt);
      const a = c.velLoop(v, dt); ({ qsp: this._q, F } = c.accelToAtt(a, this.yawSp)); rate = c.attToRate(this._q);
      this.posSp = [...q.pos];
    }
    return c.mix(F, c.rateLoop(rate, dt));
  }
}

export const CONTROLLERS = {
  pid: { label: "PID cascade", make: (q, m, o) => new PIDController(q, m, o), about: "The reference controller from the SDK: position error sets a velocity, velocity error sets an acceleration. Simple and robust, but it flies straight at the target - it has no idea obstacles exist." },
  lqr: { label: "LQR", make: (q, m, o) => new LQRController(q, m, o), about: "Linear-quadratic regulator: gains come from solving a Riccati equation for a double-integrator model, trading position error (Q) against effort (R). Smooth and optimal for that model, still blind to obstacles." },
  mpc: { label: "MPC (MPPI)", make: (q, m, o) => new MPCController(q, m, o), about: "Model-predictive control: every 40 ms it simulates 64 random futures 0.8 s ahead, scores them against the target and the obstacle map, and blends the best. Plans around obstacles - but it is given the map." },
  learned: { label: "Learned policy (RL)", make: (q, m, o) => new LearnedController(q, m, o), about: "A small neural network trained by reinforcement learning on the Train tab. It sees only what the drone's sensors see: 12 ToF rays, its velocity and the direction to the next target." },
};
