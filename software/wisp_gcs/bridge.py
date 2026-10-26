#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wisp ground bridge: MAVLink (Micro Air Vehicle Link) on one side, WebSocket JSON (JavaScript Object Notation)
for the apps on the other.

    python3 -m wisp_gcs.bridge --sitl ~/ardupilot          # start ArduCopter SITL and bridge it
    python3 -m wisp_gcs.bridge --connect tcp:127.0.0.1:5760 # bridge a vehicle that is already running

Then open http://127.0.0.1:8765/control-lab/ (the bridge serves the repo's docs/ folder too).

What it does:
  * reads telemetry and PID_TUNING (the live rate-loop terms), and sends the apps a state frame and a batch of
    PID samples every 20 ms, with the age of the newest attitude sample;
  * measures latency two ways: TIMESYNC round trips to the vehicle, and ping round trips to each app;
  * sends the vehicle a ground-station heartbeat once a second, so ArduPilot's ground-station-loss failsafe can
    work;
  * takes commands from the apps: arm and take off, land, stop and hover (Brake mode), change mode, read and set
    tuning parameters, and run a rate-loop step test;
  * can record every frame it sends to a JSON-lines file, which `replay.py` turns into a session the Control
    Lab plays back without a bridge.

Safety, because a web page can reach this port:
  * it listens on 127.0.0.1 only and accepts WebSocket connections only from the pages it serves, other
    localhost pages and the project's GitHub Pages site (Origin check; a sandboxed or file:// page, whose Origin
    is "null", is refused);
  * it writes only tuning parameters on an allowlist, each under an absolute ceiling; while armed it refuses a
    change of more than 4x either way in one step, and any change to a parameter that is 0 or unreadable;
  * "stop" counts as soon as it arrives: it cancels a take-off or step test even if that command has not started
    yet, and the reply says which mode the vehicle actually took (Brake, or Land if Brake was refused);
  * a step test starts only when armed in Guided mode above 3 m, aborts if anything else changes the mode, and
    ends by braking to a stop before holding position in Guided.

STATUS: Phase 1 draft. Run against ArduCopter 4.7.2 SITL only. Not for a real vehicle until Phase 3 review.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import mimetypes
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from http import HTTPStatus

from pymavlink import mavutil
from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.http11 import Response

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from wisp_gcs.steptest import StepPlan                                            # noqa: E402
from wisp_gcs.telemetry import AXIS_IDS, MODE_NUMBERS, Dejitter, VehicleState     # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
HOME = "33.7085,-118.2937,20,62"      # San Pedro cliff-top trail, same as the Phase 0 follow demo
TICK = 0.02                           # s between frames to the apps

# Telemetry streams to request (message id -> Hz)
STREAMS = {
    0: 5,          # HEARTBEAT (mode and arming changes show within 0.2 s)
    1: 2,          # SYS_STATUS
    24: 2,         # GPS_RAW_INT
    30: 50,        # ATTITUDE
    32: 10,        # LOCAL_POSITION_NED
    33: 10,        # GLOBAL_POSITION_INT
    193: 5,        # EKF_STATUS_REPORT
    194: 100,      # PID_TUNING (only sent for the axes in GCS_PID_MASK)
}

# Parameter names this app may write (ArduCopter 4.7.2 names), and the ceiling for each family.
PARAM_RULES = [
    (re.compile(r"ATC_RAT_(RLL|PIT|YAW)_(P|I|D|FF|D_FF)"), 1.0),
    (re.compile(r"ATC_RAT_(RLL|PIT|YAW)_IMAX"), 1.0),
    (re.compile(r"ATC_RAT_(RLL|PIT|YAW)_(FLTD|FLTT|FLTE|SMAX)"), 200.0),
    (re.compile(r"ATC_ANG_(RLL|PIT|YAW)_P"), 20.0),
    (re.compile(r"ATC_INPUT_TC"), 1.0),
    (re.compile(r"ATC_ACC_[RPY]_MAX"), 3000.0),
    (re.compile(r"PSC_(NE_POS|NE_VEL|D_POS|D_VEL|D_ACC)_(P|I|D|FF|IMAX)"), 20.0),
    (re.compile(r"GCS_PID_MASK"), 15.0),
]


def param_ceiling(name: str) -> float | None:
    """The largest value the app may write to `name`, or None if it may not write it at all."""
    for pat, ceiling in PARAM_RULES:
        if pat.fullmatch(name):
            return ceiling
    return None


