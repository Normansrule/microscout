# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Reference flight controller: the behaviour the MicroScout firmware is meant to
implement (milestone M7), written in Python so it can be flown in simulation today.

Cascade: position -> velocity -> attitude -> body rate -> mixer -> motors.
Pilot modes: beginner (velocity + obstacle stop), sport (angle + altitude hold),
acro (body rates, manual throttle). Onboard tasks: takeoff, land, goto, turn, flip.
Safety: arming checks, kill, altitude ceiling, geofence, low-battery auto-land,
external-control watchdog, battery current limit.

State estimation here reads the simulator's true state. The real firmware will
fuse IMU, optical flow, ToF and barometer instead - expect worse behaviour on
hardware until that estimator is tuned.
"""
import math

import numpy as np

from ..mathutil import qconj, qmul, qrot, to_euler, wrap_pi

G = 9.81


def rot_to_quat(R):
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return np.array([0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s])
    i = int(np.argmax([R[0, 0], R[1, 1], R[2, 2]]))
    if i == 0:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        return np.array([(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s])
    if i == 1:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        return np.array([(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s])
    s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
    return np.array([(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s])


class CommandRejected(Exception):
    pass


class FlightController:
    MODES = ("beginner", "sport", "acro")
    FLIPS = {"back": (1, +1), "front": (1, -1), "right": (0, +1), "left": (0, -1)}

    def __init__(self, phys, gains, safety):
        self.phys = phys
        self.p = phys.p
        self.g = gains
        self.s = safety
        A = np.vstack([np.ones(4), phys.A_tau])
        self.M = np.linalg.inv(A)
        self.armed = False
        self.mode = "beginner"
        self.task = None
        self.task_state = {}
        self.done_flag = False
        self.status = "disarmed"
        self.pos_sp = np.zeros(3)
        self.yaw_sp = 0.0
        self.sticks = None             # (roll, pitch, yaw, throttle); pitch +1 = stick forward
        self.sticks_t = -1.0
        self.ext = None                # external setpoint dict
        self.ext_t = -1.0
        self.ext_hold_t = None
        self.i_rate = np.zeros(3)
        self.i_vel = np.zeros(3)
        self.prev_w = np.zeros(3)
        self.ilim_scale = 1.0
        self.low_bat_t = 0.0
        self.warnings = []
        self.home = np.zeros(3)

    # ------------------------------------------------------------ commands
    def arm(self):
        ph = self.phys
        roll, pitch, _ = to_euler(ph.q)
        cell_v = ph.bat.voltage / self.p.battery_cells
        if max(abs(roll), abs(pitch)) > math.radians(25):
            raise CommandRejected("arming refused: not level")
        if cell_v < 3.5:
            raise CommandRejected("arming refused: battery low")
        if not ph.on_ground:
            raise CommandRejected("arming refused: not on the ground")
        self.armed = True
        self.status = "armed"
        self.home = ph.pos.copy()
        self.pos_sp = ph.pos.copy()
        self.yaw_sp = to_euler(ph.q)[2]
        self.i_rate[:] = 0
        self.i_vel[:] = 0

    def disarm(self):
        self.armed = False
        self.task = None
        self.status = "disarmed"

    def kill(self):
        self.disarm()
        self.status = "killed"

    def start(self, task, **kw):
        if not self.armed:
            raise CommandRejected(f"{task} refused: not armed")
        ph = self.phys
        if task == "flip":
            if ph.height < 1.0:
                raise CommandRejected("flip refused: climb above 1.0 m first")
            if kw.get("direction", "back") not in self.FLIPS:
                raise CommandRejected("flip direction must be back, front, left or right")
        if task in ("goto", "turn", "flip") and ph.on_ground:
            raise CommandRejected(f"{task} refused: take off first")
        self.task = task
        self.task_state = dict(kw, t0=ph.t, settle=0.0)
        self.done_flag = False
        self.ext = None
        self.ext_hold_t = None
        if task == "takeoff":
            self.pos_sp = np.array([ph.pos[0], ph.pos[1], -min(kw["height"], self.s.altitude_ceiling_m)])
        elif task == "goto":
            tgt = np.array(kw["target"], dtype=float)
            tgt[2] = -min(max(tgt[2], 0.3), self.s.altitude_ceiling_m)
            d = tgt[:2] - self.home[:2]
            r = np.linalg.norm(d)
            if r > self.s.geofence_radius_m:
                tgt[:2] = self.home[:2] + d / r * self.s.geofence_radius_m
                self.warnings.append("goto clipped to geofence")
            self.pos_sp = tgt
        elif task == "turn":
            self.yaw_sp = wrap_pi(self.yaw_sp + math.radians(kw["degrees"]))
        elif task == "flip":
            self.task_state.update(phase="climb", angle=0.0, h0=ph.height)

    def set_sticks(self, roll, pitch, yaw, throttle):
        """Radio-style input. roll +1 = right, pitch +1 = stick forward (nose down / fly forward),
        yaw +1 = clockwise, throttle 0..1."""
        if self.sticks is None:
            self.ext_hold_t = None
        self.sticks = (roll, pitch, yaw, throttle)
        self.sticks_t = self.phys.t

    def set_external(self, kind, values):
        if self.ext is None:
            self.pos_sp = self.phys.pos.copy()     # height to hold if thrust is None
        self.task = None
        self.ext = dict(kind=kind, values=np.array(values, dtype=float))
        self.ext_t = self.phys.t
        self.ext_hold_t = None

    # ------------------------------------------------------------ loops
    def _mix(self, F, tau):
        tmax = self.phys.t_max()
        t_tau = self.M[:, 1:] @ tau
        span = t_tau.max() - t_tau.min()
        if span > tmax:                      # not enough authority: keep roll/pitch, drop yaw first
            tau = np.array([tau[0], tau[1], 0.0])
            t_tau = self.M[:, 1:] @ tau
            span = t_tau.max() - t_tau.min()
            if span > tmax:
                t_tau *= tmax / span
        base = F / 4
        lo, hi = -t_tau.min(), tmax - t_tau.max()
        base = min(max(base, lo), hi)        # "air mode": keep torque, move collective
        T = base + t_tau
        return np.clip(T / tmax, 0.0, 1.0)

    def _rate_loop(self, w_sp, dt):
        w = self.phys.w
        e = w_sp - w
        self.i_rate = np.clip(self.i_rate + e * dt, -self.g.rate_i_limit, self.g.rate_i_limit)
        dw = (w - self.prev_w) / dt
        self.prev_w = w.copy()
        alpha = np.array(self.g.rate_kp) * e + np.array(self.g.rate_ki) * self.i_rate - np.array(self.g.rate_kd) * dw
        return np.array(self.p.inertia) * alpha

    def _att_to_rate(self, q_sp):
        qe = qmul(qconj(self.phys.q), q_sp)
        if qe[0] < 0:
            qe = -qe
        w_sp = 2 * np.array(self.g.att_kp) * qe[1:]
        lim = math.radians(self.g.max_rate_dps)
        return np.clip(w_sp, -lim, lim)

    def _accel_to_att(self, a_des, yaw_sp):
        """Desired world acceleration (NED) -> attitude setpoint and collective thrust (N)."""
        m = self.p.mass_kg
        max_h = G * math.tan(math.radians(self.g.max_tilt_deg))
        h = np.linalg.norm(a_des[:2])
        if h > max_h:
            a_des = a_des.copy()
            a_des[:2] *= max_h / h
        t_world = m * (a_des - np.array([0.0, 0.0, G]))
        zb = -t_world / max(np.linalg.norm(t_world), 1e-6)
        xc = np.array([math.cos(yaw_sp), math.sin(yaw_sp), 0.0])
        yb = np.cross(zb, xc)
        yb /= max(np.linalg.norm(yb), 1e-6)
        xb = np.cross(yb, zb)
        q_sp = rot_to_quat(np.column_stack([xb, yb, zb]))
        F = float(-t_world @ qrot(self.phys.q)[:, 2])
        return q_sp, max(F, 0.0)

    def _vel_loop(self, v_sp, dt):
        v = self.phys.vel
        e = v_sp - v
        self.i_vel = np.clip(self.i_vel + e * dt, -2.0, 2.0)
        return np.array(self.g.vel_kp) * e + np.array(self.g.vel_ki) * self.i_vel

    def _pos_to_vel(self, p_sp):
        v = np.array(self.g.pos_kp) * (p_sp - self.phys.pos)
        hs = np.linalg.norm(v[:2])
        vmax = self.task_state.get("speed", self.g.max_speed_ms) if self.task in ("goto", "takeoff") else self.g.max_speed_ms
        if hs > vmax:
            v[:2] *= vmax / hs
        v[2] = np.clip(v[2], -self.g.max_climb_ms, self.g.max_climb_ms)
        return v

    def _obstacle_filter(self, v_sp):
        if self.mode != "beginner":
            return v_sp
        tof = self.phys.tof()
        R = qrot(self.phys.q)
        for name, d in (("front", (1, 0, 0)), ("rear", (-1, 0, 0)), ("left", (0, -1, 0)), ("right", (0, 1, 0))):
            dist = tof.get(name)
            if dist is not None and dist < self.s.obstacle_stop_m:
                dw = R @ np.array(d, dtype=float)
                dw[2] = 0
                n = np.linalg.norm(dw)
                if n > 0:
                    dw /= n
                    toward = float(v_sp @ dw)
                    if toward > 0:
                        v_sp = v_sp - toward * dw
                        if "obstacle stop" not in self.warnings[-1:]:
                            self.warnings.append("obstacle stop")
        return v_sp

    # ------------------------------------------------------------ main step
    def step(self, dt):
        ph = self.phys
        if not self.armed:
            return np.zeros(4)
        self._safety(dt)
        if not self.armed:
            return np.zeros(4)
        roll, pitch, yaw = to_euler(ph.q)
        m = self.p.mass_kg
        cmd_rate = None
        F = None
        st = self.task_state

        if self.task == "flip":
            axis, sign = self.FLIPS[st.get("direction", "back")]
            if st["phase"] == "climb":
                v_sp = np.array([0.0, 0.0, -2.5])
                a = self._vel_loop(v_sp, dt)
                q_sp, F = self._accel_to_att(a, self.yaw_sp)
                cmd_rate = self._att_to_rate(q_sp)
                if ph.t - st["t0"] > 0.22:
                    st["phase"] = "rotate"
            elif st["phase"] == "rotate":
                cmd_rate = np.zeros(3)
                cmd_rate[axis] = sign * math.radians(self.g.max_rate_dps)
                F = 0.45 * m * G
                st["angle"] += abs(ph.w[axis]) * dt
                if st["angle"] > math.radians(320):
                    st["phase"] = "recover"
                    self.pos_sp = np.array([ph.pos[0], ph.pos[1], -max(st["h0"], ph.height)])
                    self.i_vel[:] = 0
            else:   # recover
                v_sp = self._pos_to_vel(self.pos_sp)
                v_sp[:2] = 0.0
                a = self._vel_loop(v_sp, dt)
                q_sp, F = self._accel_to_att(a, self.yaw_sp)
                cmd_rate = self._att_to_rate(q_sp)
                tilt = math.degrees(math.acos(max(-1, min(1, qrot(ph.q)[2, 2]))))
                if tilt < 8 and abs(ph.vel[2]) < 0.6:
                    self.pos_sp = ph.pos.copy()
                    self._finish("flip complete")
        elif self.ext is not None:
            k, vals = self.ext["kind"], self.ext["values"]
            if k == "rates":      # deg/s roll, pitch, yaw + thrust 0..1 of max total
                cmd_rate = np.radians(vals[:3])
                F = float(vals[3]) * 4 * ph.t_max()
            elif k == "attitude":  # deg roll, pitch, yaw-rate deg/s + thrust 0..1
                q_sp = _q_from_rp_yaw(math.radians(vals[0]), math.radians(vals[1]), yaw)
                cmd_rate = self._att_to_rate(q_sp)
                cmd_rate[2] = math.radians(vals[2])
                if math.isnan(vals[3]):          # thrust=None -> hold the current height
                    vz_sp = float(np.clip(self.g.pos_kp[2] * (self.pos_sp[2] - ph.pos[2]), -self.g.max_climb_ms, self.g.max_climb_ms))
                    az = float(self._vel_loop(np.array([ph.vel[0], ph.vel[1], vz_sp]), dt)[2])
                    F = m * (G - az) / max(qrot(ph.q)[2, 2], 0.3)
                else:
                    F = float(vals[3]) * 4 * ph.t_max()
            elif k == "velocity":  # m/s forward-world x, y, up + yaw rate deg/s
                v_sp = np.array([vals[0], vals[1], -vals[2]])
                v_sp = self._obstacle_filter(v_sp)
                self.yaw_sp = wrap_pi(self.yaw_sp + math.radians(vals[3]) * dt)
                a = self._vel_loop(v_sp, dt)
                q_sp, F = self._accel_to_att(a, self.yaw_sp)
                cmd_rate = self._att_to_rate(q_sp)
                self.pos_sp = ph.pos.copy()
            elif k == "position":
                self.pos_sp = np.array([vals[0], vals[1], -vals[2]])
        elif self.sticks is not None and self.task is None:
            r, pch, yw, thr = self.sticks
            if self.mode == "acro":                      # stick forward = nose-down rate
                cmd_rate = np.radians(np.array([r, -pch, yw]) * self.g.max_rate_dps)
                F = thr * 4 * ph.t_max()
            elif self.mode == "sport":
                tilt = math.radians(self.g.max_tilt_deg)
                self.yaw_sp = wrap_pi(self.yaw_sp + yw * math.radians(180) * dt)
                q_sp = _q_from_rp_yaw(r * tilt, -pch * tilt, self.yaw_sp)   # stick forward = nose down
                vz = -(thr - 0.5) * 2 * self.g.max_climb_ms
                az = float(self._vel_loop(np.array([ph.vel[0], ph.vel[1], vz]), dt)[2])
                F = m * (G - az) / max(qrot(ph.q)[2, 2], 0.3)
                cmd_rate = self._att_to_rate(q_sp)
                self.pos_sp = ph.pos.copy()
            else:   # beginner: sticks are velocities in the heading frame
                c, s_ = math.cos(yaw), math.sin(yaw)
                fwd, rgt = pch * self.g.max_speed_ms, r * self.g.max_speed_ms
                v_sp = np.array([c * fwd - s_ * rgt, s_ * fwd + c * rgt, -(thr - 0.5) * 2 * self.g.max_climb_ms])
                v_sp = self._obstacle_filter(v_sp)
                self.yaw_sp = wrap_pi(self.yaw_sp + yw * math.radians(90) * dt)
                a = self._vel_loop(v_sp, dt)
                q_sp, F = self._accel_to_att(a, self.yaw_sp)
                cmd_rate = self._att_to_rate(q_sp)
                self.pos_sp = ph.pos.copy()

        if cmd_rate is None:   # position hold (default) and task targets
            if self.task == "land":
                v_sp = np.array([0.0, 0.0, 0.5 if ph.height > 0.3 else 0.25])
                v_sp[:2] = self.pos_sp[:2] - ph.pos[:2]
            else:
                v_sp = self._pos_to_vel(self.pos_sp)
                if self.task in ("goto",):
                    v_sp = self._obstacle_filter(v_sp)
            a = self._vel_loop(v_sp, dt)
            q_sp, F = self._accel_to_att(a, self.yaw_sp)
            cmd_rate = self._att_to_rate(q_sp)
            self._check_task_done(dt)

        tau = self._rate_loop(cmd_rate, dt)
        F = F * self.ilim_scale
        u = self._mix(F, tau)
        if self.task == "land" and ph.on_ground and ph.t - st.get("t0", 0) > 0.3 and abs(ph.vel[2]) < 0.1:
            self._finish("landed")
            self.disarm()
            return np.zeros(4)
        return u

    def _check_task_done(self, dt):
        ph = self.phys
        st = self.task_state
        if self.task in ("takeoff", "goto"):
            err = np.linalg.norm(self.pos_sp - ph.pos)
            ok = err < (0.06 if self.task == "takeoff" else 0.08) and np.linalg.norm(ph.vel) < 0.15
            st["settle"] = st["settle"] + dt if ok else 0.0
            if st["settle"] > 0.3:
                self._finish(f"{self.task} complete")
        elif self.task == "turn":
            ok = abs(wrap_pi(to_euler(ph.q)[2] - self.yaw_sp)) < math.radians(3) and abs(ph.w[2]) < 0.2
            st["settle"] = st["settle"] + dt if ok else 0.0
            if st["settle"] > 0.3:
                self._finish("turn complete")

    def _finish(self, msg):
        self.task = None
        self.done_flag = True
        self.status = msg

    def _safety(self, dt):
        ph = self.phys
        s = self.s
        # battery current limit (DR-06)
        if ph.bat.current > s.battery_current_limit_a:
            self.ilim_scale = max(0.5, self.ilim_scale - 0.002)
        else:
            self.ilim_scale = min(1.0, self.ilim_scale + 0.001)
        # altitude ceiling
        if ph.height > s.altitude_ceiling_m + 0.3 and self.task != "flip" and self.mode != "acro":
            self.pos_sp[2] = -s.altitude_ceiling_m
            self.ext = None
            if "altitude ceiling" not in self.warnings[-1:]:
                self.warnings.append("altitude ceiling")
        # low battery -> auto-land
        cell = ph.bat.voltage / self.p.battery_cells
        self.low_bat_t = self.low_bat_t + dt if cell < s.low_battery_cell_v else 0.0
        if self.low_bat_t > 2.0 and self.task != "land":
            self.warnings.append("low battery: auto-land")
            self.task = "land"
            self.task_state = dict(t0=ph.t, settle=0.0)
            self.ext = None
        # radio-stick watchdog (R-17): stale sticks -> hover, then land after 3 s
        if self.sticks is not None and ph.t - self.sticks_t > s.link_timeout_s:
            self.warnings.append("radio link lost: hover")
            self.sticks = None
            self.pos_sp = ph.pos.copy()
            self.ext_hold_t = ph.t
        # external-control watchdog: hover, then land after 3 s
        if self.ext is not None and ph.t - self.ext_t > s.link_timeout_s:
            self.warnings.append("link lost: hover")
            self.ext = None
            self.pos_sp = ph.pos.copy()
            self.ext_hold_t = ph.t
        if self.ext_hold_t is not None and self.task is None and self.ext is None and ph.t - self.ext_hold_t > 3.0:
            self.warnings.append("link lost: landing")
            self.pos_sp[2] = ph.pos[2]
            self.ext_hold_t = None
            self.task = "land"
            self.task_state = dict(t0=ph.t, settle=0.0)


def _q_from_rp_yaw(roll, pitch, yaw):
    from ..mathutil import from_euler
    return from_euler(roll, pitch, yaw)
