// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Flight recorder: samples one simulated drone at a fixed rate of simulation time, summarises the flight,
// writes CSV, and gives back the pose at any time (for ghost replays). Plain JavaScript, no DOM, so the
// tests can run it under Node.

import { toEuler, qnormalize } from "./math.js";

export const COLUMNS = [
  "t_s", "x_m", "y_m", "height_m", "vx_ms", "vy_ms", "vz_ms", "roll_deg", "pitch_deg", "yaw_deg",
  "m1_cmd", "m2_cmd", "m3_cmd", "m4_cmd", "thrust_n", "battery_v", "battery_a", "used_mah",
  "m1_a", "m2_a", "m3_a", "m4_a", "current_limited", "power_cut",
];
const R2D = 180 / Math.PI;

export class Recording {
  constructor(name, rate = 50, maxSeconds = 900) {
    this.name = name; this.dt = 1 / rate; this.max = Math.round(maxSeconds * rate);
    this.rows = []; this.q = []; this.worst = null; this.alerts = []; this.next = 0; this.full = false;
  }

  /** Call after every physics step; keeps one row per 1/rate s of simulation time. */
  sample(quad) {
    if (quad.t + 1e-9 < this.next || this.full) return;
    if (this.rows.length >= this.max) { this.full = true; return; }
    this.next = quad.t + this.dt;
    const [r, p, y] = toEuler(quad.q);
    this.rows.push([
      quad.t, quad.pos[0], quad.pos[1], -quad.pos[2], quad.vel[0], quad.vel[1], -quad.vel[2], r * R2D, p * R2D, y * R2D,
      ...quad.cmd, quad.thrust.reduce((a, b) => a + b, 0), quad.bat.voltage, quad.bat.current, quad.usedMah,
      ...quad.motorA, quad.limiting ? 1 : 0, quad.cutoff ? 1 : 0,
    ]);
    this.q.push([...quad.q]);
    this.worst = quad.worstHit;
    this.alerts = quad.alerts.slice();
  }

  get duration() { return this.rows.length ? this.rows[this.rows.length - 1][0] - this.rows[0][0] : 0; }

  col(name) { const i = COLUMNS.indexOf(name); return this.rows.map((r) => r[i]); }

  /** Numbers for the summary panel. */
  stats(cells = 2) {
    const n = this.rows.length;
    if (!n) return null;
    const c = (k) => COLUMNS.indexOf(k);
    let dist = 0, vmax = 0, hmax = 0, imax = 0, vmin = Infinity, limited = 0;
    for (let i = 0; i < n; i++) {
      const r = this.rows[i];
      if (i) { const s = this.rows[i - 1]; dist += Math.hypot(r[1] - s[1], r[2] - s[2], r[3] - s[3]); }
      vmax = Math.max(vmax, Math.hypot(r[c("vx_ms")], r[c("vy_ms")], r[c("vz_ms")]));
      hmax = Math.max(hmax, r[c("height_m")]);
      imax = Math.max(imax, r[c("battery_a")]);
      vmin = Math.min(vmin, r[c("battery_v")] / cells);
      if (r[c("current_limited")]) limited += this.dt;
    }
    const worst = this.worst || null;
    return {
      duration: this.duration, distance: dist, maxSpeed: vmax, maxHeight: hmax, maxCurrent: imax, minCellV: vmin,
      usedMah: this.rows[n - 1][c("used_mah")] - this.rows[0][c("used_mah")], limited, worst,
      powerCut: this.alerts.find((a) => a.kind === "cutoff") || null,
    };
  }

  toCSV() {
    const head = [
      "# MicroScout Flight Lab flight recording - simulation with estimated parameters, not a real flight",
      `# ${this.name}; ${this.rows.length} rows at ${Math.round(1 / this.dt)} Hz of simulation time; heights and vertical speed positive up`,
      COLUMNS.join(","),
    ];
    const fmt = (v) => (Number.isInteger(v) ? String(v) : v.toFixed(4));
    return head.concat(this.rows.map((r) => r.map(fmt).join(","))).join("\n") + "\n";
  }

  /** Position (NED, m) and attitude quaternion at time t, interpolated; null outside the recording. */
  poseAt(t) {
    const n = this.rows.length;
    if (!n) return null;
    const t0 = this.rows[0][0];
    if (t < t0 || t > this.rows[n - 1][0]) return null;
    const k = Math.min(n - 2, Math.max(0, Math.floor((t - t0) / this.dt)));
    if (n === 1) return { pos: [this.rows[0][1], this.rows[0][2], -this.rows[0][3]], q: this.q[0] };
    const a = this.rows[k], b = this.rows[k + 1];
    const f = Math.min(1, Math.max(0, (t - a[0]) / Math.max(1e-9, b[0] - a[0])));
    const L = (i) => a[i] + (b[i] - a[i]) * f;
    const qa = this.q[k], qb0 = this.q[k + 1];
    const sgn = qa[0] * qb0[0] + qa[1] * qb0[1] + qa[2] * qb0[2] + qa[3] * qb0[3] < 0 ? -1 : 1;
    const q = qnormalize(qa.map((v, i) => v + (sgn * qb0[i] - v) * f));
    return { pos: [L(1), L(2), -L(3)], q };
  }
}
