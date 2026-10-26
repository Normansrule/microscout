# SPDX-License-Identifier: MIT
"""Turn MAVLink messages into the JSON the Wisp apps read.

Pure functions and a small state object, no I/O, so the same code runs live (bridge.py), on a recorded
session (replay) and in the tests. Field names and units are part of the app contract: SI units, angles in
degrees for display, rates in deg/s, time in seconds.

STATUS: Phase 1 draft. Checked against ArduCopter 4.7.2 SITL (software in the loop) only; never against a real
vehicle.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

# ArduCopter custom_mode numbers (ArduCopter/mode.h, 4.7.2)
COPTER_MODES = {
    0: "STABILIZE", 2: "ALT_HOLD", 3: "AUTO", 4: "GUIDED", 5: "LOITER", 6: "RTL", 9: "LAND",
    16: "POSHOLD", 17: "BRAKE", 23: "FOLLOW", 25: "SYSTEMID",
}
MODE_NUMBERS = {v: k for k, v in COPTER_MODES.items()}

# PID_TUNING axis ids (MAVLink PID_TUNING_AXIS)
PID_AXES = {1: "roll", 2: "pitch", 3: "yaw", 4: "accz"}
AXIS_IDS = {v: k for k, v in PID_AXES.items()}

# EKF_STATUS_REPORT flags worth showing (MAVLink EKF_STATUS_FLAGS)
EKF_FLAGS = {
    1: "attitude", 2: "velocity_horiz", 4: "velocity_vert", 8: "pos_horiz_rel", 16: "pos_horiz_abs",
    32: "pos_vert_abs", 64: "pos_vert_agl", 128: "const_pos_mode", 256: "pred_pos_horiz_rel",
    512: "pred_pos_horiz_abs", 1024: "uninitialized", 32768: "gps_glitch",
}

MAV_MODE_FLAG_SAFETY_ARMED = 128


def deg(x: float) -> float:
    return math.degrees(x)


@dataclass
class PidSample:
    """One PID_TUNING message. Rate-loop values: desired and achieved in deg/s; ff, p, i, d are the terms'
    contributions to the normalised motor command (-1..1), as ArduPilot's AC_PID reports them."""
    t: float
    axis: str
    des: float
    ach: float
    ff: float
    p: float
    i: float
    d: float

    def as_list(self) -> list:
        return [round(self.t, 4), self.axis, round(self.des, 3), round(self.ach, 3),
                round(self.ff, 5), round(self.p, 5), round(self.i, 5), round(self.d, 5)]


