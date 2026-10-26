// SPDX-License-Identifier: MIT
// Wisp Phase 0 concept mockups: the one loop model every Control Lab mockup draws from.
// Roll-rate loop of Wisp Follow, all numbers ESTIMATES until system identification (roadmap phase 6):
//   plant   P(s) = b e^(-s Td) / (s (tau s + 1))      command -> roll rate (rad/s)
//   control C(s) = Kp + Ki / s + Kd s / (1 + s / wd)  ArduPilot-style rate PID with a filtered D term
// b = max roll torque / Ixx, tau = motor time constant, Td = loop and sensor delay, wd = D-term filter.

export const PLANT = { b: 700, tau: 0.03, Td: 0.0025 };            // 1/s^2, s, s  (ESTIMATE)
export const GAINS = { Kp: 0.135, Ki: 0.135, Kd: 0.0036, fd: 20 }; // fd in Hz   (example values)

const cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cdiv = (a, b) => { const d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };

/** Open-loop L(jw) = C(jw) P(jw). */
export function loop(w, g = GAINS, p = PLANT) {
  const s = [0, w];
  const wd = 2 * Math.PI * g.fd;
  const C = [g.Kp, 0];
  const I = cdiv([g.Ki, 0], s);
  const D = cdiv(cmul([g.Kd, 0], s), [1, w / wd]);
  const c = [C[0] + I[0] + D[0], C[1] + I[1] + D[1]];
  const delay = [Math.cos(-w * p.Td), Math.sin(-w * p.Td)];
  const P = cdiv(cmul([p.b, 0], delay), cmul(s, [1, w * p.tau]));
  return cmul(c, P);
}

/** Bode data over 1..2000 rad/s, with crossover, phase margin and gain margin. */
export function bode(g = GAINS, p = PLANT, n = 240) {
  const pts = [];
  let unwrap = 0, prev = null;
  for (let i = 0; i < n; i++) {
    const w = 10 ** (0 + (Math.log10(2000) * i) / (n - 1));
    const L = loop(w, g, p);
    let ph = (Math.atan2(L[1], L[0]) * 180) / Math.PI + unwrap;
    if (prev !== null) { while (ph - prev > 180) { ph -= 360; unwrap -= 360; } while (ph - prev < -180) { ph += 360; unwrap += 360; } }
    prev = ph;
    pts.push({ w, mag: 20 * Math.log10(Math.hypot(L[0], L[1])), ph });
  }
  let wc = null, pm = null, w180 = null, gm = null;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (wc === null && a.mag >= 0 && b.mag < 0) {
      const f = a.mag / (a.mag - b.mag);
      wc = a.w * (b.w / a.w) ** f; pm = 180 + (a.ph + (b.ph - a.ph) * f);
    }
    if (w180 === null && a.ph > -180 && b.ph <= -180) {
      const f = (a.ph + 180) / (a.ph - b.ph);
      w180 = a.w * (b.w / a.w) ** f; gm = -(a.mag + (b.mag - a.mag) * f);
    }
  }
  return { pts, wc, pm, w180, gm };
}

/** Closed-loop response to a step in rate setpoint (deg/s), simulated at 2 kHz with the same plant. */
export function step(g = GAINS, p = PLANT, amp = 90, T = 0.4) {
  const dt = 0.0005, nd = Math.round(p.Td / dt), wd = 2 * Math.PI * g.fd;
  const buf = new Array(nd + 1).fill(0);
  let rate = 0, acc = 0, integ = 0, dFilt = 0, prevE = amp * Math.PI / 180, torqueState = 0;
  const out = [];
  for (let k = 0; k * dt <= T; k++) {
    const sp = (amp * Math.PI) / 180;
    const e = sp - rate;
    integ += e * dt;
    const dRaw = (e - prevE) / dt; prevE = e;
    dFilt += (dRaw - dFilt) * Math.min(1, wd * dt);
    const u = Math.max(-1, Math.min(1, g.Kp * e + g.Ki * integ + g.Kd * dFilt));
    buf.push(u); const ud = buf.shift();
    torqueState += (ud - torqueState) * (dt / p.tau);
    acc = p.b * torqueState;
    rate += acc * dt;
    if (k % 4 === 0) out.push({ t: k * dt, rate: (rate * 180) / Math.PI, u, e, integ, d: dFilt });
  }
  const sp = amp;
  const peak = Math.max(...out.map((o) => o.rate));
  const rise = out.find((o) => o.rate >= 0.9 * sp)?.t ?? null;
  let settle = null;
  for (let i = out.length - 1; i >= 0; i--) if (Math.abs(out[i].rate - sp) > 0.05 * sp) { settle = out[Math.min(out.length - 1, i + 1)].t; break; }
  return { out, sp, overshoot: Math.max(0, (peak - sp) / sp), rise, settle };
}

/** The PID output for one sample, with every term, for the live equation. */
export function pidTerms(e, integ, de, g = GAINS) {
  const P = g.Kp * e, I = g.Ki * integ, D = g.Kd * de;
  return { P, I, D, u: P + I + D };
}
