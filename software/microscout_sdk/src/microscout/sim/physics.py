# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Rigid-body quadrotor model with first-order motors, inflow thrust loss, drag,
a simple battery and a box-shaped room.

It is a teaching and pre-flight tool: every parameter is an estimate until it is
identified from real flight logs (Gate G7). NED world frame, FRD body frame.
"""
import math

import numpy as np

from ..mathutil import qmul, qnorm, qrot

G = 9.81
RHO = 1.225


class Battery:
    def __init__(self, mah, cells, r_int):
        self.cap_c = mah * 3.6          # coulombs
        self.used_c = 0.0
        self.cells = cells
        self.r_int = r_int
        self.current = 0.0
        self.voltage = self.ocv()

    @property
    def soc(self):
        return max(0.0, 1.0 - self.used_c / self.cap_c)

    def ocv(self):
        # crude per-cell open-circuit curve (ASSUMPTION): 3.5 V empty .. 4.2 V full
        return self.cells * (3.5 + 0.7 * self.soc)

    def step(self, power_w, dt):
        v = self.ocv()
        i = power_w / max(v, 1e-3)
        for _ in range(3):              # solve V = OCV - I R, I = P / V
            vt = max(v - i * self.r_int, 0.5 * v)
            i = power_w / vt
        self.current = i
        self.voltage = v - i * self.r_int
        self.used_c += i * dt


class QuadPhysics:
    def __init__(self, params, room=(10.0, 10.0, 4.0)):
        self.p = params
        self.room = room
        self.pos = np.zeros(3)          # NED, z = -height
        self.vel = np.zeros(3)
        self.q = np.array([1.0, 0.0, 0.0, 0.0])
        self.w = np.zeros(3)            # body rates p, q, r (rad/s)
        self.thrust = np.zeros(4)       # actual thrust per motor (N)
        self.cmd = np.zeros(4)
        self.on_ground = True
        self.events = []                # (time, kind, speed)
        self.t = 0.0
        self.bat = Battery(params.battery_mah, params.battery_cells, params.battery_r_int_ohm)
        I = np.array(params.inertia)
        self.I = I
        xy = np.array(params.motor_xy)
        spin = np.array(params.motor_spin, dtype=float)
        k = params.yaw_torque_per_thrust_m
        # torque = A_tau @ thrust ; rows: roll, pitch, yaw
        self.A_tau = np.vstack([-xy[:, 1], xy[:, 0], -spin * k])

    @property
    def height(self):
        return -self.pos[2]

    def t_max(self):
        """Available thrust per motor, scaled by battery voltage (ASSUMPTION: thrust ~ V^2)."""
        v_ref = 7.6
        return self.p.t_max_per_motor_n * min(1.1, (self.bat.voltage / v_ref) ** 2)

    def step(self, cmd, dt):
        p = self.p
        self.cmd = np.clip(cmd, 0.0, 1.0)
        tmax = self.t_max()
        target = self.cmd * tmax
        self.thrust += (target - self.thrust) * min(1.0, dt / p.motor_tau_s)
        R = qrot(self.q)
        v_body = R.T @ self.vel
        v_ax = max(0.0, -v_body[2])     # inflow along the thrust axis
        loss = max(0.0, 1.0 - v_ax / p.prop_pitch_speed_ms)
        T = self.thrust * loss
        # forces (world)
        f = R @ np.array([0.0, 0.0, -T.sum()]) + np.array([0.0, 0.0, p.mass_kg * G])
        speed = np.linalg.norm(self.vel)
        f -= 0.5 * RHO * p.drag_cda_m2 * speed * self.vel
        # torques (body)
        tau = self.A_tau @ T - p.angular_drag * self.w - np.cross(self.w, self.I * self.w)
        # integrate (semi-implicit Euler)
        acc = f / p.mass_kg
        self.vel += acc * dt
        self.w += tau / self.I * dt
        self.pos += self.vel * dt
        dq = qmul(self.q, np.array([0.0, *self.w])) * 0.5 * dt
        self.q = qnorm(self.q + dq)
        self._contacts()
        # battery: motor power ~ T^1.5 anchored at the hover efficiency (ESTIMATE)
        t_hover = p.mass_kg * G / 4
        p_hover_each = (t_hover / G * 1000) / p.hover_eff_g_per_w
        pw = float(np.sum(p_hover_each * (np.maximum(T, 0) / t_hover) ** 1.5)) + p.electronics_w
        self.bat.step(pw, dt)
        self.t += dt

    def _contacts(self):
        L, W, H = self.room
        # floor (z = 0) and ceiling (z = -H)
        if self.pos[2] >= 0.0:
            if self.vel[2] > 0.5:
                self.events.append((self.t, "floor_impact", float(self.vel[2])))
            self.pos[2] = 0.0
            if self.vel[2] > 0:
                self.vel[2] = 0.0
            self.vel[:2] *= 0.98         # ground friction
            thrust_up = self.thrust.sum() * qrot(self.q)[2, 2]
            self.on_ground = thrust_up < self.p.mass_kg * G * 1.02
            if self.on_ground:
                self.w *= 0.9
        else:
            self.on_ground = False
        if self.pos[2] < -H:
            self.events.append((self.t, "ceiling_impact", float(-self.vel[2])))
            self.pos[2] = -H
            self.vel[2] = max(self.vel[2], 0.0)
        for ax, half in ((0, L / 2), (1, W / 2)):
            if abs(self.pos[ax]) > half:
                self.events.append((self.t, "wall_impact", float(abs(self.vel[ax]))))
                self.pos[ax] = math.copysign(half, self.pos[ax])
                self.vel[ax] = 0.0

    def tof(self):
        """Distances (m) along body axes to the room surfaces; None beyond 4 m (VL53L1X/L5CX range)."""
        L, W, H = self.room
        R = qrot(self.q)
        out = {}
        for name, d in (("front", (1, 0, 0)), ("rear", (-1, 0, 0)), ("left", (0, -1, 0)),
                        ("right", (0, 1, 0)), ("down", (0, 0, 1))):
            dw = R @ np.array(d, dtype=float)
            best = math.inf
            planes = ((0, L / 2), (0, -L / 2), (1, W / 2), (1, -W / 2), (2, 0.0), (2, -H))
            for ax, val in planes:
                if abs(dw[ax]) < 1e-9:
                    continue
                s = (val - self.pos[ax]) / dw[ax]
                if s > 0:
                    best = min(best, s)
            out[name] = best if best <= 4.0 else None
        return out
