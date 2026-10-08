// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Runs RL training off the main thread so the 3D view stays smooth.
import { Trainer } from "./rl.js";

let trainer = null, running = false, looping = false, budget = Infinity;

async function loop() {
  if (looping) return;                 // a pause followed quickly by a start must not run two loops
  looping = true;
  while (running && trainer && budget-- > 0) {
    const out = trainer.iterate();
    postMessage({ type: "progress", ...out, history: trainer.history.slice(-1), sigmaMean: trainer.sig.reduce((a, c) => a + c, 0) / trainer.sig.length });
    if (trainer.opt.maxIters && trainer.iter >= trainer.opt.maxIters) { running = false; postMessage({ type: "done" }); }
    await new Promise((r) => setTimeout(r, 0));
  }
  if (budget <= 0) running = false;
  looping = false;
}

onmessage = (e) => {
  const m = e.data;
  if (m.type === "start") {
    if (!trainer || m.fresh) trainer = new Trainer(m.config);
    running = true; budget = m.iterations ?? Infinity;      // iterations: run that many, then pause (used by recordings)
    postMessage({ type: "started", n: trainer.n });
    loop();
  } else if (m.type === "pause") {
    running = false;
  } else if (m.type === "reset") {
    running = false; trainer = null;
  } else if (m.type === "export") {
    if (trainer) postMessage({ type: "policy", policy: trainer.exportPolicy(m.which || "best"), history: trainer.history });
  }
};
