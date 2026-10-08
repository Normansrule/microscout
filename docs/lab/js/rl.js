// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Reinforcement learning for the Flight Lab: an episode runner with a shaped reward and four
// trainers you can compare - Cross-Entropy Method, Evolution Strategies (OpenAI-ES), Augmented
// Random Search and REINFORCE (policy gradient). Everything runs in the browser (in a worker).

import { rng, toEuler } from "./math.js";
import { buildCourse } from "./world.js";
import { Quad } from "./physics.js";
import { LearnedController, Mission } from "./control.js";
import { Policy, observe, ACT_DIM } from "./policy.js";

export const TRAINERS = {
  cem: { label: "Cross-entropy method (CEM)", about: "Samples a population of policies around a mean, keeps the best 20 % and refits the mean and spread to them. Simple, robust, no gradients." },
  es: { label: "Evolution strategies (OpenAI-ES)", about: "Estimates a gradient from mirrored random perturbations of the policy, ranks their returns and takes an Adam step. Scales to many parameters." },
  ars: { label: "Augmented random search (ARS)", about: "Like ES but only uses the best few perturbation directions and normalises by the spread of their returns. Very strong on linear policies." },
  reinforce: { label: "REINFORCE (policy gradient)", about: "Adds Gaussian noise to the actions, then pushes up the log-probability of actions that led to above-average returns. Learns per step instead of per episode - noisier." },
};

export const DEFAULT_TRAIN = {
  trainer: "cem", course: "gates", arch: "linear", residual: false, population: 24, episodes: 1,
  actionMode: "velocity", sigma: 0.1, lr: 0.05, elite: 0.2, randomize: true, wind: 0, gust: 0, crashEnds: true, maxTime: 20, seed: 7, init: "random",
};

/**
 * One episode with a given parameter vector. Returns the shaped return and diagnostics.
 * Reward per 40 ms step: 5 x progress toward the current target (m) + 10 per gate/waypoint
 * + 20 on finishing - 0.02 per step - 20 for a crash (impact > 0.6 m/s or > 70 deg tilt).
 */
export function runEpisode(policy, params, opt, seed, record = false, noise = null) {
  const course = buildCourse(opt.course, seed, opt.randomize);
  const R = rng(seed * 7919 + 13);
  const env = {
    wind: [opt.wind * (opt.randomize ? R() * 2 - 1 : 1), opt.wind * (opt.randomize ? R() * 2 - 1 : 0), 0],
    gust: opt.gust, seed, payload_g: opt.randomize ? R() * 8 : 0,
    motorHealth: opt.randomize ? [1, 1, 1, 1].map(() => 0.92 + 0.08 * R()) : [1, 1, 1, 1],
  };
  const quad = new Quad(course, undefined, env);
  quad.reset(course.start[2] >= 0 ? [course.start[0], course.start[1], -1.0] : course.start, 0);
  quad.thrust = [0, 1, 2, 3].map(() => (quad.mass * 9.81) / 4 * quad.env.motorHealth[0]);   // start in a hover
  const mission = new Mission(course);
  const pol = { act: (o) => policy.act(o, params) };
  const ctrl = new LearnedController(quad, mission, { policy: pol, residual: opt.residual, actionMode: opt.actionMode });
  const stochastic = noise != null;
  const steps = [];
  if (stochastic) {
    ctrl.outer = function () {            // Gaussian exploration around the policy's mean action
      const obs = observe(quad, mission, this.yaw);
      const cache = {};
      const mu = policy.net.forward(obs, cache, params);
      const std = policy.logStd.map(Math.exp);
      const a = mu.map((m, i) => m + std[i] * noise.normal());
      steps.push({ obs, cache, mu, a, r: 0 });
      return this.actionAccel(a, 0.04);
    };
  }
  const dt = 0.004, tmax = Math.min(opt.maxTime, course.timeLimit);
  let ret = 0, crashed = false, tick = 0, impact0 = 0;
  let prevDist = dist(quad.pos, mission.target);
  const traj = [];
  while (quad.t < tmax) {
    const prev = [...quad.pos];
    const u = ctrl.update(dt);
    quad.step(u, dt);
    const bonus = mission.update(prev, quad.pos);
    if (++tick % 10 !== 0 && !bonus) continue;
    let r = -0.02;
    if (course.hold) {
      const d = dist(quad.pos, mission.target);
      r = 0.1 - 0.25 * d - 0.03 * Math.hypot(...quad.vel);
    } else {
      const d = dist(quad.pos, mission.target);
      r += bonus ? 10 : 5 * (prevDist - d);
      prevDist = dist(quad.pos, mission.target);
    }
    const [roll, pitch] = toEuler(quad.q);
    const hard = quad.maxImpact > 0.6 && quad.maxImpact > impact0;
    if (quad.maxImpact > impact0) { r -= 2 * (quad.maxImpact - impact0); impact0 = quad.maxImpact; }
    if ((hard && opt.crashEnds) || Math.max(Math.abs(roll), Math.abs(pitch)) > 1.22 || (quad.onGround && quad.t > 1)) {
      r -= 20; crashed = true;
    }
    if (mission.done) r += 20 + 2 * (tmax - quad.t);
    ret += r;
    if (stochastic && steps.length) steps[steps.length - 1].r += r;
    if (record && tick % 25 === 0) traj.push([...quad.pos]);
    if (crashed || mission.done) break;
  }
  if (record) traj.push([...quad.pos]);
  return { ret, success: mission.done, crashed, gates: mission.i, time: quad.t, traj, steps };
}