ALLOWED_ORIGINS = [
    re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"),
    "https://normansrule.github.io",
    None,            # no Origin header: not a browser (tests, scripts); browsers always send one
]

TUNING_PARAMS = [
    "ATC_RAT_RLL_P", "ATC_RAT_RLL_I", "ATC_RAT_RLL_D", "ATC_RAT_RLL_FF", "ATC_RAT_RLL_FLTD",
    "ATC_RAT_PIT_P", "ATC_RAT_PIT_I", "ATC_RAT_PIT_D", "ATC_RAT_PIT_FF", "ATC_RAT_PIT_FLTD",
    "ATC_RAT_YAW_P", "ATC_RAT_YAW_I", "ATC_RAT_YAW_D", "ATC_RAT_YAW_FF", "ATC_RAT_YAW_FLTE",
    "ATC_ANG_RLL_P", "ATC_ANG_PIT_P", "ATC_ANG_YAW_P", "ATC_INPUT_TC",
    "ATC_ACC_R_MAX", "ATC_ACC_P_MAX", "ATC_ACC_Y_MAX", "GCS_PID_MASK",
]


class Stopped(Exception):
    """A stop arrived while a long command was running."""


class Link:
    """The MAVLink side. A reader thread folds messages into VehicleState; senders share one lock."""

    def __init__(self, url: str, on_event):
        self.url = url
        self.on_event = on_event            # called from the reader thread with a dict
        self.mav = None
        self.state = VehicleState()
        self.pid_buf: list = []
        self.pid_clock: dict[str, Dejitter] = {}     # one per axis
        self.lock = threading.Lock()                 # state, pid_buf
        self.send_lock = threading.Lock()
        self.ts_lock = threading.Lock()
        self.timesync_rtt_ms: float | None = None
        self._ts_pending: dict[int, float] = {}
        self._param_waiters: dict[str, threading.Event] = {}
        self._acks: dict[int, tuple[threading.Event, list]] = {}
        self.stop_gen = 0                   # counts stops; a command started at gen g is stopped once it moves
        self.running = True

    def connect(self, timeout=60.0):
        t0 = time.time()
        while True:
            try:
                self.mav = mavutil.mavlink_connection(self.url, source_system=255, source_component=190,
                                                      autoreconnect=True)
                break
            except OSError:
                if time.time() - t0 > timeout:
                    raise
                time.sleep(0.5)
        hb = self.mav.wait_heartbeat(timeout=timeout)
        if hb is None:
            raise TimeoutError("no heartbeat from the vehicle")
        for msg_id, hz in STREAMS.items():
            self.command_long(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, int(1e6 / hz))
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._pinger, daemon=True).start()

    def stopped(self, gen: int) -> bool:
        return self.stop_gen != gen

    # ---- sending -------------------------------------------------------------------------------------
    def command_long(self, cmd, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0):
        with self.send_lock:
            self.mav.mav.command_long_send(self.mav.target_system, self.mav.target_component, cmd, 0,
                                           p1, p2, p3, p4, p5, p6, p7)

    def command_ack(self, cmd, *params, timeout=1.5) -> int | None:
        """Send a COMMAND_LONG and wait for its COMMAND_ACK. Returns the MAV_RESULT, or None on no reply."""
        ev, box = threading.Event(), []
        self._acks[cmd] = (ev, box)
        self.command_long(cmd, *params)
        ev.wait(timeout)
        self._acks.pop(cmd, None)
        return box[0] if box else None

    def set_mode(self, name: str, timeout=1.5) -> bool:
        """Ask for a flight mode (MAV_CMD_DO_SET_MODE) and return whether the vehicle accepted it."""
        res = self.command_ack(mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                               mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, MODE_NUMBERS[name],
                               timeout=timeout)
        return res == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def set_param(self, name: str, value: float, timeout=2.0) -> float | None:
        ev = threading.Event()
        self._param_waiters[name] = ev
        with self.send_lock:
            self.mav.mav.param_set_send(self.mav.target_system, self.mav.target_component,
                                        name.encode(), float(value), mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        ev.wait(timeout)
        return self.state.params.get(name)

    def get_param(self, name: str, timeout=2.0) -> float | None:
        ev = threading.Event()
        self._param_waiters[name] = ev
        with self.send_lock:
            self.mav.mav.param_request_read_send(self.mav.target_system, self.mav.target_component,
                                                 name.encode(), -1)
        ev.wait(timeout)
        return self.state.params.get(name)

    def attitude_target(self, type_mask, q, rates, thrust):
        with self.send_lock:
            self.mav.mav.set_attitude_target_send(
                int(time.monotonic() * 1000) & 0xFFFFFFFF, self.mav.target_system,
                self.mav.target_component, type_mask, q, rates[0], rates[1], rates[2], thrust)

    # ---- receiving -----------------------------------------------------------------------------------
    def _reader(self):
        while self.running:
            try:
                m = self.mav.recv_match(blocking=True, timeout=0.5)
            except Exception as e:            # a dropped TCP link: autoreconnect retries
                self.on_event({"type": "event", "level": "warn", "text": f"link error: {e}"})
                time.sleep(0.5)
                continue
            if m is None or m.get_type() == "BAD_DATA":
                continue
            now = time.monotonic()
            d = m.to_dict()
            kind = d["mavpackettype"]
            if kind == "TIMESYNC":
                self._timesync(d, now)
                continue
            if kind == "COMMAND_ACK":
                waiter = self._acks.get(d["command"])
                if waiter:
                    waiter[1].append(d["result"])
                    waiter[0].set()
                continue
            with self.lock:
                sample = self.state.update(d, now)
                if sample is not None:
                    sample.t = self.pid_clock.setdefault(sample.axis, Dejitter())(now)
                    self.pid_buf.append(sample)
            if kind == "PARAM_VALUE":
                ev = self._param_waiters.pop(d["param_id"], None)
                if ev:
                    ev.set()
                self.on_event({"type": "param", "name": d["param_id"], "value": d["param_value"]})
            elif kind == "STATUSTEXT":
                self.on_event({"type": "event", "level": "vehicle", "severity": d["severity"],
                               "text": d["text"]})

    def _timesync(self, d, now):
        # Our requests carry tc1 = 0 and ts1 = our clock in ns; the vehicle echoes ts1 with tc1 filled in.
        if d["tc1"] == 0:
            return
        with self.ts_lock:
            sent = self._ts_pending.pop(d["ts1"], None)
            if sent is not None:
                rtt = (now - sent) * 1000.0
                prev = self.timesync_rtt_ms
                self.timesync_rtt_ms = rtt if prev is None else 0.8 * prev + 0.2 * rtt

    def _pinger(self):
        while self.running:
            try:
                ts = time.monotonic_ns()
                with self.ts_lock:
                    self._ts_pending[ts] = ts / 1e9
                    while len(self._ts_pending) > 20:
                        self._ts_pending.pop(next(iter(self._ts_pending)))
                with self.send_lock:
                    self.mav.mav.timesync_send(0, ts)
                    self.mav.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                                                mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            except Exception as e:             # keep pinging through a dropped link
                self.on_event({"type": "event", "level": "warn", "text": f"ping error: {e}"})
            time.sleep(1.0)

    def take_pid(self):
        with self.lock:
            buf, self.pid_buf = self.pid_buf, []
        return buf


class Bridge:
    def __init__(self, link: Link, record: pathlib.Path | None):
        self.link = link
        self.clients: set = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.record_f = open(record, "w") if record else None
        self.busy = threading.Lock()          # one long-running command (takeoff, step test) at a time
        self.t0 = time.monotonic()
        self.tasks: set = set()

    # frames to apps ----------------------------------------------------------------------------------
    def emit(self, frame: dict):
        """Thread-safe: queue a frame for every connected app (and the recording)."""
        if self.loop is None:
            return
        self.loop.call_soon_threadsafe(self._emit_now, frame)

    def _emit_now(self, frame: dict):
        frame.setdefault("tb", round(time.monotonic() - self.t0, 4))
        text = json.dumps(frame, separators=(",", ":"))
        if self.record_f and frame.get("type") != "pong":
            self.record_f.write(text + "\n")
        for ws in list(self.clients):
            if frame.get("to") not in (None, id(ws)):
                continue
            asyncio.ensure_future(self._send(ws, text))

    async def _send(self, ws, text):
        try:
            await ws.send(text)
        except Exception:
            self.clients.discard(ws)

    async def ticker(self):
        while True:
            await asyncio.sleep(TICK)
            now = time.monotonic()
            with self.link.lock:
                snap = self.link.state.snapshot(now)
            snap["t"] = round(snap["t"] - self.t0, 3) if snap["t"] else 0.0
            snap["latency"] = {"vehicle_rtt_ms": _r(self.link.timesync_rtt_ms, 2)}
            self._emit_now(snap)
            pid = self.link.take_pid()
            if pid:
                rows = []
                for s in pid:
                    s.t -= self.t0
                    rows.append(s.as_list())
                self._emit_now({"type": "pid", "cols": ["t", "axis", "des", "ach", "ff", "p", "i", "d"],
                                "rows": rows})

    # commands from apps --------------------------------------------------------------------------------
    async def handler(self, ws):
        self.clients.add(ws)
        hello = {"type": "hello", "bridge": "wisp_gcs 0.2", "vehicle": self.link.url,
                 "params": {k: v for k, v in self.link.state.params.items() if k in TUNING_PARAMS}}
        await ws.send(json.dumps(hello))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get("cmd") == "ping":
                    await ws.send(json.dumps({"type": "pong", "t": msg.get("t"),
                                              "tb": round(time.monotonic() - self.t0, 4)}))
                    continue
                if self.record_f and msg.get("cmd"):
                    self.record_f.write(json.dumps({"type": "cmd", "tb": round(time.monotonic() - self.t0, 4),
                                                    **msg}) + "\n")
                if msg.get("cmd") == "stop":
                    # Counts the moment it arrives: any command received before it is now stopped, even one
                    # whose worker thread has not started yet.
                    self.link.stop_gen += 1
                gen = self.link.stop_gen
                # Long commands (take-off, step test) run in worker threads so that a later stop is handled
                # while they are still going.
                task = asyncio.create_task(asyncio.to_thread(self.dispatch, msg, id(ws), gen))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)
        finally:
            self.clients.discard(ws)

    def reply(self, to, ok, text, **extra):
        self.emit({"type": "result", "to": to, "ok": ok, "text": text, **extra})

    def dispatch(self, msg: dict, to, gen: int):
        cmd = msg.get("cmd")
        L = self.link
        try:
            if cmd == "stop":
                self._stop(to)
            elif cmd == "mode":
                if msg.get("name") not in ("GUIDED", "LOITER", "BRAKE", "LAND", "RTL", "ALT_HOLD"):
                    return self.reply(to, False, f"mode {msg.get('name')!r} not allowed from the app")
                ok = L.set_mode(msg["name"])
                self.reply(to, ok, f"Mode {msg['name']} {'accepted' if ok else 'refused by the vehicle'}")
            elif cmd == "land":
                ok = L.set_mode("LAND")
                self.reply(to, ok, "Landing" if ok else "Land refused by the vehicle")
            elif cmd == "takeoff":
                self._long(to, gen, self._takeoff, float(msg.get("alt", 10.0)))
            elif cmd == "get_params":
                names = [n for n in msg.get("names", TUNING_PARAMS) if param_ceiling(str(n)) is not None]
                vals = {n: L.get_param(n) for n in names}
                self.emit({"type": "params", "to": to, "values": vals})
            elif cmd == "set_param":
                self._set_param(to, str(msg.get("name", "")), msg.get("value"))
            elif cmd == "pid_axis":
                axis = msg.get("axis", "roll")
                mask = 1 << (AXIS_IDS[axis] - 1)
                v = L.set_param("GCS_PID_MASK", mask)
                self.reply(to, v == mask, f"Streaming PID terms for {axis}")
            elif cmd == "step":
                plan = StepPlan(axis=msg.get("axis", "roll"), amp=float(msg.get("amp", 90.0)),
                                dur=float(msg.get("dur", 0.4)))
                self._long(to, gen, self._step, plan)
            else:
                self.reply(to, False, f"unknown command {cmd!r}")
        except Stopped:
            self.reply(to, False, f"{cmd} aborted by stop")
        except (ValueError, KeyError, TypeError) as e:
            self.reply(to, False, f"{cmd}: {e}")

    def _long(self, to, gen, fn, *args):
        if self.link.stopped(gen):
            raise Stopped
        if not self.busy.acquire(blocking=False):
            return self.reply(to, False, "busy with another command")
        try:
            fn(to, gen, *args)
        finally:
            self.busy.release()

    def _stop(self, to):
        L = self.link
        if L.set_mode("BRAKE"):
            return self.reply(to, True, "Stopping: Brake mode accepted, holding position")
        # Brake needs a position estimate; without one the safest thing left is to land.
        if L.set_mode("LAND"):
            return self.reply(to, False, "Brake refused by the vehicle; landing instead")
        self.reply(to, False, "Brake and Land both refused or unanswered: take manual control")

    def _set_param(self, to, name, value):
        L = self.link
        ceiling = param_ceiling(name)
        if ceiling is None:
            return self.reply(to, False, f"{name} is not a tuning parameter this app may change")
        try:
            value = float(value)
        except (TypeError, ValueError):
            return self.reply(to, False, "value must be a number")
        if not math.isfinite(value) or value < 0 or value > ceiling:
            return self.reply(to, False, f"{name}: {value:g} is outside 0-{ceiling:g}")
        if L.state.armed and name != "GCS_PID_MASK":
            cur = L.state.params.get(name)
            if cur is None:
                cur = L.get_param(name)
            if cur is None:
                return self.reply(to, False, f"{name}: could not read its current value; not changed in flight")
            if cur == 0 and value != 0:
                return self.reply(to, False, f"{name} is 0; set it while disarmed, not in flight")
            ratio = value / cur if cur else 1.0
            if not 0.25 / 1.0001 <= ratio <= 4.0 * 1.0001:
                return self.reply(to, False, f"{name}: change from {cur:g} to {value:g} is more than 4x; "
                                             "do it in smaller steps or while disarmed")
        got = L.set_param(name, value)
        ok = got is not None and abs(got - value) <= 1e-6 * max(1.0, abs(value))
        self.reply(to, ok, f"{name} = {got:g}" if got is not None else f"{name}: no reply", name=name,
                   value=got)

    def _wait(self, cond, timeout, gen):
        """Wait for cond(state); raise Stopped if a stop arrives."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            if self.link.stopped(gen):
                raise Stopped
            with self.link.lock:
                if cond(self.link.state):
                    return True
            time.sleep(0.05)
        return False

    def _takeoff(self, to, gen, alt):
        L = self.link
        if not 2.0 <= alt <= 30.0:
            return self.reply(to, False, "take-off height must be 2-30 m")
        if not L.state.armed:
            for _ in range(3):
                L.set_mode("GUIDED")
                if self._wait(lambda s: s.mode == "GUIDED", 3, gen):
                    break
            else:
                return self.reply(to, False, "vehicle did not enter Guided mode")
            for _ in range(20):            # pre-arm checks pass once the EKF has a position, ~20-40 s in SITL
                L.command_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
                if self._wait(lambda s: s.armed, 2, gen):
                    break
            else:
                return self.reply(to, False, "arming refused (pre-arm checks); see the vehicle messages")
        if L.stopped(gen):
            raise Stopped
        L.command_long(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, alt)
        ok = self._wait(lambda s: (s.alt_rel or 0) >= alt * 0.95, 30, gen)
        self.reply(to, ok, f"Hovering at {alt:g} m" if ok else "take-off did not reach height")

    def _step(self, to, gen, plan: StepPlan):
        L = self.link
        with L.lock:
            s = L.state
            if not (s.armed and s.mode == "GUIDED" and (s.alt_rel or 0) > 3.0):
                return self.reply(to, False, "step test needs the vehicle armed, in Guided, above 3 m")
            yaw = s.att["yaw"]
        mask = 1 << (AXIS_IDS[plan.axis] - 1)
        if L.state.params.get("GCS_PID_MASK") != mask:
            L.set_param("GCS_PID_MASK", mask)
        names = [f"ATC_RAT_{_AX[plan.axis]}_{k}" for k in ("P", "I", "D", "FF", "FLTD")]
        gains = {n: (L.state.params[n] if n in L.state.params else L.get_param(n)) for n in names}
        if L.stopped(gen):
            raise Stopped
        start = time.monotonic()
        self.emit({"type": "step_start", "axis": plan.axis, "amp": plan.amp, "dur": plan.dur,
                   "t_step": round(start + plan.lead - self.t0, 4), "gains": gains})
        phase_log = []
        last_phase = None
        while True:
            t = time.monotonic() - start
            if t >= plan.total:
                break
            if L.stopped(gen):
                raise Stopped                 # the stop itself has already asked for Brake
            mode = L.state.mode
            if mode != "GUIDED":
                return self.reply(to, False, f"step test stopped: the mode changed to {mode}; left as it is")
            c = plan.command(t, yaw)
            if c["phase"] != last_phase:
                phase_log.append([round(time.monotonic() - self.t0, 4), c["phase"]])
                last_phase = c["phase"]
            L.attitude_target(c["type_mask"], c["q"], c["rates"], c["thrust"])
            time.sleep(0.02)
        # The step leaves the drone drifting. Brake to a stop, then re-enter Guided, which holds position there.
        self.emit({"type": "step_end", "axis": plan.axis, "phases": phase_log,
                   "t_step": round(start + plan.lead - self.t0, 4)})
        if not L.set_mode("BRAKE"):
            return self.reply(to, False, "Step test finished, but Brake was refused: check the vehicle",
                              phases=phase_log)
        self._wait(lambda s: s.vel is not None and math.hypot(s.vel["n"], s.vel["e"]) < 0.3, 4, gen)
        held = L.set_mode("GUIDED")
        self.reply(to, True, "Step test finished; braked and holding position" if held
                   else "Step test finished; left in Brake (Guided refused)", phases=phase_log)


_AX = {"roll": "RLL", "pitch": "PIT", "yaw": "YAW"}


def _r(x, n):
    return None if x is None else round(x, n)


def static_files(connection, request):
    """Serve docs/ over plain HTTP so the Control Lab can be opened from the bridge itself."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    path = request.path.split("?")[0]
    if path == "/":
        path = "/index.html"
    if path.endswith("/"):
        path += "index.html"
    target = (DOCS / path.lstrip("/")).resolve()
    if DOCS.resolve() not in target.parents or not target.is_file():
        return connection.respond(HTTPStatus.NOT_FOUND, "Not found\n")
    body = target.read_bytes()
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    headers = Headers([("Content-Type", ctype), ("Content-Length", str(len(body))),
                       ("Cache-Control", "no-store")])
    return Response(200, "OK", headers, body)


