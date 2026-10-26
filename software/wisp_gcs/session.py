#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A scripted Control Lab session against a running bridge, as an app would drive it.

    python3 -m wisp_gcs.session --out session.json

Takes off to 10 m, then runs the same roll-rate step at three gain sets (ArduCopter's defaults, half and
double the P, I and D gains), tries a stop in the middle of a fourth step, restores the defaults and lands.
It scores every step from the PID_TUNING samples and writes a summary. Run the bridge with --record to keep
the full telemetry for replay.

STATUS: Phase 1 draft; ArduCopter 4.7.2 SITL (software in the loop) only.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time

from websockets.asyncio.client import connect

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from wisp_gcs.steptest import score     # noqa: E402

DEFAULTS = {"ATC_RAT_RLL_P": 0.135, "ATC_RAT_RLL_I": 0.135, "ATC_RAT_RLL_D": 0.0036}
GAIN_SETS = [("default", 1.0), ("half", 0.5), ("double", 2.0)]


class Client:
    def __init__(self, ws):
        self.ws = ws
        self.state = None
        self.pid = []
        self.results = []
        self.steps = []
        self.events = []
        self.pings = []

    async def pump(self):
        async for raw in self.ws:
            f = json.loads(raw)
            k = f["type"]
            if k == "state":
                self.state = f
            elif k == "pid":
                self.pid.extend(f["rows"])
            elif k == "result":
                self.results.append(f)
            elif k in ("step_start", "step_end"):
                self.steps.append(f)
            elif k == "event":
                self.events.append(f)
                print("  vehicle:", f.get("text"), flush=True)
            elif k == "pong":
                self.pings.append(time.time() * 1000 - f["t"])

    async def cmd(self, timeout=90, **c):
        n = len(self.results)
        await self.ws.send(json.dumps(c))
        t0 = time.time()
        while len(self.results) == n:
            if time.time() - t0 > timeout:
                raise TimeoutError(f"no result for {c}")
            await asyncio.sleep(0.05)
        r = self.results[n]
        print(f"  {c.get('cmd')}: {'ok' if r['ok'] else 'FAILED'} - {r['text']}", flush=True)
        return r

    async def ping(self):
        await self.ws.send(json.dumps({"cmd": "ping", "t": time.time() * 1000}))


async def run(url, out):
    async with connect(url) as ws:
        c = Client(ws)
        pump = asyncio.create_task(c.pump())
        for _ in range(5):
            await c.ping()
            await asyncio.sleep(0.2)
        print("waiting for a GPS (global positioning system) fix and EKF (extended Kalman filter) position",
              flush=True)
        t0 = time.time()
        while not (c.state and c.state["gps"] and c.state["gps"]["fix"] >= 3
                   and "pos_horiz_abs" in (c.state["ekf"] or {}).get("flags", [])):
            if time.time() - t0 > 120:
                raise TimeoutError("no GPS fix")
            await asyncio.sleep(0.5)
        r = await c.cmd(cmd="takeoff", alt=10)
        assert r["ok"], r
        await asyncio.sleep(3)
        await c.cmd(cmd="pid_axis", axis="roll")
        summary = {"vehicle": "ArduCopter 4.7.2 SITL, + quad model", "steps": []}
        for name, k in GAIN_SETS:
            for p, v in DEFAULTS.items():       # from the defaults each time: a 4x jump would be refused
                await c.cmd(cmd="set_param", name=p, value=v)
            for p, v in DEFAULTS.items():
                await c.cmd(cmd="set_param", name=p, value=round(v * k, 6))
            await asyncio.sleep(2)
            n0 = len(c.steps)
            r = await c.cmd(cmd="step", axis="roll", amp=90, dur=0.4)
            start = next(s for s in c.steps[n0:] if s["type"] == "step_start")
            rows = [row for row in c.pid if row[1] == "roll" and start["t_step"] - 0.5 <= row[0]
                    <= start["t_step"] + 3.0]
            sc = score([x[0] for x in rows], [x[2] for x in rows], [x[3] for x in rows],
                       start["t_step"], 90.0)
            print(f"  {name} gains: {sc}", flush=True)
            summary["steps"].append({"name": name, "scale": k, "gains": start["gains"], "score": sc,
                                     "t_step": start["t_step"], "samples": len(rows)})
            await asyncio.sleep(2)
        # stop in the middle of a step: the drone must brake and hold
        n = len(c.results)
        await ws.send(json.dumps({"cmd": "step", "axis": "roll", "amp": 90, "dur": 0.4}))
        await asyncio.sleep(0.7)
        t_stop = time.time()
        await ws.send(json.dumps({"cmd": "stop"}))
        while not any("aborted" in r["text"] for r in c.results[n:]) and time.time() - t_stop < 5:
            await asyncio.sleep(0.01)
        t_abort = time.time() - t_stop
        await asyncio.sleep(2.5)
        summary["stop_test"] = {"results": [r["text"] for r in c.results[n:]],
                                "abort_reply_s": round(t_abort, 3), "mode_after": c.state["mode"],
                                "roll_after_deg": c.state["att"]["roll"],
                                "speed_after_ms": round(sum(v * v for v in c.state["vel"].values()) ** 0.5, 2)}
        print("  after stop:", summary["stop_test"], flush=True)
        for p, v in DEFAULTS.items():
            await c.cmd(cmd="set_param", name=p, value=v)
        # the safety rule: a >4x jump while armed is refused
        r = await c.cmd(cmd="set_param", name="ATC_RAT_RLL_P", value=1.0)
        summary["refused_big_change"] = not r["ok"]
        r = await c.cmd(cmd="set_param", name="ARMING_CHECK", value=0)
        summary["refused_non_tuning_param"] = not r["ok"]
        for _ in range(5):
            await c.ping()
            await asyncio.sleep(0.2)
        await c.cmd(cmd="land")
        t0 = time.time()
        while c.state["armed"] and time.time() - t0 < 60:
            await asyncio.sleep(0.5)
        summary["landed_and_disarmed"] = not c.state["armed"]
        summary["app_rtt_ms"] = round(sorted(c.pings)[len(c.pings) // 2], 2) if c.pings else None
        summary["vehicle_rtt_ms"] = c.state["latency"]["vehicle_rtt_ms"]
        pump.cancel()
        pathlib.Path(out).write_text(json.dumps(summary, indent=1))
        print(json.dumps({k: v for k, v in summary.items() if k != "steps"}, indent=1))
        return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8765/ws")
    ap.add_argument("--out", default="session.json")
    a = ap.parse_args()
    asyncio.run(run(a.url, a.out))


if __name__ == "__main__":
    main()
