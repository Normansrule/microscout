// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Offline trainer for the Flight Lab's bundled policies (same code the browser runs):
//   node docs/lab/train.mjs '{"course":"forest","trainer":"cem","arch":"linear","init":"pd"}' 150 policies/forest.json
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { Trainer, runEpisode } from "./js/rl.js";
import { Policy } from "./js/policy.js";

const cfg = JSON.parse(process.argv[2] || "{}");
const iters = +(process.argv[3] || 100);
const out = resolve(process.argv[4] || "policies/out.json");
const T = new Trainer(cfg);
const t0 = Date.now();
for (let i = 0; i < iters; i++) {
  const { stats: s } = T.iterate();
  if ((i + 1) % 10 === 0) console.log(`${i + 1}/${iters} mean ${s.mean.toFixed(1)} val ${s.val.toFixed(1)} best ${T.best.ret.toFixed(1)} succ ${s.success}`);
}
// score the best policy on 20 unseen courses
const pol = Policy.fromJSON(T.exportPolicy("best"));
let succ = 0, crash = 0, ret = 0;
for (let s = 5000; s < 5020; s++) {
  const r = runEpisode(pol, pol.net.params, { ...T.opt, randomize: true }, s);
  succ += r.success; crash += r.crashed; ret += r.ret;
}
const meta = { ...T.exportPolicy("best"), config: T.opt, iterations: iters, trainSeconds: (Date.now() - t0) / 1000,
  test: { courses: 20, success: succ / 20, crash: crash / 20, meanReturn: ret / 20 },
  history: T.history.map((h) => ({ i: h.iter, mean: +h.mean.toFixed(2), max: +h.max.toFixed(2), val: +h.val.toFixed(2) })),
  note: "Trained in simulation with estimated parameters; not validated on hardware." };
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(meta));
console.log("wrote", out, meta.test);