@dataclass
class VehicleState:
    """The latest value of everything the apps show. `update` returns a PidSample for PID_TUNING messages
    (they are streamed in batches, not folded into the state) and None otherwise."""
    t: float = 0.0
    mode: str = "UNKNOWN"
    armed: bool = False
    heartbeat_t: float | None = None
    att_t: float | None = None         # when the newest ATTITUDE arrived
    att: dict = field(default_factory=lambda: {"roll": 0.0, "pitch": 0.0, "yaw": 0.0})
    rates: dict = field(default_factory=lambda: {"p": 0.0, "q": 0.0, "r": 0.0})
    pos: dict | None = None            # local NED (north-east-down) from home, metres
    vel: dict | None = None            # local NED, m/s
    alt_rel: float | None = None       # metres above home
    gps: dict | None = None
    batt: dict | None = None
    ekf: dict | None = None
    statustext: list = field(default_factory=list)
    params: dict = field(default_factory=dict)

    def update(self, m: dict, t: float) -> PidSample | None:
        kind = m.get("mavpackettype")
        self.t = t
        if kind == "HEARTBEAT":
            if m.get("type") == 6:                 # MAV_TYPE_GCS: our own or another ground station's
                return None
            self.mode = COPTER_MODES.get(m["custom_mode"], f"MODE{m['custom_mode']}")
            self.armed = bool(m["base_mode"] & MAV_MODE_FLAG_SAFETY_ARMED)
            self.heartbeat_t = t
        elif kind == "ATTITUDE":
            self.att_t = t
            self.att = {"roll": deg(m["roll"]), "pitch": deg(m["pitch"]), "yaw": deg(m["yaw"]) % 360}
            self.rates = {"p": deg(m["rollspeed"]), "q": deg(m["pitchspeed"]), "r": deg(m["yawspeed"])}
        elif kind == "LOCAL_POSITION_NED":
            self.pos = {"n": m["x"], "e": m["y"], "d": m["z"]}
            self.vel = {"n": m["vx"], "e": m["vy"], "d": m["vz"]}
        elif kind == "GLOBAL_POSITION_INT":
            self.alt_rel = m["relative_alt"] / 1000.0
        elif kind == "GPS_RAW_INT":
            self.gps = {"fix": m["fix_type"], "sats": m["satellites_visible"],
                        "lat": m["lat"] / 1e7, "lon": m["lon"] / 1e7}
        elif kind == "SYS_STATUS":
            pct = m["battery_remaining"]
            self.batt = {"v": m["voltage_battery"] / 1000.0,
                         "a": None if m["current_battery"] < 0 else m["current_battery"] / 100.0,
                         "pct": None if pct < 0 else pct}
        elif kind == "EKF_STATUS_REPORT":
            flags = m["flags"]
            # The variances here are test ratios: innovation squared over its allowed variance. Above 1.0 the
            # EKF (extended Kalman filter) rejects that sensor's measurement.
            self.ekf = {
                "flags": [name for bit, name in EKF_FLAGS.items() if flags & bit],
                "vel": m["velocity_variance"], "pos_h": m["pos_horiz_variance"],
                "pos_v": m["pos_vert_variance"], "compass": m["compass_variance"],
                "terrain": m["terrain_alt_variance"],
            }
        elif kind == "STATUSTEXT":
            self.statustext = (self.statustext + [[round(t, 2), m["severity"], m["text"]]])[-20:]
        elif kind == "PARAM_VALUE":
            self.params[m["param_id"]] = m["param_value"]
        elif kind == "PID_TUNING":
            axis = PID_AXES.get(m["axis"], str(m["axis"]))
            scale = 1.0 if axis == "accz" else math.degrees(1.0)   # rate loops report rad/s
            return PidSample(t, axis, m["desired"] * scale, m["achieved"] * scale,
                             m["FF"], m["P"], m["I"], m["D"])
        return None

    def snapshot(self, now: float) -> dict:
        hb_age = None if self.heartbeat_t is None else round(now - self.heartbeat_t, 2)
        return {
            "type": "state", "t": round(self.t, 3), "mode": self.mode, "armed": self.armed,
            "heartbeat_age": hb_age,
            "att_age_ms": None if self.att_t is None else round((now - self.att_t) * 1000, 1), "att": _round(self.att, 2), "rates": _round(self.rates, 2),
            "pos": _round(self.pos, 3), "vel": _round(self.vel, 3), "alt_rel": _r(self.alt_rel, 2),
            "gps": self.gps, "batt": self.batt, "ekf": _round(self.ekf, 4),
        }


def _r(x, n):
    return None if x is None else round(x, n)


def _round(d, n):
    if d is None:
        return None
    return {k: (round(v, n) if isinstance(v, float) else v) for k, v in d.items()}


class Dejitter:
    """Timestamps for a fixed-rate stream that has no timestamps of its own (PID_TUNING).

    Messages are stamped when they arrive, so a delay on the computer (another program busy, the reader thread
    waiting) makes several arrive at once with the same time. This spreads such a burst back out at the
    stream's period: each stamp is the earlier of the arrival time and the previous stamp plus 1.01 periods, so
    it never runs ahead of the arrival time and, once the burst is over, falls back onto it. The period is the
    average spacing over the last 500 arrivals, which a short burst barely moves; a stamp is never more than
    0.25 s behind its arrival.
    """

    def __init__(self, period: float = 0.01, window: int = 500, max_lag: float = 0.25):
        self.period = period
        self.arrivals: deque = deque(maxlen=window)
        self.max_lag = max_lag
        self.last: float | None = None

    def __call__(self, arrival: float) -> float:
        self.arrivals.append(arrival)
        if len(self.arrivals) >= 50:
            self.period = (self.arrivals[-1] - self.arrivals[0]) / (len(self.arrivals) - 1)
        if self.last is None or len(self.arrivals) < 50:      # still learning the period: trust arrivals
            t = arrival if self.last is None else max(arrival, self.last + 1e-4)
        else:
            t = min(arrival, self.last + 1.01 * self.period)
            t = max(t, self.last + 1e-4, arrival - self.max_lag)   # never far behind, never backwards
        self.last = t
        return t
