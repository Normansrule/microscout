# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Command line: `microscout demo`, `microscout flip back`, `microscout plot log.csv`."""
import argparse
import sys

from . import connect


def _summary(drone):
    tel = drone.telemetry
    log = drone.log
    print(f"  sim time {tel.t:.1f} s | battery {tel.battery_pct:.0f} % ({tel.battery_v:.2f} V) | "
          f"max speed {max(s.speed for s in log):.1f} m/s | max rate {max(max(abs(r) for r in s.rates_dps) for s in log):.0f} deg/s")
    if drone._sim.phys.events:
        print("  contacts:", drone._sim.phys.events[:3])


def demo(args):
    print("MicroScout simulator demo (estimated parameters - not real hardware)")
    with connect("sim", realtime=args.realtime) as d:
        steps = [("take off to 1.5 m", lambda: d.takeoff(1.5)),
                 ("fly a 1.5 m square", lambda: [d.move(forward=1.5), d.move(right=1.5), d.move(forward=-1.5), d.move(right=-1.5)]),
                 ("turn 180 degrees", lambda: d.turn(180)),
                 ("back flip", lambda: d.flip("back")),
                 ("side flip", lambda: d.flip("right")),
                 ("land", lambda: d.land())]
        for name, fn in steps:
            fn()
            print(f"  done: {name:22s} t={d.telemetry.t:5.1f} s  height={d.telemetry.height:.2f} m")
        _summary(d)
        if args.log:
            print("  log ->", d.save_log(args.log))
        if args.trajectory:
            print("  trajectory ->", d.save_trajectory(args.trajectory))
        if args.plot:
            from .plot import plot_log
            print("  plot ->", plot_log(d.log, args.plot))


def flip(args):
    with connect("sim") as d:
        d.takeoff(args.height)
        t0 = d.telemetry.t
        d.flip(args.direction)
        f = [s for s in d.log if s.t >= t0]
        print(f"{args.direction} flip: {f[-1].t - t0:.2f} s, height {min(s.height for s in f):.2f}-{max(s.height for s in f):.2f} m, "
              f"peak rate {max(max(abs(r) for r in s.rates_dps) for s in f):.0f} deg/s")
        d.land()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="microscout", description="MicroScout SDK tools (simulator until hardware exists)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("demo", help="scripted flight in the simulator")
    a.add_argument("--realtime", action="store_true", help="run at wall-clock speed")
    a.add_argument("--log", help="write telemetry CSV")
    a.add_argument("--trajectory", help="write pose JSON for the 3D viewer")
    a.add_argument("--plot", help="write a PNG plot (needs matplotlib)")
    a.set_defaults(fn=demo)
    b = sub.add_parser("flip", help="take off and flip")
    b.add_argument("direction", nargs="?", default="back", choices=["back", "front", "left", "right"])
    b.add_argument("--height", type=float, default=1.5)
    b.set_defaults(fn=flip)
    args = ap.parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
