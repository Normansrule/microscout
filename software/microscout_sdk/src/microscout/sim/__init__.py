# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""In-process simulator: physics + reference flight controller + telemetry."""
import math

import numpy as np

from ..mathutil import to_euler
from ..params import SimConfig
from ..telemetry import Telemetry
from .fc import CommandRejected, FlightController
from .physics import QuadPhysics

__all__ = ["Simulator", "CommandRejected"]


class Simulator:
    def __init__(self, config=None):
        self.cfg = config or SimConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.phys = QuadPhysics(self.cfg.params, self.cfg.room_m)
        self.fc = FlightController(self.phys, self.cfg.gains, self.cfg.safety)
        self.log = []
        self._next_tel = 0.0

    @property
    def t(self):
        return self.phys.t

    def step(self, n=1):
        dt = self.cfg.dt
        for _ in range(n):
            u = self.fc.step(dt)
            self.phys.step(u, dt)
            if self.phys.t + 1e-12 >= self._next_tel:
                self.log.append(self.telemetry())
                self._next_tel += 1.0 / self.cfg.telemetry_hz

    def run_for(self, seconds):
        self.step(int(round(seconds / self.cfg.dt)))

    def run_until(self, predicate, timeout):
        t_end = self.t + timeout
        while self.t < t_end:
            self.step(10)
            if predicate():
                return True
        return False

    def telemetry(self):
        ph = self.phys
        r, p, y = to_euler(ph.q)
        noise = self.cfg.sensor_noise
        tof = ph.tof()
        if noise:
            tof = {k: (None if v is None else v + self.rng.normal(0, 0.01)) for k, v in tof.items()}
        return Telemetry(
            t=ph.t,
            position=tuple(float(v) for v in ph.pos),
            height=float(ph.height),
            velocity=tuple(float(v) for v in ph.vel),
            attitude_deg=(math.degrees(r), math.degrees(p), math.degrees(y)),
            quaternion=tuple(float(v) for v in ph.q),
            rates_dps=tuple(float(math.degrees(v)) for v in ph.w),
            motors=tuple(float(v) for v in ph.cmd),
            battery_v=float(ph.bat.voltage),
            battery_a=float(ph.bat.current),
            battery_pct=float(ph.bat.soc * 100),
            tof_m=tof,
            armed=self.fc.armed,
            mode=self.fc.mode,
            task=self.fc.task,
            status=self.fc.status,
            on_ground=ph.on_ground,
            warnings=tuple(self.fc.warnings[-3:]),
        )
