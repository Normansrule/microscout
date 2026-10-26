// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// JavaScript port of software/microscout_sdk/src/microscout/sim/physics.py: rigid-body quadrotor,
// first-order motors, inflow thrust loss, drag (with wind), a simple 2S battery, plus the Flight
// Lab extras: obstacles, gusts, motor damage, payload and ToF sensor noise, and the electrical limits the
// design sets (review/G2/protection.md): the firmware battery-current limit (DR-06, 30 A) and the TLV6700
// hardware under-voltage cut-off (5.77 V, RC filter 0.48 s, D-053). All parameters are ESTIMATES from
// review/G1/calc/budgets.py - this is not the real drone.

import { G, RHO, qmul, qnormalize, qrot, mulRv, mulRTv, rng } from "./math.js";
import { RAYS, TOF_RANGE, castRay, resolveCollisions, DRONE_RADIUS } from "./world.js";

export const DEFAULT_PARAMS = {
  mass_kg: 0.0862, motor_to_motor_m: 0.095, ixx: 4.69e-5, iyy: 5.76e-5, izz: 8.56e-5,
  t_max_per_motor_n: 0.085 * 9.81, motor_tau_s: 0.03, yaw_torque_per_thrust_m: 0.012,
  prop_pitch_speed_ms: 59.0, drag_cda_m2: 0.010, angular_drag: 2.0e-6, battery_mah: 550, battery_cells: 2,
  battery_r_int_ohm: 0.045, hover_eff_g_per_w: 3.0, electronics_w: 2.98, motor_spin: [1, -1, -1, 1],
  full_power_w: 68.1,                    // one motor at full throttle: 9.20 A at 7.4 V (S15 vendor table, budgets 3d)
  pack_mass_g: 29,                       // 2S 550 mAh LiHV (budgets, OQ-2); included in mass_kg
  current_limit_a: 30,                   // firmware battery-current limit (DR-06): the XT30 is rated 30 A peak
  uv_cutoff_v: 5.77, uv_tau_s: 0.48,     // hardware cut-off U23 TLV6700: trip voltage and its RC filter (D-053)
  crush_m: 0.005,                        // ASSUMPTION: how far the frame and guards give in a hit (impact g estimate)
};

/** Battery packs the Situations tab offers (OQ-2): mass, and capacity for the alternative (550 = battery_mah). */
export const PACKS = { 550: { mah: null, mass_g: 29 }, 450: { mah: 450, mass_g: 26 } };

// Per-cell open-circuit voltage of a LiHV cell against state of charge (ESTIMATE, same table as the SDK)
const OCV_SOC = [0.0, 0.03, 0.07, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0];
const OCV_V = [3.00, 3.30, 3.50, 3.65, 3.75, 3.85, 3.98, 4.12, 4.35];
/** State of charge at which the cell's open-circuit voltage is v (inverse of cellOcv). */
export function socAt(v) {
  for (let i = 1; i < OCV_V.length; i++) if (v <= OCV_V[i]) return OCV_SOC[i - 1] + ((OCV_SOC[i] - OCV_SOC[i - 1]) * (v - OCV_V[i - 1])) / (OCV_V[i] - OCV_V[i - 1]);
  return 1;
}
// The on-board charger (BQ25887, D-033) stops at 8.4 V, 4.2 V per cell, below the pack's 4.35 V LiHV rating:
// "100 %" in the lab is that charge, about 90 % of the pack's rated capacity on this table.
export const CHARGED_SOC = socAt(4.2);

export function cellOcv(soc) {
  if (soc <= 0) return OCV_V[0];
  for (let i = 1; i < OCV_SOC.length; i++) if (soc <= OCV_SOC[i]) return OCV_V[i - 1] + ((OCV_V[i] - OCV_V[i - 1]) * (soc - OCV_SOC[i - 1])) / (OCV_SOC[i] - OCV_SOC[i - 1]);
  return OCV_V[OCV_V.length - 1];
}

export class Battery {
  constructor(mah, cells, rInt, soc = 1) {
    this.cap = mah * 3.6; this.used = this.cap * (1 - soc); this.cells = cells; this.r = rInt;
    this.current = 0; this.voltage = this.ocv();
  }
  get soc() { return Math.max(0, 1 - this.used / this.cap); }
  ocv() { return this.cells * cellOcv(this.soc); }
  step(power, dt) {
    const v = this.ocv();
    let i = power / Math.max(v, 1e-3);
    for (let k = 0; k < 3; k++) { const vt = Math.max(v - i * this.r, 0.5 * v); i = power / vt; }
    this.current = i; this.voltage = v - i * this.r; this.used += i * dt;
  }
}

/** Impact estimate: kinetic energy E = m v^2 / 2 and mean deceleration a = v^2 / (2 d) over a crush distance d, in g. */
export function impact(mass, speed, crush) {
  return { energy_j: 0.5 * mass * speed * speed, g: (speed * speed) / (2 * crush) / G };
}

