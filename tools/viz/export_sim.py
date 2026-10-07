#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Fly two scripted simulator flights and save pose tracks for the 3D viewer and renders.
Outputs docs/data/sim_flip.json and docs/data/sim_demo.json (simulation, estimated parameters)."""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "software" / "microscout_sdk" / "src"))
import microscout  # noqa: E402

OUT = REPO / "docs" / "data"
STATUS = "DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation output, not flight data)"
NOTE = "MicroScout SDK simulator, estimated parameters - not flight data"


def track(log, every):
    return [dict(t=round(s.t, 3), p=[round(v, 4) for v in s.position], q=[round(v, 5) for v in s.quaternion]) for s in log[::every]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = microscout.connect("sim")
    d.takeoff(1.5)
    d.hover(0.3)
    t0 = d.telemetry.t
    d.flip("back")
    d.hover(0.4)
    samples = track([s for s in d.log if s.t >= t0 - 0.25], 2)
    for s in samples:
        s["t"] = round(s["t"] - t0, 3)
    (OUT / "sim_flip.json").write_text(json.dumps(dict(status=STATUS, frame="NED", note=NOTE, samples=samples), separators=(",", ":")))

    d = microscout.connect("sim")
    script = "takeoff 1.2, move 1.2, turn 90, move 1.2, back flip, turn 90, move 1.2, right flip, goto home, land"
    d.takeoff(1.2); d.move(forward=1.2); d.turn(90); d.move(forward=1.2); d.flip("back")
    d.turn(90); d.move(forward=1.2); d.flip("right"); d.goto(0, 0, 1.2); d.land()
    (OUT / "sim_demo.json").write_text(json.dumps(dict(status=STATUS, frame="NED", note=NOTE, script=script, samples=track(d.log, 4)), separators=(",", ":")))
    print("wrote docs/data/sim_flip.json and sim_demo.json")


if __name__ == "__main__":
    main()
