// SPDX-License-Identifier: MIT
// Wisp Control Lab: the rate-loop model. A line-for-line port of software/wisp_gcs/fit.py (closed_loop,
// loop_response, margins) and steptest.py (score); test/loop.test.mjs checks the two give the same numbers.
//
//   target r -(+)-> AC_PID -u-> delay Td -> motor lag tau -> w' = b*u_m - a*w -> rate w
//              ^(-)                                                                 |
//              +----------- measured rate w_f <- gyro filter (INS_GYRO_FILTER) <----+
//
// Units: rates in rad/s inside the model, deg/s on screen. u is the normalised rate-controller output (-1..1).
// STATUS: Phase 1 draft. Checked against ArduCopter 4.7.2 SITL (software in the loop) only.

export const DT = 1 / 400;                       // a Copter's main loop runs at 400 Hz
export const RAD = Math.PI / 180;

// ArduCopter 4.7.2 defaults for the roll and pitch rate PID (ATC_RAT_RLL_*), read from SITL.
export const ARDU_DEFAULTS = { P: 0.135, I: 0.135, D: 0.0036, FF: 0, FLTD: 20, IMAX: 0.5 };

// Wisp Follow: ESTIMATE from the Phase 0 concept model (b = peak roll torque / inertia, tau = motor time
// constant), not identified from any flight. A 40 Hz gyro filter is a typical small-quad setting (ESTIMATE).
export const WISP_PLANT = { b: 700, a: 0, tau: 0.03, td: 0.0025, gyro_hz: 40, estimate: true };

/** ArduPilot's LowPassFilter2p: a Butterworth biquad, bilinear transform. */
export function biquad(sampleHz, cutoffHz, x0 = 0) {
  if (cutoffHz <= 0) return (x) => x;
  const fr = sampleHz / cutoffHz, ohm = Math.tan(Math.PI / fr);
  const c = 1 + 2 * Math.cos(Math.PI / 4) * ohm + ohm * ohm;
  const b0 = (ohm * ohm) / c, b1 = 2 * b0, b2 = b0;
  const a1 = (2 * (ohm * ohm - 1)) / c, a2 = (1 - 2 * Math.cos(Math.PI / 4) * ohm + ohm * ohm) / c;
  let d1 = x0 / (1 + a1 + a2), d2 = d1;
  return (x) => {
    const d0 = x - d1 * a1 - d2 * a2;
    const y = d0 * b0 + d1 * b1 + d2 * b2;
    d2 = d1; d1 = d0;
    return y;
  };
}

function interp(x, xs, ys) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  return ys[lo] + ((ys[hi] - ys[lo]) * (x - xs[lo])) / (xs[hi] - xs[lo]);
}
export { interp };

/** Simulate the rate loop following des (rad/s, sampled at tDes). Returns arrays t, wf, u, p, i, d. */
export function closedLoop(tDes, des, gains, plant, { w0 = 0, i0 = 0, tEnd, dt = DT } = {}) {
  tEnd ??= tDes[tDes.length - 1];
  const n = Math.round((tEnd - tDes[0]) / dt) + 1;
  const { P: kp, I: ki, D: kd } = gains;
  const ff = gains.FF ?? 0, fltd = gains.FLTD ?? 20, imax = gains.IMAX ?? 0.5;
  const b = plant.b, a = plant.a, tau = Math.max(plant.tau, 1e-4), td = Math.max(plant.td, 0);
  const uSat = plant.u_sat;
  const gyro = biquad(1 / dt, plant.gyro_hz ?? 20, w0);
  const alphaD = fltd > 0 ? dt / (dt + 1 / (2 * Math.PI * fltd)) : 1;
  const nd = Math.round(td / dt);
  const uHold = b ? (a * w0) / b : 0;
  const hist = new Array(nd + 1).fill(uHold);
  let w = w0, wf = w0, um = uHold, integ = i0, dfilt = 0, ePrev = null;
  const out = { t: new Float64Array(n), wf: new Float64Array(n), u: new Float64Array(n),
    p: new Float64Array(n), i: new Float64Array(n), d: new Float64Array(n), r: new Float64Array(n) };
  for (let k = 0; k < n; k++) {
    const t = tDes[0] + k * dt, r = interp(t, tDes, des);
    const e = r - wf;
    if (ePrev !== null) dfilt += alphaD * ((e - ePrev) / dt - dfilt);
    ePrev = e;
    integ = Math.max(-imax, Math.min(imax, integ + ki * e * dt));
    const pT = kp * e, dT = kd * dfilt, u = ff * r + pT + integ + dT;
    hist.push(u);
    const uDel = hist.shift();
    um += (dt / (tau + dt)) * (uDel - um);
    const torque = uSat ? Math.max(-uSat, Math.min(uSat, um)) : um;
    w += (b * torque - a * w) * dt;
    wf = gyro(w);
    out.t[k] = t; out.wf[k] = wf; out.u[k] = u; out.p[k] = pT; out.i[k] = integ; out.d[k] = dT; out.r[k] = r;
  }
  return out;
}

/** A rate-step target the way ArduPilot shapes it: slewed at the axis acceleration limit (ATC_ACC_R_MAX). */
export function shapedStep({ ampDps = 90, dur = 0.4, accMaxDps2 = 1100, pre = 0.3, post = 1.0, dt = 0.005 } = {}) {
  const t = [], des = [];
  let r = 0;
  for (let x = -pre; x <= dur + post + 1e-9; x += dt) {
    t.push(+x.toFixed(6)); des.push(r * RAD);            // value at x, then slew toward the goal
    const goal = x >= -1e-9 && x < dur - 1e-9 ? ampDps : 0;
    const step = accMaxDps2 * dt;
    r += Math.max(-step, Math.min(step, goal - r));
  }
  return { t, des };
}

