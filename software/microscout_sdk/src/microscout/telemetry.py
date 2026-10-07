# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Telemetry record shared by the simulator and (later) the real radio link."""
import csv
import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Telemetry:
    """One telemetry sample.

    position:     (x, y, z) metres in the take-off frame, NED: x forward at take-off, y right, z down
    height:       metres above the take-off floor (= -z)
    velocity:     (vx, vy, vz) m/s, same frame as position
    attitude_deg: (roll, pitch, yaw); roll + = right side down, pitch + = nose up, yaw + = clockwise from above
    rates_dps:    body rates (roll, pitch, yaw) in deg/s
    motors:       motor commands 0..1 (Betaflight order: rear-right, front-right, rear-left, front-left)
    tof_m:        distances from the five ToF sensors (front/rear/left/right/down), None beyond range
    """
    t: float
    position: tuple
    height: float
    velocity: tuple
    attitude_deg: tuple
    quaternion: tuple
    rates_dps: tuple
    motors: tuple
    battery_v: float
    battery_a: float
    battery_pct: float
    tof_m: dict = field(default_factory=dict)
    armed: bool = False
    mode: str = "beginner"
    task: str = None
    status: str = ""
    on_ground: bool = True
    warnings: tuple = ()

    @property
    def roll(self):
        return self.attitude_deg[0]

    @property
    def pitch(self):
        return self.attitude_deg[1]

    @property
    def yaw(self):
        return self.attitude_deg[2]

    @property
    def speed(self):
        return sum(v * v for v in self.velocity) ** 0.5


FIELDS = ["t", "x", "y", "z", "height", "vx", "vy", "vz", "roll", "pitch", "yaw", "p", "q", "r",
          "m1", "m2", "m3", "m4", "battery_v", "battery_a", "battery_pct", "mode", "task", "status"]


def to_rows(log):
    for s in log:
        yield [round(s.t, 4), *[round(v, 4) for v in s.position], round(s.height, 4),
               *[round(v, 4) for v in s.velocity], *[round(v, 3) for v in s.attitude_deg],
               *[round(v, 2) for v in s.rates_dps], *[round(v, 4) for v in s.motors],
               round(s.battery_v, 3), round(s.battery_a, 3), round(s.battery_pct, 2), s.mode, s.task or "", s.status]


def save_csv(log, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(to_rows(log))


def save_trajectory_json(log, path, every=1):
    """Compact pose track for the 3D viewer: t, position (NED), quaternion, motors."""
    data = [dict(t=round(s.t, 3), p=[round(v, 4) for v in s.position], q=[round(v, 5) for v in s.quaternion],
                 m=[round(v, 3) for v in s.motors]) for s in log[::every]]
    with open(path, "w") as f:
        json.dump(dict(frame="NED", samples=data), f, separators=(",", ":"))


def as_dict(sample):
    return asdict(sample)
