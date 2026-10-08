// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Learning curves for the four RL algorithms in the Train tab, from random weights, on the
// window course with a new random layout every iteration. Writes docs/data/lab_learning.json
// (used by tools/viz/lab_charts.py). Simulation only.
//   node docs/lab/test/curves.mjs [iterations=80] [seeds=3] [algorithms=cem,es,ars,reinforce]
import { writeFileSync, existsSync, readFileSync } from "node:fs";
import { Trainer, DEFAULT_TRAIN } from "../js/rl.js";

const iters = +(process.argv[2] || 80), seeds = +(process.argv[3] || 3);
const algs = (process.argv[4] || "cem,es,ars,reinforce").split(",");
const file = new URL("../../data/lab_learning.json", import.meta.url);
const out = existsSync(file) ? JSON.parse(readFileSync(file)) : { course: "window", init: "random", runs: {} };
Object.assign(out, { note: "Simulation with estimated parameters (docs/lab). Not a measurement.", iterations: iters, seeds });
for (const alg of algs) {
  out.runs[alg] = [];
  for (let s = 0; s < seeds; s++) {
    const T = new Trainer({ ...DEFAULT_TRAIN, course: "window", trainer: alg, init: "random", randomize: true, seed: 21 + s });
    const t0 = Date.now(), val = [], succ = [];
    for (let i = 0; i < iters; i++) { const { stats } = T.iterate(); val.push(+stats.val.toFixed(2)); succ.push(stats.success); }
    out.runs[alg].push({ seed: 21 + s, val, success: succ, msPerIter: (Date.now() - t0) / iters });
    console.log(alg, "seed", 21 + s, "final val", val.slice(-10).reduce((a, b) => a + b, 0) / 10, "ms/it", ((Date.now() - t0) / iters).toFixed(0));
  }
  writeFileSync(file, JSON.stringify(out));
}
