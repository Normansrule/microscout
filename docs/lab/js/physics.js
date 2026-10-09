// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// JavaScript port of software/microscout_sdk/src/microscout/sim/physics.py: rigid-body quadrotor,
// first-order motors, inflow thrust loss, drag (with wind), a simple 2S battery, plus the Flight
// Lab extras: obstacles, gusts, motor damage, payload and ToF sensor noise. All parameters are
// ESTIMATES from review/G1/calc/budgets.py - this is not the real drone.

import { G, RHO, qmul, qnormalize, qrot, mulRv, mulRTv, rng } from "./math.js";
import { RAYS, TOF_RANGE, castRay, resolveCollisions, DRONE_RADIUS } from "./world.js";

export const DEFAULT_PARAMS = {
  mass_kg: 0.0862, motor_to_motor_m: 0.095, ixx: 4.69e-5, iyy: 5.76e-5, izz: 8.56e-5,
  t_max_per_motor_n: 0.085 * 9.81, motor_tau_s: 0.03, yaw_torque_per_thrust_m: 0.012,
  prop_pitch_speed_ms: 59.0, drag_cda_m2: 0.010, angular_drag: 2.0e-6, battery_mah: 550, battery_cells: 2,
  battery_r_int_ohm: 0.045, hover_eff_g_per_w: 3.0, electronics_w: 2.98, motor_spin: [1, -1, -1, 1],
};

export class Battery {
  constructor(mah, cells, rInt, soc = 1) {
    this.cap = mah * 3.6; this.used = this.cap * (1 - soc); this.cells = cells; this.r = rInt;
    this.current = 0; this.voltage = this.ocv();
  }
  get soc() { return Math.max(0, 1 - this.used / this.cap); }
  ocv() { return this.cells * (3.5 + 0.7 * this.soc); }
  step(power, dt) {
    const v = this.ocv();
    let i = power / Math.max(v, 1e-3);
    for (let k = 0; k < 3; k++) { const vt = Math.max(v - i * this.r, 0.5 * v); i = power / vt; }
    this.current = i; this.voltage = v - i * this.r; this.used += i * dt;
  }
}

export class Quad {
  /**
   * @param {object} course from world.buildCourse
   * @param {object} env {wind:[x,y,z] m/s, gust: m/s, motorHealth:[4], payload_g, tofNoise: m, batterySoc, seed}
   */
  constructor(course, params = DEFAULT_PARAMS, env = {}) {
    this.p = { ...DEFAULT_PARAMS, ...params };
    this.course = course;
    this.env = { wind: [0, 0, 0], gust: 0, motorHealth: [1, 1, 1, 1], payload_g: 0, tofNoise: 0, batterySoc: 1, seed: 1, ...env };
    this.rand = rng(this.env.seed);
    this.mass = this.p.mass_kg + this.env.payload_g / 1000;
    this.I = [this.p.ixx, this.p.iyy, this.p.izz];
    const a = this.p.motor_to_motor_m / Math.SQRT2 / 2;
    this.xy = [[-a, a], [a, a], [-a, -a], [a, -a]];             // motors 1..4: RR, FR, RL, FL (x fwd, y right)
    const k = this.p.yaw_torque_per_thrust_m, s = this.p.motor_spin;
    this.Atau = [this.xy.map((m) => -m[1]), this.xy.map((m) => m[0]), s.map((sp) => -sp * k)];
    this.reset();
  }

  reset(pos = null, yaw = 0) {
    const st = pos || this.course.start;
    this.pos = [st[0], st[1], st[2]];
    this.vel = [0, 0, 0];
    this.q = [Math.cos(yaw / 2), 0, 0, Math.sin(yaw / 2)];
    this.w = [0, 0, 0];
    this.thrust = [0, 0, 0, 0];
    this.cmd = [0, 0, 0, 0];
    this.t = 0;
    this.onGround = this.pos[2] >= -1e-6;
    this.gustV = [0, 0, 0];
    this.events = [];
    this.maxImpact = 0;
    this.bat = new Battery(this.p.battery_mah, this.p.battery_cells, this.p.battery_r_int_ohm, this.env.batterySoc);
  }

  get height() { return -this.pos[2]; }
  tMax() { return this.p.t_max_per_motor_n * Math.min(1.1, (this.bat.voltage / 7.6) ** 2); }

  wind() {
    const w = this.env.wind, g = this.gustV;
    return [w[0] + g[0], w[1] + g[1], w[2] + g[2]];
  }

