#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wisp Phase 0: first simulated follow-me flight in ArduPilot SITL (software in the loop).

A simulated walker (standing in for the phone app) sends its GPS position over MAVLink as
GLOBAL_POSITION_INT, the way ArduPilot's own autotest `ModeFollow` does. ArduCopter in FOLLOW mode keeps
a fixed offset behind the walker. The script records both tracks and reports how far the drone sat from
where it should be.

Usage (ArduPilot built for SITL, see review/P0/sitl.md):
    python3 follow_demo.py --ardupilot ~/ardupilot --out out/

It starts the SITL binary itself, so no MAVProxy is needed. Simulation only: it says nothing about how a
real Wisp will fly.
"""
import argparse
import csv
import math
import pathlib
import subprocess
import sys
import time

from pymavlink import mavutil

HOME = (33.7085, -118.2937, 20.0, 62.0)   # a cliff-top trail spot in San Pedro (lat, lon, alt m, heading deg); simulation only
WALK_SPEED = 1.4      # m/s
HEADING = 62.0        # deg, direction of the walk
OFFSET_BEHIND = 4.0   # m
HEIGHT = 3.0          # m above the walker
WALK_TIME = 60.0      # s
GCS_SYSID = 255       # the walker's messages come from this system id (FOLL_SYSID)

EARTH_R = 6378137.0


def offset_ll(lat, lon, north, east):
    return (lat + math.degrees(north / EARTH_R),
            lon + math.degrees(east / (EARTH_R * math.cos(math.radians(lat)))))


def ne_between(lat0, lon0, lat1, lon1):
    return (math.radians(lat1 - lat0) * EARTH_R,
            math.radians(lon1 - lon0) * EARTH_R * math.cos(math.radians(lat0)))


def set_param(m, name, value, timeout=5.0):
    for _ in range(3):
        m.mav.param_set_send(m.target_system, m.target_component, name.encode(), float(value),
                             mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg and msg.param_id == name and abs(msg.param_value - float(value)) < 1e-4:
                return msg.param_value
    raise RuntimeError(f"could not set {name}")


def command(m, cmd, *params):
    p = list(params) + [0] * (7 - len(params))
    m.mav.command_long_send(m.target_system, m.target_component, cmd, 0, *p)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ardupilot", default=str(pathlib.Path.home() / "ardupilot"), help="ArduPilot source tree with build/sitl")
    ap.add_argument("--out", default="out", help="folder for the CSV log and the chart")
    ap.add_argument("--speedup", type=int, default=1)
    ap.add_argument("--instance", type=int, default=0, help="SITL instance: TCP port 5760 + 10 x instance")
    a = ap.parse_args()
    root = pathlib.Path(a.ardupilot).expanduser()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    binary = root / "build/sitl/bin/arducopter"
    defaults = root / "Tools/autotest/default_params/copter.parm"
    sitl = subprocess.Popen([str(binary), "--model", "+", "--speedup", str(a.speedup), "--defaults", str(defaults),
                             "--home", ",".join(str(v) for v in HOME), "-w", f"-I{a.instance}"],
                            cwd=out, stdout=open(out / "sitl.log", "w"), stderr=subprocess.STDOUT)
    try:
        time.sleep(3)
        m = mavutil.mavlink_connection(f"tcp:127.0.0.1:{5760 + 10 * a.instance}", source_system=GCS_SYSID)
        m.wait_heartbeat(timeout=30)
        print(f"connected to system {m.target_system}")
        # 10 Hz position from the drone
        command(m, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 100000)
        set_param(m, "FOLL_ENABLE", 1)
        time.sleep(1)
        for name, value in (("FOLL_SYSID", GCS_SYSID), ("FOLL_OFS_TYPE", 1), ("FOLL_OFS_X", -OFFSET_BEHIND),
                            ("FOLL_OFS_Y", 0), ("FOLL_OFS_Z", -HEIGHT), ("FOLL_ALT_TYPE", 1), ("FOLL_YAW_BEHAVE", 1)):
            print(f"{name} = {set_param(m, name, value)}")

        # wait for the EKF to use GPS (GUIDED needs a position), then switch to GUIDED, arm and take off at once
        # (an armed copter that does not take off disarms itself after a few seconds)
        t0 = time.time()
        while True:
            if time.time() - t0 > 180 or sitl.poll() is not None:
                raise RuntimeError("no GUIDED arm within 180 s (EKF or pre-arm checks)")
            m.set_mode("GUIDED")
            hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
            if not hb or hb.get_srcSystem() != m.target_system or hb.custom_mode != 4:
                time.sleep(1)
                continue
            command(m, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
            armed = False
            t_arm = time.time()
            while time.time() - t_arm < 3:
                hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
                if hb and hb.get_srcSystem() == m.target_system and hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                    armed = True
                    break
            if armed:
                command(m, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, HEIGHT)   # at once, before auto-disarm
                break
            time.sleep(2)
        print(f"armed in GUIDED and taking off after {time.time() - t0:.0f} s")
        t1 = time.time()
        while True:
            pos = m.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=5)
            if pos and pos.relative_alt / 1000 > HEIGHT * 0.9:
                break
            if time.time() - t1 > 60 or sitl.poll() is not None:
                raise RuntimeError("take-off did not reach the follow height")
        start = (pos.lat / 1e7, pos.lon / 1e7)
        print(f"at {pos.relative_alt / 1000:.1f} m, switching to FOLLOW")

        # the walker starts 4 m ahead of the drone and walks along HEADING
        h = math.radians(HEADING)
        w0 = offset_ll(*start, OFFSET_BEHIND * math.cos(h), OFFSET_BEHIND * math.sin(h))
        m.set_mode("FOLLOW")
        rows, t_start, last_send = [], time.time(), 0.0
        while (now := time.time() - t_start) < WALK_TIME:
            s = WALK_SPEED * now
            wl = offset_ll(*w0, s * math.cos(h), s * math.sin(h))
            if now - last_send >= 0.1:
                vn, ve = WALK_SPEED * math.cos(h), WALK_SPEED * math.sin(h)
                m.mav.global_position_int_send(int(now * 1000), int(wl[0] * 1e7), int(wl[1] * 1e7),
                                               int(HOME[2] * 1000), 0, int(vn * 100), int(ve * 100), 0, int(HEADING * 100))
                last_send = now
            msg = m.recv_match(type=["GLOBAL_POSITION_INT", "HEARTBEAT"], blocking=True, timeout=0.2)
            if sitl.poll() is not None:
                raise RuntimeError("SITL exited; see sitl.log")
            if msg and msg.get_type() == "GLOBAL_POSITION_INT" and msg.get_srcSystem() == m.target_system:
                dn, de = ne_between(*wl, msg.lat / 1e7, msg.lon / 1e7)
                behind = -(dn * math.cos(h) + de * math.sin(h))       # metres behind the walker along the heading
                side = -dn * math.sin(h) + de * math.cos(h)
                rows.append((round(now, 2), round(dn, 3), round(de, 3), round(behind, 3), round(side, 3),
                             round(msg.relative_alt / 1000, 3), round(math.hypot(msg.vx, msg.vy) / 100, 3)))
        m.set_mode("LAND")
        print("walk finished, landing")
    finally:
        time.sleep(1)
        sitl.terminate()

    with open(out / "follow_demo.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["t_s", "north_from_walker_m", "east_from_walker_m", "behind_m", "side_m", "height_m", "speed_ms"])
        wr.writerows(rows)
    tail = [r for r in rows if r[0] > 20]
    if not tail:
        sys.exit("no position data recorded")
    err = [math.hypot(r[3] - OFFSET_BEHIND, r[4]) for r in tail]
    summary = (f"after 20 s: mean {sum(r[3] for r in tail) / len(tail):.2f} m behind (want {OFFSET_BEHIND}), "
               f"side {max(abs(r[4]) for r in tail):.2f} m at most, height {sum(r[5] for r in tail) / len(tail):.2f} m "
               f"(want {HEIGHT}), speed {sum(r[6] for r in tail) / len(tail):.2f} m/s (walker {WALK_SPEED}); "
               f"position error mean {sum(err) / len(err):.2f} m, max {max(err):.2f} m")
    print(summary)
    (out / "summary.txt").write_text(summary + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
        t = [r[0] for r in rows]
        ax[0].plot(t, [r[3] for r in rows], label="behind the walker (m)")
        ax[0].plot(t, [r[4] for r in rows], label="to the side (m)")
        ax[0].axhline(OFFSET_BEHIND, ls="--", lw=0.8, color="grey")
        ax[0].legend(frameon=False)
        ax[1].plot(t, [r[5] for r in rows], label="height (m)")
        ax[1].plot(t, [r[6] for r in rows], label="ground speed (m/s)")
        ax[1].axhline(HEIGHT, ls="--", lw=0.8, color="grey")
        ax[1].set_xlabel("time in FOLLOW (s)")
        ax[1].legend(frameon=False)
        fig.suptitle("ArduCopter SITL, FOLLOW mode, simulated walker (simulation only)", fontsize=10)
        fig.tight_layout()
        fig.savefig(out / "follow_demo.png", dpi=130)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
