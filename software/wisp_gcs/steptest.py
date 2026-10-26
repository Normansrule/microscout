# SPDX-License-Identifier: MIT
"""Rate-loop step test: what to command, and how to score the response.

The test runs in ArduCopter's Guided mode with SET_ATTITUDE_TARGET messages:
  1. hold level for `lead` seconds,
  2. command a body-rate step of `amp` deg/s on one axis (attitude ignored) for `dur` seconds,
  3. command zero body rate for `tail` seconds (the step back down),
  4. hold level again for `recover` seconds.
ArduPilot shapes the step (ATC_ACC_*_MAX acceleration limits), so the rate loop's own target, reported in
PID_TUNING `desired`, is the reference the response is scored against, not the raw command.

STATUS: Phase 1 draft, exercised in ArduCopter 4.7.2 SITL (software in the loop) only. On a real Wisp this test
is only for a tethered or netted drone (Phase 3), never free flight near people.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# SET_ATTITUDE_TARGET type_mask bits (MAVLink ATTITUDE_TARGET_TYPEMASK)
IGNORE_ROLL_RATE, IGNORE_PITCH_RATE, IGNORE_YAW_RATE = 1, 2, 4
IGNORE_THRUST, IGNORE_ATTITUDE = 64, 128
HOLD_ALTITUDE_THRUST = 0.5      # Guided reads thrust as a climb rate by default: 0.5 means hold altitude

AXES = ("roll", "pitch", "yaw")


@dataclass(frozen=True)
class StepPlan:
    axis: str = "roll"
    amp: float = 90.0        # deg/s
    lead: float = 0.5        # s
    dur: float = 0.4         # s
    tail: float = 0.4        # s
    recover: float = 2.0     # s

    def __post_init__(self):
        if self.axis not in AXES:
            raise ValueError(f"axis must be one of {AXES}")
        if not 5.0 <= abs(self.amp) <= 360.0:
            raise ValueError("amp must be 5-360 deg/s")
        if not 0.05 <= self.dur <= 1.0:
            raise ValueError("dur must be 0.05-1.0 s")
        # Tilt reached during the step, roughly amp * dur. Keep it moderate so the drone stays near hover.
        if self.axis != "yaw" and abs(self.amp) * self.dur > 45.0:
            raise ValueError("amp x dur over 45 degrees of tilt; shorten the step")

    @property
    def total(self) -> float:
        return self.lead + self.dur + self.tail + self.recover

    def command(self, t: float, yaw_deg: float) -> dict:
        """The SET_ATTITUDE_TARGET fields to send `t` seconds into the test."""
        if self.lead <= t < self.lead + self.dur + self.tail:
            rate = math.radians(self.amp) if t < self.lead + self.dur else 0.0
            rates = [0.0, 0.0, 0.0]
            rates[AXES.index(self.axis)] = rate
            return {"type_mask": IGNORE_ATTITUDE, "q": [1.0, 0.0, 0.0, 0.0], "rates": rates,
                    "thrust": HOLD_ALTITUDE_THRUST, "phase": "step" if rate else "zero"}
        return {"type_mask": IGNORE_ROLL_RATE | IGNORE_PITCH_RATE | IGNORE_YAW_RATE,
                "q": level_quaternion(yaw_deg), "rates": [0.0, 0.0, 0.0],
                "thrust": HOLD_ALTITUDE_THRUST, "phase": "level"}


def level_quaternion(yaw_deg: float) -> list[float]:
    h = math.radians(yaw_deg) / 2
    return [math.cos(h), 0.0, 0.0, math.sin(h)]


def score(t, des, ach, t_step, amp):
    """Score a response to a step that starts at `t_step`. `des` is the shaped target the rate loop saw.

    Returns rise time (10-90 % of amp), overshoot (% of amp), 5 % settling time and the RMS (root mean square)
    tracking error over the step, all from the sampled data, so they are only as fine as the sample rate.
    """
    pts = [(ti, d, a) for ti, d, a in zip(t, des, ach) if ti >= t_step]
    if len(pts) < 5:
        return None
    sign = 1.0 if amp >= 0 else -1.0
    A = abs(amp)
    # the step's "up" part ends when the target starts falling again
    peak_d = max(pts, key=lambda p: sign * p[1])
    up = [p for p in pts if p[0] <= peak_d[0] + 0.0001 or sign * p[1] >= 0.98 * A]
    t_end = up[-1][0]
    win = [p for p in pts if p[0] <= t_end]

    def first_cross(level):
        for (t0, _, a0), (t1, _, a1) in zip(win, win[1:]):
            if sign * a0 < level <= sign * a1:
                return t0 + (t1 - t0) * (level - sign * a0) / ((sign * a1 - sign * a0) or 1e-9)
        return None

    t10, t90 = first_cross(0.1 * A), first_cross(0.9 * A)
    peak = max(sign * p[2] for p in win)
    settle = None
    for i in range(len(win)):
        if all(abs(sign * p[2] - A) <= 0.05 * A for p in win[i:]) and i < len(win) - 1:
            settle = win[i][0] - t_step
            break
    err = [d - a for _, d, a in win]
    return {
        "rise_s": None if (t10 is None or t90 is None) else round(t90 - t10, 4),
        "overshoot_pct": round(max(0.0, (peak - A) / A * 100.0), 1),
        "settle_s": None if settle is None else round(settle, 3),
        "rms_err_dps": round(math.sqrt(sum(e * e for e in err) / len(err)), 2),
        "peak_dps": round(sign * peak, 1),
        "window_s": round(t_end - t_step, 3),
    }