  step(cmd, dt) {
    const p = this.p;
    // gusts: Ornstein-Uhlenbeck process with ~1.5 s correlation time (ASSUMPTION)
    if (this.env.gust > 0) {
      const th = 1 / 1.5, sg = this.env.gust * Math.sqrt(2 * th * dt);
      for (let i = 0; i < 3; i++) this.gustV[i] += -th * this.gustV[i] * dt + sg * this.rand.normal() * (i === 2 ? 0.3 : 1);
    }
    const tmax = this.tMax();
    for (let i = 0; i < 4; i++) {
      const c = Math.min(1, Math.max(0, cmd[i]));
      this.cmd[i] = c;
      const target = c * tmax * this.env.motorHealth[i];
      this.thrust[i] += (target - this.thrust[i]) * Math.min(1, dt / p.motor_tau_s);
    }
    const R = qrot(this.q);
    const w = this.wind();
    const air = [this.vel[0] - w[0], this.vel[1] - w[1], this.vel[2] - w[2]];
    const vb = mulRTv(R, air);
    const vax = Math.max(0, -vb[2]);
    const loss = Math.max(0, 1 - vax / p.prop_pitch_speed_ms);
    const T = this.thrust.map((x) => x * loss);
    const Ts = T[0] + T[1] + T[2] + T[3];
    const fb = mulRv(R, [0, 0, -Ts]);
    const sp = Math.hypot(air[0], air[1], air[2]);
    const kd = 0.5 * RHO * p.drag_cda_m2 * sp;
    const f = [fb[0] - kd * air[0], fb[1] - kd * air[1], fb[2] + this.mass * G - kd * air[2]];
    const A = this.Atau, I = this.I, wv = this.w;
    const tau = [0, 1, 2].map((r) => A[r][0] * T[0] + A[r][1] * T[1] + A[r][2] * T[2] + A[r][3] * T[3] - p.angular_drag * wv[r]);
    const Iw = [I[0] * wv[0], I[1] * wv[1], I[2] * wv[2]];
    tau[0] -= wv[1] * Iw[2] - wv[2] * Iw[1];
    tau[1] -= wv[2] * Iw[0] - wv[0] * Iw[2];
    tau[2] -= wv[0] * Iw[1] - wv[1] * Iw[0];
    for (let i = 0; i < 3; i++) {
      this.vel[i] += (f[i] / this.mass) * dt;
      this.w[i] += (tau[i] / I[i]) * dt;
      this.pos[i] += this.vel[i] * dt;
    }
    const dq = qmul(this.q, [0, ...this.w]);
    this.q = qnormalize([this.q[0] + 0.5 * dt * dq[0], this.q[1] + 0.5 * dt * dq[1], this.q[2] + 0.5 * dt * dq[2], this.q[3] + 0.5 * dt * dq[3]]);
    this.contacts(R);
    const tHover = (this.mass * G) / 4;
    const pEach = (tHover / G * 1000) / p.hover_eff_g_per_w;
    let pw = p.electronics_w;
    for (let i = 0; i < 4; i++) pw += pEach * Math.pow(Math.max(T[i], 0) / tHover, 1.5);
    this.bat.step(pw, dt);
    this.t += dt;
  }

  contacts(R) {
    const [L, W, H] = this.course.room;
    if (this.pos[2] >= 0) {
      if (this.vel[2] > 0.5) this.hit("floor", this.vel[2]);
      this.pos[2] = 0;
      if (this.vel[2] > 0) this.vel[2] = 0;
      this.vel[0] *= 0.98; this.vel[1] *= 0.98;
      const up = (this.thrust[0] + this.thrust[1] + this.thrust[2] + this.thrust[3]) * R[8];
      this.onGround = up < this.mass * G * 1.02;
      if (this.onGround) { this.w[0] *= 0.9; this.w[1] *= 0.9; this.w[2] *= 0.9; }
    } else this.onGround = false;
    if (this.pos[2] < -H) { this.hit("ceiling", -this.vel[2]); this.pos[2] = -H; this.vel[2] = Math.max(this.vel[2], 0); }
    for (const [ax, half] of [[0, L / 2 - DRONE_RADIUS], [1, W / 2 - DRONE_RADIUS]]) {
      if (Math.abs(this.pos[ax]) > half) {
        this.hit("wall", Math.abs(this.vel[ax]));
        this.pos[ax] = Math.sign(this.pos[ax]) * half;
        this.vel[ax] *= -0.2;
      }
    }
    const imp = resolveCollisions(this.course, this.pos, this.vel);
    if (imp > 0.05) {
      this.hit("obstacle", imp);
      for (let i = 0; i < 3; i++) this.w[i] += (this.rand() - 0.5) * imp * 20;   // knocks upset the attitude
    }
  }

  hit(kind, speed) {
    if (speed < 0.05) return;
    this.maxImpact = Math.max(this.maxImpact, speed);
    if (this.events.length < 200) this.events.push({ t: this.t, kind, speed });
  }

  /** ToF readings (m), body-fixed rays from world.RAYS; 4 m = nothing seen. */
  tof() {
    const R = qrot(this.q);
    return RAYS.map((r) => {
      const d = mulRv(R, r.d);
      let v = castRay(this.course, this.pos, d, TOF_RANGE);
      if (this.env.tofNoise > 0 && v < TOF_RANGE) v = Math.max(0, v + this.env.tofNoise * this.rand.normal());
      return v;
    });
  }
}
