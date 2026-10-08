// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Observation, action mapping and the small neural networks used by the RL trainers.

import { toEuler, clamp, rng } from "./math.js";
import { RAYS, TOF_RANGE } from "./world.js";

export const OBS_NAMES = ["target fwd", "target right", "target down", "vel fwd", "vel right", "vel down", ...RAYS.map((r) => `ToF ${r.name}`)];
export const OBS_DIM = OBS_NAMES.length;     // 18
export const ACT_DIM = 3;

/** What the policy sees, in the drone's heading frame: target direction, velocity, ToF rays. */
export function observe(quad, mission, yaw = null) {
  const y = yaw ?? toEuler(quad.q)[2];
  const c = Math.cos(y), s = Math.sin(y);
  const t = mission.target;
  let dx = t[0] - quad.pos[0], dy = t[1] - quad.pos[1], dz = t[2] - quad.pos[2];
  const n = Math.hypot(dx, dy, dz);
  if (n > 3) { dx *= 3 / n; dy *= 3 / n; dz *= 3 / n; }
  const v = quad.vel;
  const tof = quad.tof();
  return [
    (c * dx + s * dy) / 3, (-s * dx + c * dy) / 3, dz / 3,
    (c * v[0] + s * v[1]) / 3, (-s * v[0] + c * v[1]) / 3, v[2] / 3,
    ...tof.map((d) => 1 - Math.min(d, TOF_RANGE) / TOF_RANGE),
  ];
}

/** Action in [-1, 1]^3 (heading frame) -> world acceleration (m/s^2). */
export function actionToAccel(a, yaw, scale = 7) {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  const f = clamp(a[0], -1, 1) * scale, r = clamp(a[1], -1, 1) * scale, d = clamp(a[2], -1, 1) * scale * 0.6;
  return [c * f - s * r, s * f + c * r, d];
}

/** Action in [-1, 1]^3 (heading frame) -> world velocity setpoint (m/s) for the drone's velocity loop. */
export function actionToVel(a, yaw, vmax = 2.5) {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  const f = clamp(a[0], -1, 1) * vmax, r = clamp(a[1], -1, 1) * vmax, d = clamp(a[2], -1, 1) * 1.5;
  return [c * f - s * r, s * f + c * r, d];
}

/** Fully connected network with tanh hidden layers and a tanh output (actions in [-1, 1]). */
export class MLP {
  constructor(sizes, params = null, seed = 1) {
    this.sizes = sizes;
    this.n = 0;
    for (let i = 0; i < sizes.length - 1; i++) this.n += sizes[i] * sizes[i + 1] + sizes[i + 1];
    this.params = params ? Float64Array.from(params) : this.init(seed);
  }
  init(seed) {
    const R = rng(seed), p = new Float64Array(this.n);
    let o = 0;
    for (let l = 0; l < this.sizes.length - 1; l++) {
      const a = this.sizes[l], b = this.sizes[l + 1];
      const last = l === this.sizes.length - 2;
      const sc = last ? 0.05 / Math.sqrt(a) : 1 / Math.sqrt(a);     // near-zero output: start by hovering
      for (let i = 0; i < a * b; i++) p[o++] = R.normal() * sc;
      o += b;
    }
    return p;
  }
  /** Returns the output; if cache is given, stores activations for backward(). */
  forward(x, cache = null, params = this.params) {
    let h = x, o = 0;
    if (cache) cache.acts = [x];
    for (let l = 0; l < this.sizes.length - 1; l++) {
      const a = this.sizes[l], b = this.sizes[l + 1], out = new Array(b);
      for (let j = 0; j < b; j++) {
        let z = params[o + a * b + j];
        for (let i = 0; i < a; i++) z += params[o + j * a + i] * h[i];
        out[j] = Math.tanh(z);
      }
      o += a * b + b;
      h = out;
      if (cache) cache.acts.push(out);
    }
    return h;
  }
  /** Gradient of sum(gOut * output) w.r.t. params, given a forward() cache. */
  backward(cache, gOut, grad) {
    const acts = cache.acts;
    let g = gOut.map((v, j) => v * (1 - acts[acts.length - 1][j] ** 2));
    let o = this.n;
    for (let l = this.sizes.length - 2; l >= 0; l--) {
      const a = this.sizes[l], b = this.sizes[l + 1];
      o -= a * b + b;
      const hin = acts[l];
      const gin = new Array(a).fill(0);
      for (let j = 0; j < b; j++) {
        grad[o + a * b + j] += g[j];
        for (let i = 0; i < a; i++) { grad[o + j * a + i] += g[j] * hin[i]; gin[i] += g[j] * this.params[o + j * a + i]; }
      }
      if (l > 0) g = gin.map((v, i) => v * (1 - hin[i] ** 2));
    }
  }
}

/** A deterministic policy wrapper used by the controllers and for evaluation. */
export class Policy {
  constructor(arch = "mlp", params = null, seed = 1) {
    this.arch = arch;
    this.net = new MLP(arch === "linear" ? [OBS_DIM, ACT_DIM] : [OBS_DIM, 24, ACT_DIM], params, seed);
    this.logStd = [-0.7, -0.7, -0.7];     // used by REINFORCE only
  }
  get size() { return this.net.n; }
  act(obs, params = undefined) { return this.net.forward(obs, null, params ?? this.net.params); }
  toJSON() { return { arch: this.arch, params: Array.from(this.net.params), logStd: this.logStd }; }
  static fromJSON(j) { const p = new Policy(j.arch, j.params); if (j.logStd) p.logStd = j.logStd; return p; }
}