/** Linear weights that make the policy a plain PD controller towards the target (a warm start). */
export function pdPrior(net, actionMode = "velocity") {
  const p = new Float64Array(net.n), D = net.sizes[0];
  const set = (out, inp, w) => { p[out * D + inp] = w; };
  if (actionMode === "velocity") {          // v = 1.5 x error (m/s), through tanh x 2.5 (horizontal) / x 1.5 (vertical)
    set(0, 0, 1.8); set(1, 1, 1.8); set(2, 2, 3.0);
  } else {                                  // a = 2 x err - 2.5 x vel (m/s^2), through tanh x 7 / x 4.2
    set(0, 0, 0.86); set(0, 3, -1.07); set(1, 1, 0.86); set(1, 4, -1.07); set(2, 2, 2.1); set(2, 5, -2.1);
  }
  return p;
}

function dist(a, b) { return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); }

class Adam {
  constructor(n, lr) { this.m = new Float64Array(n); this.v = new Float64Array(n); this.t = 0; this.lr = lr; }
  step(theta, g) {     // gradient ASCENT
    this.t++;
    const b1 = 0.9, b2 = 0.999;
    for (let i = 0; i < theta.length; i++) {
      this.m[i] = b1 * this.m[i] + (1 - b1) * g[i];
      this.v[i] = b2 * this.v[i] + (1 - b2) * g[i] * g[i];
      const mh = this.m[i] / (1 - b1 ** this.t), vh = this.v[i] / (1 - b2 ** this.t);
      theta[i] += (this.lr * mh) / (Math.sqrt(vh) + 1e-8);
    }
  }
}

function ranks(x) {   // centred ranks in [-0.5, 0.5]
  const idx = x.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
  const r = new Float64Array(x.length);
  idx.forEach(([, i], k) => { r[i] = k / (x.length - 1) - 0.5; });
  return r;
}

export class Trainer {
  constructor(opt = {}) {
    this.opt = { ...DEFAULT_TRAIN, ...opt };
    this.policy = new Policy(this.opt.arch, null, this.opt.seed);
    this.n = this.policy.size;
    if (this.opt.init === "pd" && this.opt.arch === "linear") this.policy.net.params = pdPrior(this.policy.net, this.opt.actionMode);
    this.theta = Float64Array.from(this.policy.net.params);
    this.sig = new Float64Array(this.n).fill(this.opt.sigma);
    this.rand = rng(this.opt.seed);
    this.adam = new Adam(this.n, this.opt.lr);
    this.iter = 0;
    this.history = [];
    this.best = { ret: -Infinity, params: Float64Array.from(this.theta) };
  }

  evaluate(params, seeds, record = false) {
    let ret = 0, succ = 0, gates = 0, crash = 0;
    const trajs = [];
    for (const s of seeds) {
      const r = runEpisode(this.policy, params, this.opt, s, record);
      ret += r.ret; succ += r.success ? 1 : 0; gates += r.gates; crash += r.crashed ? 1 : 0;
      if (record) trajs.push(r.traj);
    }
    const k = seeds.length;
    return { ret: ret / k, success: succ / k, gates: gates / k, crash: crash / k, trajs };
  }

  seeds() {
    const base = this.opt.randomize ? 1000 + this.iter * 31 : this.opt.seed;
    return Array.from({ length: this.opt.episodes }, (_, i) => base + i);
  }

