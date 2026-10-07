# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""The `Drone` object: one API for beginners and for control-theory work.

High level (blocking, beginner friendly):
    takeoff(), move(), goto(), turn(), flip(), hover(), land()
Pilot style:
    set_mode("beginner" | "sport" | "acro"), sticks(...)
Low level (for PID / LQR / MPC experiments):
    rates(), attitude(), velocity(), control_loop(your_function)
Data:
    telemetry, log, save_log(), save_trajectory()
"""
import math
import time

from .sim import CommandRejected, Simulator
from .telemetry import save_csv, save_trajectory_json


class CommandFailed(RuntimeError):
    pass


class SimLink:
    """Runs the simulator in this process. realtime=True paces it to the wall clock."""

    def __init__(self, config=None, realtime=False):
        self.sim = Simulator(config)
        self.realtime = realtime

    def advance(self, seconds):
        if not self.realtime:
            self.sim.run_for(seconds)
            return
        t0 = time.monotonic()
        s0 = self.sim.t
        while self.sim.t - s0 < seconds:
            self.sim.step(10)
            lag = (self.sim.t - s0) - (time.monotonic() - t0)
            if lag > 0:
                time.sleep(lag)

    def until(self, pred, timeout):
        if not self.realtime:
            return self.sim.run_until(pred, timeout)
        t_end = self.sim.t + timeout
        while self.sim.t < t_end:
            self.advance(0.01)
            if pred():
                return True
        return False


class UdpLink:
    """Wi-Fi link to real hardware. The firmware side arrives at milestone M7;
    the draft message format is in docs/protocol.md."""

    def __init__(self, host, port=2390):
        raise CommandFailed(
            f"udp://{host}:{port}: no MicroScout hardware or firmware exists yet (Gate G1). "
            "Use microscout.connect('sim') - the same code will run on the real drone once M7 lands.")


def connect(uri="sim", realtime=False, config=None):
    """Connect to a drone. uri: 'sim' (simulator) or 'udp://<ip>' (real drone, from M7)."""
    if uri == "sim":
        return Drone(SimLink(config, realtime))
    if uri.startswith("udp://"):
        host = uri[6:].split(":")[0]
        return Drone(UdpLink(host))
    raise ValueError("uri must be 'sim' or 'udp://<ip>'")


class Drone:
    def __init__(self, link):
        self.link = link
        self._fc = link.sim.fc
        self._sim = link.sim

    # ------------------------------------------------------------ context manager
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self._fc.armed and not self._sim.phys.on_ground:
            try:
                self.land()
            except CommandFailed:
                self.emergency_stop()
        return False

    # ------------------------------------------------------------ data
    @property
    def telemetry(self):
        return self._sim.telemetry()

    @property
    def log(self):
        return self._sim.log

    @property
    def config(self):
        """Simulator configuration: .params (vehicle), .gains (controller), .safety (limits)."""
        return self._sim.cfg

    def save_log(self, path):
        save_csv(self.log, path)
        return path

    def save_trajectory(self, path, every=2):
        save_trajectory_json(self.log, path, every)
        return path

    # ------------------------------------------------------------ basics
    def arm(self):
        try:
            self._fc.arm()
        except CommandRejected as e:
            raise CommandFailed(str(e)) from None
        return self.telemetry

    def disarm(self):
        self._fc.disarm()
        return self.telemetry

    def emergency_stop(self):
        """Motors off immediately (the kill switch). The drone falls."""
        self._fc.kill()
        return self.telemetry

    def set_mode(self, mode):
        if mode not in self._fc.MODES:
            raise ValueError(f"mode must be one of {self._fc.MODES}")
        self._fc.mode = mode
        return mode

    # ------------------------------------------------------------ high-level actions
    def _run_task(self, task, timeout, **kw):
        try:
            self._fc.start(task, **kw)
        except CommandRejected as e:
            raise CommandFailed(str(e)) from None
        ok = self.link.until(lambda: self._fc.done_flag or not self._fc.armed and task != "land", timeout)
        if task == "land":
            ok = self.link.until(lambda: not self._fc.armed, timeout) or not self._fc.armed
        if not ok:
            raise CommandFailed(f"{task} did not finish within {timeout} s (status: {self._fc.status})")
        return self.telemetry

    def takeoff(self, height=1.0, timeout=10.0):
        """Arm if needed and climb to `height` metres, then hold position."""
        if not self._fc.armed:
            self.arm()
        return self._run_task("takeoff", timeout, height=height)

    def land(self, timeout=20.0):
        """Descend, touch down and disarm."""
        self._fc.ext = None
        return self._run_task("land", timeout)

    def wait(self, seconds=1.0):
        """Let time pass without sending anything new (the drone keeps its last command;
        if that was a low-level setpoint, the onboard watchdog takes over)."""
        self.link.advance(seconds)
        return self.telemetry

    def hover(self, seconds=1.0):
        """Hold the current position for `seconds`."""
        self._fc.ext = None
        self._fc.sticks = None
        self.link.advance(seconds)
        return self.telemetry

    def goto(self, x, y, height, speed=1.0, timeout=20.0):
        """Fly to (x, y) metres in the take-off frame (x forward, y right) at `height` metres."""
        return self._run_task("goto", timeout, target=(x, y, height), speed=speed)

    def move(self, forward=0.0, right=0.0, up=0.0, speed=1.0, timeout=20.0):
        """Move relative to where the drone is pointing."""
        tel = self.telemetry
        yaw = math.radians(tel.yaw)
        x = tel.position[0] + forward * math.cos(yaw) - right * math.sin(yaw)
        y = tel.position[1] + forward * math.sin(yaw) + right * math.cos(yaw)
        return self.goto(x, y, tel.height + up, speed, timeout)

    def turn(self, degrees, timeout=10.0):
        """Rotate in place; positive = clockwise seen from above."""
        return self._run_task("turn", timeout, degrees=degrees)

    def flip(self, direction="back", timeout=5.0):
        """Flip 360 degrees: 'back', 'front', 'left' or 'right'. Needs at least 1 m of height."""
        return self._run_task("flip", timeout, direction=direction)

    # ------------------------------------------------------------ pilot-style input
    def sticks(self, roll=0.0, pitch=0.0, yaw=0.0, throttle=0.5, seconds=0.5):
        """Hold radio-stick positions for `seconds`. roll/pitch/yaw in -1..1, throttle 0..1.
        pitch +1 = stick forward (fly forward / nose down), roll +1 = right, yaw +1 = clockwise.
        Beginner: sticks are speeds; sport: angles; acro: rotation rates."""
        self._fc.task = None
        self._fc.ext = None
        for _ in range(max(1, int(seconds * 50))):      # a radio sends ~50 frames/s
            self._fc.set_sticks(roll, pitch, yaw, throttle)
            self.link.advance(0.02)
        self._fc.sticks = None                         # sticks released: hold position
        self._fc.pos_sp = self._sim.phys.pos.copy()
        return self.telemetry

    # ------------------------------------------------------------ low-level setpoints
    def _hold_ext(self, kind, values, seconds):
        steps = max(1, int(seconds * 100))
        for _ in range(steps):
            self._fc.set_external(kind, values)
            self.link.advance(0.01)
        return self.telemetry

    def rates(self, roll_dps, pitch_dps, yaw_dps, thrust, seconds=0.1):
        """Body-rate setpoint (deg/s) + collective thrust 0..1 of maximum."""
        return self._hold_ext("rates", (roll_dps, pitch_dps, yaw_dps, thrust), seconds)

    def attitude(self, roll_deg, pitch_deg, yaw_rate_dps, thrust=None, seconds=0.1):
        """Attitude setpoint (deg) + yaw rate (deg/s) + collective thrust 0..1.
        thrust=None lets the drone hold its height for you."""
        return self._hold_ext("attitude", (roll_deg, pitch_deg, yaw_rate_dps, float("nan") if thrust is None else thrust), seconds)

    def velocity(self, vx, vy, vup, yaw_rate_dps=0.0, seconds=0.1):
        """Velocity setpoint in the take-off frame: vx forward, vy right, vup up (m/s)."""
        return self._hold_ext("velocity", (vx, vy, vup, yaw_rate_dps), seconds)

    def control_loop(self, controller, rate_hz=100, seconds=5.0):
        """Run your own controller. `controller(telemetry)` returns one of
        {'rates': (p, q, r, thrust)}, {'attitude': (roll, pitch, yaw_rate, thrust or None)},
        {'velocity': (vx, vy, vup, yaw_rate)} - or None to stop early.
        If it stops answering, the onboard watchdog hovers and then lands."""
        dt = 1.0 / rate_hz
        for _ in range(int(seconds * rate_hz)):
            out = controller(self.telemetry)
            if out is None:
                break
            (kind, values), = out.items()
            if kind == "attitude" and len(values) == 4 and values[3] is None:
                values = (*values[:3], float("nan"))
            self._fc.set_external(kind, values)
            self.link.advance(dt)
        self._fc.ext = None
        self._fc.pos_sp = self._sim.phys.pos.copy()
        return self.telemetry
