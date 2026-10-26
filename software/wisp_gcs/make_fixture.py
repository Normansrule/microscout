#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Write docs/control-lab/test/fixture.json: Python model outputs the JavaScript port must reproduce."""
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from wisp_gcs.fit import closed_loop, margins    # noqa: E402
from wisp_gcs.steptest import score               # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
data = json.loads((ROOT / "docs/control-lab/data/sitl-roll-steps.json").read_text())
sitl = {k: data["plant"][k] for k in ("b", "a", "tau", "td", "gyro_hz")}
wisp = {"b": 700, "a": 0, "tau": 0.03, "td": 0.0025, "gyro_hz": 40}
t = [round(-0.3 + k * 0.005, 6) for k in range(int(1.7 / 0.005) + 1)]
des = [math.radians(min(90.0, 1100 * max(0.0, x))) if x < 0.4 else
       math.radians(max(0.0, 90.0 - 1100 * (x - 0.4))) for x in t]
cases = []
for pname, plant in (("sitl", sitl), ("wisp", wisp), ("sitl_sat", {**sitl, "u_sat": 0.3})):
    for k in (0.5, 1.0, 2.0):
        g = {"P": 0.135 * k, "I": 0.135 * k, "D": 0.0036 * k, "FF": 0.0, "FLTD": 20.0, "IMAX": 0.5}
        tt, wf, u = closed_loop(np.array(t), np.array(des), g, plant, w0=0.01, i0=0.002)
        idx = list(range(0, len(tt), 20))
        m = margins(g, plant)
        cases.append({"plant": plant, "gains": g, "w0": 0.01, "i0": 0.002,
                      "idx": idx, "wf": [float(wf[i]) for i in idx], "u": [float(u[i]) for i in idx],
                      "margins": m})
step = data["steps"][0]
rows = step["rows"]
sc = score([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows], 0.0, step["amp_dps"])
out = {"t": t, "des": des, "cases": cases,
       "score": {"t": [r[0] for r in rows], "des": [r[1] for r in rows], "ach": [r[2] for r in rows],
                 "amp": step["amp_dps"], "expected": sc}}
(ROOT / "docs/control-lab/test/fixture.json").write_text(json.dumps(out))
print("cases", len(cases), {c["plant"]["b"]: c["margins"]["pm_deg"] for c in cases})