// ---- frequency domain ----------------------------------------------------------------------------------
const cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cdiv = (a, b) => { const q = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / q, (a[1] * b[0] - a[0] * b[1]) / q]; };
const cadd = (...z) => z.reduce((s, x) => [s[0] + x[0], s[1] + x[1]], [0, 0]);

/** Open-loop response L(j 2 pi f) = C G F, as in fit.py loop_response. */
export function loopResponse(fHz, gains, plant, dt = DT) {
  const w = 2 * Math.PI * fHz, s = [0, w];
  const wd = 2 * Math.PI * (gains.FLTD ?? 20);
  const C = cadd([gains.P, 0], cdiv([gains.I, 0], s), cdiv(cmul([gains.D, 0], s), [1, w / wd]));
  const delay = (plant.td ?? 0) + dt;
  const G = cdiv(cmul([plant.b, 0], [Math.cos(-w * delay), Math.sin(-w * delay)]),
    cmul([plant.a, w], [1, plant.tau * w]));
  const gh = plant.gyro_hz ?? 20;
  let F = [1, 0];
  if (gh > 0) { const wc = 2 * Math.PI * gh; F = cdiv([wc * wc, 0], [wc * wc - w * w, Math.SQRT2 * wc * w]); }
  return cmul(cmul(C, G), F);
}

/** Bode points from 0.1 Hz to 190 Hz: magnitude (dB) and unwrapped phase (deg). */
export function bode(gains, plant, n = 400) {
  const pts = [];
  let prev = null, off = 0;
  for (let k = 0; k < n; k++) {
    const f = 10 ** (-1 + (k / (n - 1)) * (Math.log10(190) + 1));
    const L = loopResponse(f, gains, plant);
    let ph = Math.atan2(L[1], L[0]) + off;
    if (prev !== null) { while (ph - prev > Math.PI) { ph -= 2 * Math.PI; off -= 2 * Math.PI; } while (ph - prev < -Math.PI) { ph += 2 * Math.PI; off += 2 * Math.PI; } }
    prev = ph;
    pts.push({ f, mag: Math.hypot(L[0], L[1]), ph });
  }
  return pts;
}

/** Gain crossover and phase margin, phase crossover and gain margin (fit.py margins). */
export function margins(gains, plant) {
  const pts = bode(gains, plant, 4000);
  const out = { fcHz: null, pmDeg: null, f180Hz: null, gmDb: null };
  for (let k = 0; k < pts.length - 1; k++) {
    const a = pts[k], b = pts[k + 1];
    if (out.fcHz === null && a.mag >= 1 && b.mag < 1) {
      const x = -Math.log(a.mag) / (Math.log(b.mag) - Math.log(a.mag));
      out.fcHz = a.f + (b.f - a.f) * x;
      out.pmDeg = 180 + (a.ph + (b.ph - a.ph) * ((out.fcHz - a.f) / (b.f - a.f))) / RAD;
    }
    if (out.f180Hz === null && a.ph > -Math.PI && b.ph <= -Math.PI) {
      out.f180Hz = b.f + ((a.f - b.f) * (-Math.PI - b.ph)) / (a.ph - b.ph);
      out.gmDb = -20 * Math.log10(a.mag + (b.mag - a.mag) * ((out.f180Hz - a.f) / (b.f - a.f)));
    }
  }
  return out;
}

/** Step scores (steptest.py score): rise 10-90 %, overshoot, 5 % settling, RMS tracking error. deg/s in. */
export function score(t, des, ach, tStep, amp) {
  const pts = [];
  for (let k = 0; k < t.length; k++) if (t[k] >= tStep) pts.push([t[k], des[k], ach[k]]);
  if (pts.length < 5) return null;
  const sign = amp >= 0 ? 1 : -1, A = Math.abs(amp);
  let peakD = pts[0];
  for (const p of pts) if (sign * p[1] > sign * peakD[1]) peakD = p;
  const up = pts.filter((p) => p[0] <= peakD[0] + 0.0001 || sign * p[1] >= 0.98 * A);
  const tEnd = up[up.length - 1][0];
  const win = pts.filter((p) => p[0] <= tEnd);
  const cross = (level) => {
    for (let k = 0; k < win.length - 1; k++) {
      const a0 = sign * win[k][2], a1 = sign * win[k + 1][2];
      if (a0 < level && level <= a1) return win[k][0] + ((win[k + 1][0] - win[k][0]) * (level - a0)) / ((a1 - a0) || 1e-9);
    }
    return null;
  };
  const t10 = cross(0.1 * A), t90 = cross(0.9 * A);
  const peak = Math.max(...win.map((p) => sign * p[2]));
  let settle = null;
  for (let i = 0; i < win.length - 1; i++) {
    if (win.slice(i).every((p) => Math.abs(sign * p[2] - A) <= 0.05 * A)) { settle = win[i][0] - tStep; break; }
  }
  const err = win.map((p) => p[1] - p[2]);
  return {
    rise_s: t10 === null || t90 === null ? null : t90 - t10,
    overshoot_pct: Math.max(0, ((peak - A) / A) * 100),
    settle_s: settle,
    rms_err_dps: Math.sqrt(err.reduce((s, e) => s + e * e, 0) / err.length),
    peak_dps: sign * peak,
  };
}