  /** One training iteration. Returns stats and a few sample trajectories to draw as ghosts. */
  iterate() {
    const t0 = performance.now();
    const o = this.opt, seeds = this.seeds();
    let rets = [], ghosts = [];
    if (o.trainer === "reinforce") ({ rets, ghosts } = this.reinforce(seeds));
    else {
      const pop = [];
      const P = o.trainer === "cem" ? o.population : Math.max(2, Math.floor(o.population / 2));
      for (let k = 0; k < P; k++) {
        const eps = new Float64Array(this.n);
        for (let i = 0; i < this.n; i++) eps[i] = this.rand.normal();
        pop.push(eps);
      }
      const evalAt = (eps, sgn) => {
        const p = new Float64Array(this.n);
        for (let i = 0; i < this.n; i++) p[i] = this.theta[i] + sgn * this.sig[i] * eps[i];
        const rec = ghosts.length < 6;
        const r = this.evaluate(p, seeds, rec);
        if (rec) ghosts.push(r.trajs[0]);
        return r.ret;
      };
      if (o.trainer === "cem") {
        const scored = pop.map((eps) => ({ eps, ret: evalAt(eps, 1) }));
        rets = scored.map((s) => s.ret);
        scored.sort((a, b) => b.ret - a.ret);
        const ne = Math.max(2, Math.round(P * o.elite));
        const el = scored.slice(0, ne).map((s) => Float64Array.from(s.eps, (e, i) => this.theta[i] + this.sig[i] * e));
        const floor = 0.02 + 0.2 * o.sigma * Math.exp(-this.iter / 25);
        for (let i = 0; i < this.n; i++) {
          let m = 0; for (const e of el) m += e[i]; m /= ne;
          let v = 0; for (const e of el) v += (e[i] - m) ** 2; v /= ne;
          this.theta[i] = m; this.sig[i] = Math.sqrt(v) + floor;
        }
      } else {
        const rp = [], rm = [];
        for (const eps of pop) { rp.push(evalAt(eps, 1)); rm.push(evalAt(eps, -1)); }
        rets = [...rp, ...rm];
        const g = new Float64Array(this.n);
        if (o.trainer === "es") {
          const rk = ranks(rets);
          pop.forEach((eps, k) => { const w = rk[k] - rk[k + pop.length]; for (let i = 0; i < this.n; i++) g[i] += w * eps[i]; });
          for (let i = 0; i < this.n; i++) g[i] /= pop.length * o.sigma;
          this.adam.step(this.theta, g);
        } else {      // ARS: top-b directions, step normalised by the std of their returns
          const b = Math.max(1, Math.round(pop.length / 2));
          const order = pop.map((_, k) => k).sort((x, y) => Math.max(rp[y], rm[y]) - Math.max(rp[x], rm[x])).slice(0, b);
          const used = order.flatMap((k) => [rp[k], rm[k]]);
          const mu = used.reduce((a, c) => a + c, 0) / used.length;
          const sd = Math.sqrt(used.reduce((a, c) => a + (c - mu) ** 2, 0) / used.length) || 1;
          for (const k of order) for (let i = 0; i < this.n; i++) g[i] += (rp[k] - rm[k]) * pop[k][i];
          for (let i = 0; i < this.n; i++) this.theta[i] += (o.lr / (b * sd)) * g[i] * o.sigma;
        }
      }
    }
    // evaluate the current (mean) policy on fixed validation courses
    const val = this.evaluate(this.theta, [101, 202], true);
    if (val.ret > this.best.ret) this.best = { ret: val.ret, params: Float64Array.from(this.theta) };
    this.iter++;
    const s = rets.slice().sort((a, b) => a - b);
    const st = {
      iter: this.iter, mean: rets.reduce((a, c) => a + c, 0) / rets.length, max: s[s.length - 1], min: s[0],
      val: val.ret, success: val.success, gates: val.gates, crash: val.crash, ms: performance.now() - t0,
    };
    this.history.push(st);
    return { stats: st, ghosts, valTraj: val.trajs, params: Array.from(this.theta), best: Array.from(this.best.params) };
  }

  reinforce(seeds) {
    const o = this.opt, M = Math.max(4, Math.round(o.population / 3));
    const all = [], rets = [], ghosts = [];
    for (let m = 0; m < M; m++) {
      const r = runEpisode(this.policy, this.theta, o, seeds[m % seeds.length] + m * 97, m < 6, this.rand);
      rets.push(r.ret); all.push(r.steps);
      if (m < 6) ghosts.push(r.traj);
    }
    // discounted returns-to-go, normalised across the batch
    const gam = 0.98, adv = [];
    for (const ep of all) { let G = 0; const a = new Array(ep.length); for (let t = ep.length - 1; t >= 0; t--) { G = ep[t].r + gam * G; a[t] = G; } adv.push(a); }
    const flat = adv.flat(), mu = flat.reduce((a, c) => a + c, 0) / Math.max(1, flat.length);
    const sd = Math.sqrt(flat.reduce((a, c) => a + (c - mu) ** 2, 0) / Math.max(1, flat.length)) || 1;
    const g = new Float64Array(this.n), gls = [0, 0, 0];
    const net = this.policy.net, saved = net.params;
    net.params = this.theta;
    all.forEach((ep, e) => ep.forEach((st, t) => {
      const A = (adv[e][t] - mu) / sd;
      const std = this.policy.logStd.map(Math.exp);
      const gOut = st.mu.map((m, i) => (A * (st.a[i] - m)) / (std[i] * std[i]));
      net.backward(st.cache, gOut, g);
      for (let i = 0; i < ACT_DIM; i++) gls[i] += A * (((st.a[i] - st.mu[i]) ** 2) / (std[i] * std[i]) - 1);
    }));
    net.params = saved;
    const N = Math.max(1, flat.length);
    for (let i = 0; i < this.n; i++) g[i] /= N;
    this.adam.step(this.theta, g);
    for (let i = 0; i < ACT_DIM; i++) this.policy.logStd[i] = Math.max(-2.5, Math.min(0, this.policy.logStd[i] + 0.01 * gls[i] / N));
    return { rets, ghosts };
  }

  exportPolicy(which = "best") {
    const p = new Policy(this.opt.arch, which === "best" ? this.best.params : this.theta);
    p.logStd = [...this.policy.logStd];
    return p.toJSON();
  }
}