export class Quad {
  /**
   * @param {object} course from world.buildCourse
   * @param {object} env {wind:[x,y,z] m/s, gust: m/s, motorHealth:[4], payload_g, tofNoise: m, batterySoc, seed,
   *   pack: 550 | 450 (mAh), currentLimit: A (0 = off), hwCutoff: true | false}
   */
  constructor(course, params = DEFAULT_PARAMS, env = {}) {
    this.p = { ...DEFAULT_PARAMS, ...params };
    this.course = course;
    this.env = { wind: [0, 0, 0], gust: 0, motorHealth: [1, 1, 1, 1], payload_g: 0, tofNoise: 0, batterySoc: 1, seed: 1,
      pack: 550, currentLimit: this.p.current_limit_a, hwCutoff: true, ...env };
    this.rand = rng(this.env.seed);
    const pack = PACKS[this.env.pack] || PACKS[550];
    this.packMah = pack.mah || this.p.battery_mah;
    this.mass = this.p.mass_kg + (pack.mass_g - this.p.pack_mass_g) / 1000 + this.env.payload_g / 1000;
    // motor power P = P_ref (T / T_ref)^n through two budget anchors (ESTIMATE): hover of the drone as designed at
    // 3.0 g/W, and the vendor's full-throttle power at the lab's full thrust: n = ln(P_full / P_ref) / ln(T_max / T_ref)
    this.tRef = (this.p.mass_kg * G) / 4;
    this.pRefEach = (this.tRef / G * 1000) / this.p.hover_eff_g_per_w;
    this.powerN = Math.log(this.p.full_power_w / this.pRefEach) / Math.log(this.p.t_max_per_motor_n / this.tRef);
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
    this.worstHit = null;
    this.bat = new Battery(this.packMah, this.p.battery_cells, this.p.battery_r_int_ohm, this.env.batterySoc * CHARGED_SOC);
    this.usedStart = this.bat.used;      // charge already gone at the start (coulombs)
    this.vFilt = this.bat.voltage;       // the cut-off's RC-filtered view of the battery voltage
    this.cutoff = false;                 // true once the hardware cut-off has switched the drone off
    this.limiting = false;               // firmware current limit active this step
    this.limitTime = 0;                  // seconds spent current-limited
    this.motorA = [0, 0, 0, 0];          // battery current drawn by each motor (A)
    this.alerts = [];                    // power events: {t, kind: "limit" | "cutoff", v}
  }

  /** Electrical power drawn by one motor at thrust T (N): P = P_ref (T / T_ref)^n (n about 1.64). */
  motorPower(T) { return this.pRefEach * Math.pow(Math.max(T, 0) / this.tRef, this.powerN); }

  get height() { return -this.pos[2]; }
  /** Charge drawn since the start of this flight (mAh). */
  get usedMah() { return (this.bat.used - this.usedStart) / 3.6; }
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
    const target = [0, 0, 0, 0];
    for (let i = 0; i < 4; i++) {
      const c = this.cutoff ? 0 : Math.min(1, Math.max(0, cmd[i]));
      this.cmd[i] = c;
      target[i] = c * tmax * this.env.motorHealth[i];
    }
    // firmware current limit (DR-06), modelled as a feed-forward on the commanded thrust: if the commanded thrust
    // would draw more than the limit, every motor is scaled by k with sum P(k T) = I_lim V - P_elec, so
    // k = ((I_lim V - P_elec) / sum P(T))^(1/n)
    const lim = this.env.currentLimit;
    const wasLimiting = this.limiting;
    this.limiting = false;
    if (lim > 0 && !this.cutoff) {
      const v = Math.max(1, Math.min(this.bat.voltage, this.bat.ocv() - lim * this.bat.r));   // terminal voltage at the limit
      const pm = target.reduce((a, t) => a + this.motorPower(t), 0);
      if ((pm + p.electronics_w) / v > lim && pm > 0) {
        const k = Math.pow(Math.max(0, lim * v - p.electronics_w) / pm, 1 / this.powerN);
        for (let i = 0; i < 4; i++) target[i] *= k;
        this.limiting = true;
        this.limitTime += dt;
        if (!wasLimiting && (!this.alerts.length || this.t - this.alerts[this.alerts.length - 1].t > 2)) this.alerts.push({ t: this.t, kind: "limit", v: lim });
      }
    }
    for (let i = 0; i < 4; i++) this.thrust[i] += (target[i] - this.thrust[i]) * Math.min(1, dt / p.motor_tau_s);
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
    // power follows the thrust the motors are spinning for (before the inflow loss: at a given speed the motor
    // works as hard in a climb); after a cut-off the soft switch has turned the electronics off too
    let pw = this.cutoff ? 0 : p.electronics_w;
    const pmot = this.thrust.map((x) => this.motorPower(x));
    for (let i = 0; i < 4; i++) pw += pmot[i];
    this.bat.step(pw, dt);
    for (let i = 0; i < 4; i++) this.motorA[i] = pmot[i] / Math.max(this.bat.voltage, 1e-3);
    // hardware under-voltage cut-off: the TLV6700 sees the battery through an RC filter (tau 0.48 s), so a short
    // sag under a throttle punch does not trip it; once tripped, the soft switch turns the drone off
    this.vFilt += (this.bat.voltage - this.vFilt) * Math.min(1, dt / p.uv_tau_s);
    if (this.env.hwCutoff && !this.cutoff && this.vFilt < p.uv_cutoff_v) {
      this.cutoff = true;
      this.alerts.push({ t: this.t, kind: "cutoff", v: this.vFilt });
    }
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
    const e = { t: this.t, kind, speed, ...impact(this.mass, speed, this.p.crush_m) };
    if (!this.worstHit || speed > this.worstHit.speed) this.worstHit = e;
    if (this.events.length < 200) this.events.push(e);
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
