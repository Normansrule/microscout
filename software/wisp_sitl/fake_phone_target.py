#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Written for Wisp Phase 0 (ArduCopter 4.7.2). Simulation only.
"""
fake_phone_target.py - emulate a phone "follow-me" target for ArduCopter SITL.

Sends GLOBAL_POSITION_INT (default) or FOLLOW_TARGET from its own MAVLink system
id, so a Copter with FOLL_ENABLE=1 and FOLL_SYSID=<that id> in FOLLOW mode (mode 23)
tracks it. Written against ArduCopter 4.7.2 (libraries/AP_Follow/AP_Follow.cpp).

Example (SITL started with sim_vehicle.py; SERIAL1 listens on tcp 5762):
    python3 fake_phone_target.py --connect tcp:127.0.0.1:5762 --sysid 101 \
        --pattern circle --speed 3 --radius 25
"""
import argparse
import math
import time

from pymavlink import mavutil

EARTH_R = 6378137.0


def offset_ll(lat_deg, lon_deg, dn_m, de_m):
    """Return lat/lon moved by (north, east) metres (flat-earth approximation)."""
    dlat = math.degrees(dn_m / EARTH_R)
    dlon = math.degrees(de_m / (EARTH_R * math.cos(math.radians(lat_deg))))
    return lat_deg + dlat, lon_deg + dlon


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="tcp:127.0.0.1:5762",
                    help="SITL SERIAL1 (tcp:127.0.0.1:5762) or udpin:127.0.0.1:14550 behind MAVProxy")
    ap.add_argument("--sysid", type=int, default=101, help="target sysid; must equal FOLL_SYSID")
    ap.add_argument("--msg", choices=["gpi", "follow_target"], default="gpi")
    ap.add_argument("--pattern", choices=["line", "circle"], default="circle")
    ap.add_argument("--speed", type=float, default=3.0, help="walking/jogging speed m/s")
    ap.add_argument("--radius", type=float, default=25.0, help="circle radius m")
    ap.add_argument("--heading", type=float, default=0.0, help="line heading deg (0=N)")
    ap.add_argument("--rate", type=float, default=5.0, help="send rate Hz (phone GPS is ~1-10 Hz)")
    ap.add_argument("--rel-alt", type=float, default=1.5, help="phone height above home, m")
    args = ap.parse_args()

    m = mavutil.mavlink_connection(args.connect, source_system=args.sysid,
                                   source_component=mavutil.mavlink.MAV_COMP_ID_ONBOARD_COMPUTER)
    print("waiting for vehicle heartbeat ...")
    m.wait_heartbeat()
    veh_sys = m.target_system
    print("vehicle sysid", veh_sys)

    # ask the vehicle for its home position so the target starts next to it
    m.mav.command_long_send(veh_sys, 1, mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0,
                            mavutil.mavlink.MAVLINK_MSG_ID_HOME_POSITION, 0, 0, 0, 0, 0, 0)
    home = m.recv_match(type="HOME_POSITION", blocking=True, timeout=10)
    if home is None:
        raise SystemExit("no HOME_POSITION (wait for GPS lock / EKF origin in SITL)")
    lat0, lon0 = home.latitude * 1e-7, home.longitude * 1e-7
    home_amsl_m = home.altitude * 1e-3
    print("home %.7f %.7f %.1f m AMSL" % (lat0, lon0, home_amsl_m))

    t0 = time.monotonic()
    period = 1.0 / args.rate
    next_hb = 0.0
    while True:
        t = time.monotonic() - t0
        if args.pattern == "circle":
            w = args.speed / args.radius            # rad/s
            ang = w * t
            dn, de = args.radius * math.cos(ang), args.radius * math.sin(ang)
            vn, ve = -args.speed * math.sin(ang), args.speed * math.cos(ang)
        else:
            h = math.radians(args.heading)
            dn, de = args.speed * t * math.cos(h), args.speed * t * math.sin(h)
            vn, ve = args.speed * math.cos(h), args.speed * math.sin(h)
        lat, lon = offset_ll(lat0, lon0, dn, de)
        hdg_deg = (math.degrees(math.atan2(ve, vn)) + 360.0) % 360.0
        now_ms = int(t * 1000)

        if t >= next_hb:
            m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GENERIC,
                                 mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            next_hb = t + 1.0

        if args.msg == "gpi":
            # AP_Follow uses relative_alt when FOLL_ALT_TYPE=1 (Copter default), alt when 0
            m.mav.global_position_int_send(
                now_ms,
                int(lat * 1e7), int(lon * 1e7),
                int((home_amsl_m + args.rel_alt) * 1000),   # alt, mm AMSL
                int(args.rel_alt * 1000),                   # relative_alt, mm
                int(vn * 100), int(ve * 100), 0,            # vx, vy, vz cm/s (NED)
                int(hdg_deg * 100))                         # hdg cdeg; 65535 = unknown
        else:
            # est_capabilities bit0 pos (required), bit1 vel, bit3 attitude+rates
            yaw = math.radians(hdg_deg)
            q = [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]
            yaw_rate = (args.speed / args.radius) if args.pattern == "circle" else 0.0
            m.mav.follow_target_send(
                now_ms, (1 << 0) | (1 << 1) | (1 << 3),
                int(lat * 1e7), int(lon * 1e7),
                home_amsl_m + args.rel_alt,                 # alt, m AMSL (always absolute)
                [vn, ve, 0.0], [0.0, 0.0, 0.0], q,
                [0.0, 0.0, yaw_rate], [0.0, 0.0, 0.0], 0)
        time.sleep(period)


if __name__ == "__main__":
    main()
