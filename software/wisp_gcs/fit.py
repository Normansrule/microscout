# SPDX-License-Identifier: MIT
"""Rate-loop model: predict a step response from a plant and PID gains, and fit the plant to step tests.

Loop, one body axis, small angles, run at 400 Hz (a Copter's main-loop rate):

    target r --(+)--> AC_PID --u--> [delay Td] -> [motor lag tau] -> w' = b*u_m - a*w --> true rate w
               ^(-)                                                                          |
               +------------------- measured rate w_f <-- gyro filter (INS_GYRO_FILTER) <----+

u is the rate controller's output (FF + P + I + D, normalised -1..1, as PID_TUNING reports it). The gyro filter
is ArduPilot's second-order Butterworth low-pass (LowPassFilter2p); PID_TUNING's "achieved" is the filtered
rate, so that is what the model is compared with. AC_PID: P on error, I with an IMAX clamp, D on error through a
first-order filter at FLTD Hz.

`fit` estimates b, a, tau and Td by output error: it simulates the closed loop for each recorded step and
adjusts the four numbers (Nelder-Mead) until the simulated filtered rate matches the recorded one. It is a
first system-identification pass; Phase 6 does it properly from 400 Hz logs.

The Control Lab runs the same loop in JavaScript (docs/control-lab/js/loop.js); tests check the two agree.

STATUS: Phase 1 draft. Validated only against ArduCopter 4.7.2 SITL (software in the loop).
"""
from __future__ import annotations

import math

import numpy as np

DT = 1 / 400


class Biquad:
    """ArduPilot's DigitalBiquadFilter as configured by LowPassFilter2p (Butterworth, bilinear transform)."""

    def __init__(self, sample_hz: float, cutoff_hz: float, x0: float = 0.0):
        self.off = cutoff_hz <= 0
        if self.off:
            return
        fr = sample_hz / cutoff_hz
        ohm = math.tan(math.pi / fr)
        c = 1 + 2 * math.cos(math.pi / 4) * ohm + ohm * ohm
        self.b0 = ohm * ohm / c
        self.b1, self.b2 = 2 * self.b0, self.b0
        self.a1 = 2 * (ohm * ohm - 1) / c
        self.a2 = (1 - 2 * math.cos(math.pi / 4) * ohm + ohm * ohm) / c
        self.d1 = self.d2 = x0 / (1 + self.a1 + self.a2)

    def __call__(self, x: float) -> float:
        if self.off:
            return x
        d0 = x - self.d1 * self.a1 - self.d2 * self.a2
        y = d0 * self.b0 + self.d1 * self.b1 + self.d2 * self.b2
        self.d2, self.d1 = self.d1, d0
        return y


def closed_loop(t_des, des, gains, plant, w0=0.0, i0=0.0, t_end=None, dt=DT):
    """Simulate the rate loop following `des` (rad/s, sampled at t_des).

    gains: P, I, D, FF, FLTD (Hz), IMAX.  plant: b, a, tau, td, gyro_hz, and optionally u_sat (the command
    beyond which the motors give no more torque; the linear model has none).
    Returns t, w_f (filtered, what PID_TUNING reports), u.
    """
    t_end = t_des[-1] if t_end is None else t_end
    n = int(round((t_end - t_des[0]) / dt)) + 1
    t = t_des[0] + np.arange(n) * dt
    r = np.interp(t, t_des, des)
    kp, ki, kd = gains["P"], gains["I"], gains["D"]
    ff, fltd, imax = gains.get("FF", 0.0), gains.get("FLTD", 20.0), gains.get("IMAX", 0.5)
    b, a, tau, td = plant["b"], plant["a"], max(plant["tau"], 1e-4), max(plant["td"], 0.0)
    u_sat = plant.get("u_sat")                  # optional actuator limit (motors at full or idle)
    gyro = Biquad(1 / dt, plant.get("gyro_hz", 20.0), w0)
    alpha_d = dt / (dt + 1 / (2 * math.pi * fltd)) if fltd > 0 else 1.0
    nd = int(round(td / dt))
    u_hold = (a * w0 / b) if b else 0.0         # the command that holds the starting rate
    hist = [u_hold] * (nd + 1)
    w, wf, um, integ, dfilt, e_prev = w0, w0, u_hold, i0, 0.0, None
    wfs, us = np.empty(n), np.empty(n)
    for k in range(n):
        e = r[k] - wf
        if e_prev is not None:
            dfilt += alpha_d * ((e - e_prev) / dt - dfilt)
        e_prev = e
        integ = max(-imax, min(imax, integ + ki * e * dt))
        u = ff * r[k] + kp * e + integ + kd * dfilt
        hist.append(u)
        u_del = hist.pop(0)
        um += dt / (tau + dt) * (u_del - um)
        w += (b * (max(-u_sat, min(u_sat, um)) if u_sat else um) - a * w) * dt
        wf = gyro(w)
        wfs[k], us[k] = wf, u
    return t, wfs, us