def start_sitl(ardupilot: pathlib.Path, instance: int, speedup: int, log_dir: pathlib.Path):
    binary = ardupilot / "build/sitl/bin/arducopter"
    defaults = ardupilot / "Tools/autotest/default_params/copter.parm"
    if not binary.exists():
        sys.exit(f"{binary} not found: build SITL first (review/P0/sitl.md)")
    port = 5760 + 10 * instance
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            sys.exit(f"port {port} is busy: another SITL instance {instance} is running; stop it or use "
                     "--instance")
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(binary), "--model", "+", "--speedup", str(speedup), "--defaults", str(defaults),
           "--home", HOME, "-I", str(instance)]
    out = open(log_dir / f"sitl-{instance}.out", "w")
    proc = subprocess.Popen(cmd, cwd=log_dir, stdout=out, stderr=subprocess.STDOUT)
    return proc, f"tcp:127.0.0.1:{5760 + 10 * instance}"


async def amain(args):
    sitl = None
    url = args.connect
    if args.sitl:
        sitl, url = start_sitl(pathlib.Path(args.sitl).expanduser(), args.instance, 1,
                               pathlib.Path(args.workdir))
    bridge = None
    link = Link(url, lambda ev: bridge.emit(ev) if bridge else None)
    try:
        print(f"connecting to {url} ...", flush=True)
        await asyncio.to_thread(link.connect)
        bridge = Bridge(link, pathlib.Path(args.record) if args.record else None)
        bridge.loop = asyncio.get_running_loop()
        bridge.loop.add_signal_handler(signal.SIGTERM, asyncio.current_task().cancel)
        for n in TUNING_PARAMS:
            await asyncio.to_thread(link.get_param, n, 1.0)
        print(f"vehicle connected; Control Lab at http://127.0.0.1:{args.port}/control-lab/", flush=True)
        async with serve(bridge.handler, "127.0.0.1", args.port, origins=ALLOWED_ORIGINS,
                         process_request=static_files, max_size=2**16):
            await bridge.ticker()
    finally:
        link.running = False
        if bridge and bridge.record_f:
            bridge.record_f.close()
        if sitl:
            sitl.terminate()
            sitl.wait(5)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sitl", help="ArduPilot source tree with SITL built; starts arducopter")
    src.add_argument("--connect", help="MAVLink URL of a running vehicle, e.g. tcp:127.0.0.1:5760")
    ap.add_argument("--instance", type=int, default=4, help="SITL instance (TCP port 5760 + 10 x instance)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--record", help="write every frame to this JSON-lines file")
    ap.add_argument("--workdir", default=os.path.expanduser("~/.wisp/sitl"),
                    help="where SITL keeps its logs and eeprom")
    args = ap.parse_args(argv)
    try:
        asyncio.run(amain(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
