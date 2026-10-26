// SPDX-License-Identifier: MIT
// The JavaScript loop model must reproduce the Python one (software/wisp_gcs/fit.py) on the same inputs.
// Fixture: python3 software/wisp_gcs/make_fixture.py. Run: node --test docs/control-lab/test/
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { closedLoop, margins, score, shapedStep, bode, WISP_PLANT, ARDU_DEFAULTS } from "../js/loop.js";

const fx = JSON.parse(readFileSync(new URL("./fixture.json", import.meta.url)));
const close = (a, b, tol, what) => assert.ok(Math.abs(a - b) <= tol * Math.max(1, Math.abs(b)), `${what}: ${a} vs ${b}`);

test("closed loop matches Python on every plant and gain set", () => {
  for (const c of fx.cases) {
    const o = closedLoop(fx.t, fx.des, c.gains, c.plant, { w0: c.w0, i0: c.i0 });
    c.idx.forEach((k, j) => {
      if (!Number.isFinite(c.wf[j]) || Math.abs(c.wf[j]) > 1e6) return;      // diverging cases: compare the start
      close(o.wf[k], c.wf[j], 1e-6, `wf b=${c.plant.b} P=${c.gains.P} k=${k}`);
      close(o.u[k], c.u[j], 1e-6, `u b=${c.plant.b} P=${c.gains.P} k=${k}`);
    });
  }
});

test("stability margins match Python", () => {
  for (const c of fx.cases) {
    const m = margins(c.gains, c.plant), e = c.margins;
    for (const [js, py] of [["fcHz", "fc_hz"], ["pmDeg", "pm_deg"], ["f180Hz", "f180_hz"], ["gmDb", "gm_db"]]) {
      if (e[py] === null) { assert.equal(m[js], null, `${js} should be null`); continue; }
      close(m[js], e[py], 2e-3, `${js} b=${c.plant.b} P=${c.gains.P}`);
    }
  }
});

test("step score matches Python on recorded SITL data", () => {
  const s = fx.score, got = score(s.t, s.des, s.ach, 0, s.amp), e = s.expected;
  close(got.rise_s, e.rise_s, 1e-3, "rise");
  close(got.overshoot_pct, e.overshoot_pct, 0.02, "overshoot (Python rounds to 0.1)");
  close(got.rms_err_dps, e.rms_err_dps, 0.01, "rms");
  close(got.settle_s, e.settle_s, 1e-3, "settle");
});

test("shaped step slews at the acceleration limit and returns to zero", () => {
  const { t, des } = shapedStep({ ampDps: 90, dur: 0.4, accMaxDps2: 1100 });
  const at = (x) => des[t.findIndex((v) => v >= x)] / (Math.PI / 180);
  assert.equal(at(-0.1), 0);
  close(at(0.04), 1100 * 0.04, 0.03, "ramp");
  close(at(0.3), 90, 1e-9, "plateau");
  close(at(1.2), 0, 1e-9, "back to zero");
});

test("Bode phase is continuous (unwrapped)", () => {
  const pts = bode(ARDU_DEFAULTS, WISP_PLANT);
  for (let k = 1; k < pts.length; k++) assert.ok(Math.abs(pts[k].ph - pts[k - 1].ph) < Math.PI / 2);
});