def _sse(theta, segments, gyro_hz):
    b, a, tau, td = theta
    if b <= 0 or tau <= 0 or td < 0 or a < 0 or tau > 0.2 or td > 0.05:
        return math.inf
    plant = {"b": b, "a": a, "tau": tau, "td": td, "gyro_hz": gyro_hz}
    total = 0.0
    for s in segments:
        tt, wf, _ = closed_loop(s["t"], s["des"], s["gains"], plant, w0=s["w"][0], i0=s["i0"])
        pred = np.interp(s["t"], tt, wf)
        if not np.all(np.isfinite(pred)):
            return math.inf
        total += float(((pred - s["w"]) ** 2).sum())
    return total


def nelder_mead(f, x0, step, iters=400, tol=1e-10):
    """A small Nelder-Mead minimiser, to keep the tools free of a SciPy dependency."""
    n = len(x0)
    pts = [np.array(x0, float)] + [np.array(x0, float) + np.eye(n)[i] * step[i] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = np.argsort(vals)
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) <= tol * (abs(vals[0]) + tol):
            break
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1])
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (p - pts[0]) for p in pts[1:]]
                vals = [vals[0]] + [f(p) for p in pts[1:]]
    i = int(np.argmin(vals))
    return pts[i], vals[i]


def fit(segments, gyro_hz=20.0, x0=(300.0, 2.0, 0.02, 0.005)):
    """segments: dicts with t, des, w (rad/s), gains, i0. Returns the plant and the fit's r2."""
    best, sse = nelder_mead(lambda th: _sse(th, segments, gyro_hz), x0, step=(60.0, 1.0, 0.01, 0.004))
    y = np.concatenate([s["w"] for s in segments])
    b, a, tau, td = (float(v) for v in best)
    return {"b": b, "a": a, "tau": tau, "td": td, "gyro_hz": gyro_hz,
            "r2": float(1 - sse / ((y - y.mean()) ** 2).sum())}


def score_prediction(segment, plant):
    tt, wf, _ = closed_loop(segment["t"], segment["des"], segment["gains"], plant, w0=segment["w"][0],
                            i0=segment["i0"])
    pred = np.interp(segment["t"], tt, wf)
    w = segment["w"]
    return {"rms_dps": float(math.degrees(np.sqrt(np.mean((pred - w) ** 2)))),
            "r2": float(1 - ((pred - w) ** 2).sum() / ((w - w.mean()) ** 2).sum())}, pred


def loop_response(f_hz, gains, plant, dt=DT):
    """Open-loop frequency response L(j2πf) = C * G * F, continuous-time approximation of `closed_loop`.

    C: PID with filtered D. G: delay (Td plus one sample, from the update order), motor lag, b/(s+a).
    F: second-order Butterworth gyro filter. The FF term acts on the target only, so it is not in the loop.
    """
    s = 2j * np.pi * np.asarray(f_hz, float)
    wd = 2 * np.pi * gains.get("FLTD", 20.0)
    C = gains["P"] + gains["I"] / s + gains["D"] * s / (1 + s / wd)
    G = plant["b"] / ((s + plant["a"]) * (plant["tau"] * s + 1)) * np.exp(-s * (plant["td"] + dt))
    wc = 2 * np.pi * plant.get("gyro_hz", 20.0)
    F = wc * wc / (s * s + np.sqrt(2) * wc * s + wc * wc) if plant.get("gyro_hz", 20.0) > 0 else 1.0
    return C * G * F


def margins(gains, plant):
    """Gain crossover (Hz), phase margin (deg), phase crossover (Hz) and gain margin (dB) of the rate loop."""
    f = np.logspace(-1, np.log10(190), 4000)
    L = loop_response(f, gains, plant)
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    out = {"fc_hz": None, "pm_deg": None, "f180_hz": None, "gm_db": None}
    i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(i):
        k = i[0]
        out["fc_hz"] = float(np.interp(0, [-np.log(mag[k]), -np.log(mag[k + 1])], [f[k], f[k + 1]]))
        out["pm_deg"] = float(180 + np.degrees(np.interp(out["fc_hz"], f[k:k + 2], ph[k:k + 2])))
    j = np.where((ph[:-1] > -np.pi) & (ph[1:] <= -np.pi))[0]
    if len(j):
        k = j[0]
        out["f180_hz"] = float(np.interp(-np.pi, [ph[k + 1], ph[k]], [f[k + 1], f[k]]))
        out["gm_db"] = float(-20 * np.log10(np.interp(out["f180_hz"], f[k:k + 2], mag[k:k + 2])))
    return out
