#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Turn a bridge recording (JSON lines) into the compact session file the Control Lab replays.

    python3 -m wisp_gcs.replay rec.jsonl session.json --out docs/control-lab/data/sitl-roll-steps.json

For each roll-rate step it keeps the PID_TUNING samples from 0.3 s before to 1.4 s after the step, the vehicle
state frames over the same window, the gains, and the scores. It fits the rate-loop plant on the steps named in
--fit-on (by default the first two) and records how well that plant predicts every step, including the ones it
was not fitted on, and the loop's stability margins at each step's gains.

STATUS: Phase 1 draft. The data are from ArduCopter 4.7.2 SITL (software in the loop), not a real drone.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import pathlib
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from wisp_gcs.fit import fit, margins, score_prediction      # noqa: E402
from wisp_gcs.steptest import score                           # noqa: E402

PRE, POST = 0.3, 1.4


def load(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        return [json.loads(line) for line in f]


def build(frames, summary, fit_on=None):
    pid = [r for f in frames if f["type"] == "pid" for r in f["rows"]]
    states = [f for f in frames if f["type"] == "state"]
    starts = [f for f in frames if f["type"] == "step_start"]
    ends = {round(f["t_step"], 4) for f in frames if f["type"] == "step_end"}
    names = [s["name"] for s in summary["steps"]]
    starts = [s for s in starts if round(s["t_step"], 4) in ends][:len(names)]   # completed steps only
    segs, out_steps = [], []
    for name, s in zip(names, starts):
        ts = s["t_step"]
        rows = [r for r in pid if r[1] == s["axis"] and ts - PRE <= r[0] <= ts + POST]
        t = np.array([r[0] - ts for r in rows])
        cols = np.array([r[2:] for r in rows])
        ax = {"roll": "RLL", "pitch": "PIT", "yaw": "YAW"}[s["axis"]]
        g = {k: s["gains"][f"ATC_RAT_{ax}_{k}"] for k in ("P", "I", "D", "FF", "FLTD")}
        seg = {"t": t, "des": np.radians(cols[:, 0]), "w": np.radians(cols[:, 1]), "i0": float(cols[0, 4]),
               "gains": g, "name": name}
        segs.append(seg)
        st = [{"t": round(f["tb"] - ts, 3), "roll": f["att"]["roll"], "pitch": f["att"]["pitch"],
               "alt": f["alt_rel"], "mode": f["mode"], "ekf": f["ekf"],
               "vehicle_rtt_ms": f["latency"]["vehicle_rtt_ms"]}
              for f in states if ts - PRE <= f["tb"] <= ts + POST]
        sc = score(list(t), list(cols[:, 0]), list(cols[:, 1]), 0.0, s["amp"])
        # Oscillation measure: RMS of the sample-to-sample change in the measured rate after the rise, at
        # 100 samples a second. A smooth response keeps it small; a ~20 Hz oscillation makes it large.
        after = cols[t >= 0.15, 1]
        if sc is not None and len(after) > 2:
            sc["jitter_dps"] = round(float(np.sqrt(np.mean(np.diff(after) ** 2))), 2)
        out_steps.append({
            "name": name, "axis": s["axis"], "amp_dps": s["amp"], "dur_s": s["dur"],
            "gains": {k: round(v, 6) for k, v in g.items()}, "score": sc,
            "cols": ["t", "des", "ach", "ff", "p", "i", "d"],
            "rows": [[round(float(a), 4)] + [round(float(x), 5) for x in r] for a, r in zip(t, cols)],
            "state": st,
        })
    fit_on = fit_on or names[:2]
    plant = fit([sg for sg in segs if sg["name"] in fit_on])
    for sg, o in zip(segs, out_steps):
        pred, _ = score_prediction(sg, plant)
        diverges = not (math.isfinite(pred["rms_dps"]) and pred["rms_dps"] < 1e3)
        o["prediction"] = {"rms_dps": None if diverges else round(pred["rms_dps"], 3),
                           "r2": None if diverges else round(pred["r2"], 4), "diverges": diverges}
        o["prediction"]["fitted_on_this_step"] = sg["name"] in fit_on
        m = margins(sg["gains"], plant)
        o["margins"] = {k: (None if v is None else round(v, 2)) for k, v in m.items()}
    # Out-of-sample check: fit on the first step alone and predict the rest.
    hold = fit([segs[0]])
    holdout = {"plant": {k: round(v, 5) for k, v in hold.items()}, "fitted_on": [segs[0]["name"]], "steps": {}}
    for sg in segs:
        pred, _ = score_prediction(sg, hold)
        div = not (math.isfinite(pred["rms_dps"]) and pred["rms_dps"] < 1e3)
        holdout["steps"][sg["name"]] = {"rms_dps": None if div else round(pred["rms_dps"], 3), "diverges": div,
                                        "margins": {k: (None if v is None else round(v, 2))
                                                    for k, v in margins(sg["gains"], hold).items()}}
    return {
        "about": "Roll-rate step tests in ArduCopter 4.7.2 SITL (software in the loop), + quad model, recorded "
                 "through the Wisp bridge. Simulation only: a real Wisp has different dynamics.",
        "vehicle": summary.get("vehicle"),
        "plant": {**{k: round(v, 5) for k, v in plant.items()}, "fitted_on": fit_on},
        "steps": out_steps,
        "holdout": holdout,
        "stop_test": summary.get("stop_test"),
        "latency": {"vehicle_rtt_ms": summary.get("vehicle_rtt_ms"), "app_rtt_ms": summary.get("app_rtt_ms")},
        "safety": {k: summary.get(k) for k in ("refused_big_change", "refused_non_tuning_param",
                                               "landed_and_disarmed")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recording")
    ap.add_argument("summary")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fit-on", nargs="*")
    a = ap.parse_args()
    data = build(load(a.recording), json.loads(pathlib.Path(a.summary).read_text()), a.fit_on)
    pathlib.Path(a.out).write_text(json.dumps(data, separators=(",", ":")))
    print(json.dumps({"plant": data["plant"],
                      "steps": [{k: s[k] for k in ("name", "score", "prediction", "margins")}
                                for s in data["steps"]]}, indent=1))


if __name__ == "__main__":
    main()
