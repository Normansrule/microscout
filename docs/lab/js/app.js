// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Flight Lab app: wires the simulator, controllers, RL worker, 3D view and the controls together.

import { buildCourse, COURSES, DEFAULT_SPEC, sanitizeSpec } from "./world.js";
import { Quad } from "./physics.js";
import { Mission, CONTROLLERS, PilotController, lqrGains, DEFAULT_GAINS } from "./control.js";
import { Policy, OBS_DIM } from "./policy.js";
import { TRAINERS, DEFAULT_TRAIN, pdPrior } from "./rl.js";
import { LabView, cssVar } from "./render.js";
import { PilotInput } from "./input.js";
import { lineChart } from "./charts.js";
import { toEuler, qrot } from "./math.js";

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const DT = 0.002;
const COLORS = () => ({ pid: cssVar("--c-pid", "#2a78d6"), lqr: cssVar("--c-lqr", "#13865b"), mpc: cssVar("--c-mpc", "#6f52d4"), smpc: cssVar("--c-smpc", "#6b7d12"), learned: cssVar("--c-rl", "#d6336c"), pilot: cssVar("--c-you", "#138a9e") });
const MODES = {
  beginner: "Sticks set speed (up to 2 m/s). Let go and it holds position. It stops about 40 cm short of anything its ToF sensors see.",
  sport: "Sticks set the tilt angle (up to 35°). Let go and it levels itself and holds height.",
  acro: "Sticks set rotation rate (up to 1000 °/s) and you own the throttle. Nothing is held for you - this is how flips and rolls are flown.",
};

const state = {
  tab: "fly", courseName: "gates", seed: 1, course: null, sims: [], speed: 1, rays: true, mode: "beginner",
  env: { wind: 0, dir: 90, gust: 0, motor: 100, payload: 0, noise: 0, battery: 100 },
  ctrlKind: "pid", ctrlOpts: { pid: { speed: 2, kp: 1 }, lqr: { qp: 4, qv: 1, r: 0.3 }, mpc: { samples: 64, horizon: 16, vmax: 2.5 }, smpc: { samples: 64, horizon: 16, vmax: 1.3 }, learned: { source: "bundled" } },
  spec: loadSpec(), tool: "pillar", editing: false,
  bundled: {}, trained: null, results: [], radioDropUntil: -1, lastHud: 0, logged: new Set(),
  train: { worker: null, running: false, hist: [], cfg: null, best: null, previewParams: null, previewT: 0 },
};

// ------------------------------------------------------------------ course editor storage
function encodeSpec(sp) {
  const r = (a) => a.map((v) => Math.round(v * 100) / 100);
  const j = JSON.stringify({ p: sp.pillars.map(r), c: sp.crates.map(r), g: sp.gates.map(r), o: r(sp.goal) });
  return btoa(j).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function decodeSpec(str) {
  try {
    const j = JSON.parse(atob(str.replace(/-/g, "+").replace(/_/g, "/")));
    return sanitizeSpec({ pillars: j.p, crates: j.c, gates: j.g, goal: j.o });
  } catch (e) { return null; }
}
function loadSpec() {
  const h = location.hash.match(/course=([\w-]+)/);
  if (h) { const s = decodeSpec(h[1]); if (s) return s; }
  try { const s = decodeSpec(localStorage.getItem("microscout-lab-course") || ""); if (s) return s; } catch (e) { /* storage blocked */ }
  return sanitizeSpec(DEFAULT_SPEC);
}
function saveSpec() {
  if (state.courseName === "custom" || /course=/.test(location.hash))
    history.replaceState(null, "", `${location.pathname}?course=custom#course=${encodeSpec(state.spec)}`);   // the address bar is always a share link
  try { localStorage.setItem("microscout-lab-course", encodeSpec(state.spec)); } catch (e) { /* storage blocked: the layout still lives in the page */ }
}

const view = new LabView($("#view"));
const input = new PilotInput($("#touch"));

// ------------------------------------------------------------------ helpers
function envObj(seed) {
  const e = state.env, a = (e.dir * Math.PI) / 180;
  return { wind: [-e.wind * Math.cos(a), -e.wind * Math.sin(a), 0], gust: e.gust, motorHealth: [1, 1, e.motor / 100, 1], payload_g: e.payload, tofNoise: e.noise, batterySoc: e.battery / 100, seed };
}
function log(msg, cls = "") {
  const ol = $("#log");
  const li = document.createElement("li");
  li.textContent = msg; if (cls) li.className = cls;
  ol.appendChild(li);
  while (ol.children.length > 5) ol.removeChild(ol.firstChild);
  setTimeout(() => li.remove(), 9000);
}
let toastT = 0;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 2600); }

function policyFor(kind) {
  if (kind !== "learned") return null;
  if (state.ctrlOpts.learned.source === "trained" && state.trained) return state.trained;
  const b = state.bundled[state.courseName];
  if (b) return b;
  const p = new Policy("linear"); p.net.params = pdPrior(p.net, "velocity"); p.meta = { untrained: true, config: { actionMode: "velocity" } };
  return p;
}

function makeSim(kind, color, opts = {}) {
  const course = state.course;
  const quad = new Quad(course, undefined, envObj(state.seed));
  const airborne = kind !== "pilot";
  if (airborne) {
    quad.reset([course.start[0], course.start[1], course.start[2] >= 0 ? -1.0 : course.start[2]]);
    quad.thrust = [0, 1, 2, 3].map(() => (quad.mass * 9.81) / 4);
  }
  const mission = new Mission(course);
  let ctrl;
  if (kind === "pilot") { ctrl = new PilotController(quad); ctrl.mode = state.mode; }
  else if (kind === "learned") {
    const pol = opts.policy || policyFor(kind);
    const cfg = pol.meta?.config || {};
    ctrl = CONTROLLERS.learned.make(quad, mission, { policy: { act: (o) => pol.act(o, opts.params) }, residual: cfg.residual, actionMode: cfg.actionMode || "velocity" });
  } else {
    const o = state.ctrlOpts[kind] || {};
    const gains = { ...DEFAULT_GAINS };
    if (kind === "pid") { gains.max_speed_ms = o.speed; gains.pos_kp = DEFAULT_GAINS.pos_kp.map((k) => k * o.kp); }
    ctrl = CONTROLLERS[kind].make(quad, mission, { gains, qp: o.qp, qv: o.qv, r: o.r, samples: o.samples, horizon: o.horizon, vmax: o.vmax });
  }
  const drone = view.addDrone(color, { rays: opts.primary && state.rays, tint: opts.tint });
  return { kind, quad, mission, ctrl, drone, color, status: "flying", name: opts.name || ctrl.name, primary: !!opts.primary, evIdx: 0, msgIdx: 0, preview: !!opts.preview };
}

function clearSims() { view.removeDrones(); view.clearPlan(); view.clearHits(); state.sims = []; }

function setCourse(name, seed = state.seed) {
  state.courseName = name; state.seed = seed;
  if ($("#courseSel")) $("#courseSel").value = name;
  state.course = buildCourse(name, seed, name === "forest" || name === "window", state.spec);
  $("#editor").hidden = name !== "custom";
  if (name !== "custom") setEditing(false);
  view.setCourse(state.course);
  const info = COURSES.find((c) => c[0] === name);
  $("#courseAbout").textContent = info ? info[2] : "";
  if (state.train.running) stopTraining();
  state.results = []; renderResults();
  resetTab();
}

function resetTab() {
  clearSims();
  view.clearGhosts();
  state.logged.clear();
  if (state.tab === "fly" || state.tab === "sit") {
    state.sims.push(makeSim("pilot", COLORS().pilot, { primary: true, name: "You (pilot)" }));
    view.setCamera(view.camMode === "top" ? "top" : "chase");
  } else if (state.tab === "auto") {
    state.sims.push(makeSim(state.ctrlKind, COLORS()[state.ctrlKind], { primary: true }));
  } else if (state.tab === "train") {
    if (view.camMode === "chase") view.setCamera("orbit");      // the ghosts of a whole population read best from above
    startPreview(state.train.previewParams);
  }
  updateCamButtons();
}

// ------------------------------------------------------------------ simulation loop
function stepSims(simDt) {
  const n = Math.min(200, Math.round(simDt / DT));
  for (let k = 0; k < n; k++) {
    for (const s of state.sims) {
      if (s.status !== "flying") continue;
      const q = s.quad, prev = [...q.pos];
      const u = s.ctrl.update(DT);
      q.step(u, DT);
      const bonus = s.mission.update(prev, q.pos);
      if (bonus && s.primary && s.kind !== "pilot") view.setActiveWaypoint(s.mission.i);
      if (s.kind === "pilot") {
        if (bonus) view.setActiveWaypoint(s.mission.i);
        if (s.mission.done && !s.doneLogged && !state.course.free) { s.doneLogged = true; toast(`Course complete in ${q.t.toFixed(1)} s`); log(`course complete in ${q.t.toFixed(1)} s`, "ok"); }
        continue;
      }
      const [r, p] = toEuler(q.q);
      if (s.mission.done && !state.course.hold) finish(s, "done");
      else if (q.maxImpact > 1.5) finish(s, "crashed");
      else if (Math.max(Math.abs(r), Math.abs(p)) > 1.4 || (q.onGround && q.t > 1.5)) finish(s, "crashed");
      else if (q.t > state.course.timeLimit) finish(s, state.course.hold ? "held" : "timed out");
    }
  }
}

function finish(s, status) {
  s.status = status;
  if (s.preview) { state.train.previewT = performance.now(); return; }
  const res = { name: s.name, color: s.color, status, t: s.quad.t, hit: s.quad.maxImpact, gates: s.mission.i };
  state.results.unshift(res);
  state.results = state.results.slice(0, 8);
  renderResults();
  const msg = status === "done" ? `${s.name}: finished in ${s.quad.t.toFixed(1)} s` : status === "held" ? `${s.name}: held for ${s.quad.t.toFixed(0)} s` : `${s.name}: ${status}`;
  log(msg, status === "done" || status === "held" ? "ok" : "bad");
  if (state.sims.filter((x) => x.status === "flying").length === 0) toast(msg);
}

function renderResults() {
  const tb = $("#results tbody");
  tb.innerHTML = state.results.map((r) => `<tr><td><span style="color:${r.color}">●</span> ${r.name}</td><td class="${r.status === "done" || r.status === "held" ? "ok" : "bad"}">${{ done: "finished", held: "held position" }[r.status] || r.status}</td><td>${r.t.toFixed(1)} s</td><td>${r.hit > 0.05 ? r.hit.toFixed(1) + " m/s" : "none"}</td></tr>`).join("");
}

function pilotInput(real) {
  const s = state.sims.find((x) => x.kind === "pilot");
  if (!s) return;
  const q = s.quad;
  if (q.t < state.radioDropUntil) return;      // radio "dropped": no stick updates reach the drone
  s.ctrl.mode = state.mode;
  s.ctrl.setSticks(input.read(state.mode, real), q.t);
}

function progress(s) {
  const c = state.course;
  if (c.free) return "free flight";
  if (c.hold) return "holding";
  if (c.gates.length && state.courseName === "gates") return `${s.mission.gatesPassed} of ${c.gates.length} gates`;
  if (state.courseName === "custom") return `${s.mission.gatesPassed} of ${c.gates.length} gates, then the goal`;
  return `${Math.min(s.mission.i, c.waypoints.length)} of ${c.waypoints.length} points`;
}

function hud() {
  const ro = $("#readout");
  const racers = state.sims.filter((x) => !x.preview && x.kind !== "pilot");
  if (racers.length > 1) {                 // race: one line per controller
    ro.className = "hud readout board";
    const label = { done: "finished", held: "held", crashed: "crashed", "timed out": "timed out" };
    ro.innerHTML = `<span class="h">Controller</span><span class="h">Progress</span><span class="h">Time</span>` + racers.map((s) =>
      `<span class="n"><i style="background:${s.color}"></i>${s.name}</span><span>${progress(s)}</span><span class="${s.status === "flying" ? "" : s.status === "done" || s.status === "held" ? "ok" : "bad"}">${s.status === "flying" ? s.quad.t.toFixed(1) + " s" : `${label[s.status] || s.status} ${s.quad.t.toFixed(1)} s`}</span>`).join("");
    return;
  }
  ro.className = "hud readout";
  const s = state.sims.find((x) => x.primary) || state.sims[0];
  if (!s) { ro.innerHTML = ""; return; }
  const q = s.quad, [r, p] = toEuler(q.q);
  const tilt = (Math.acos(Math.max(-1, Math.min(1, qrot(q.q)[8]))) * 180) / Math.PI;
  const wps = state.course.waypoints.length;
  const prog = state.course.free ? "free flight" : state.course.hold ? `holding ${Math.hypot(q.pos[0] - state.course.waypoints[0][0], q.pos[1] - state.course.waypoints[0][1], q.pos[2] - state.course.waypoints[0][2]).toFixed(2)} m from the mark` : state.course.gates.length && state.courseName === "gates" ? `gate ${Math.min(s.mission.gatesPassed + 1, state.course.gates.length)} of ${state.course.gates.length}` : `waypoint ${Math.min(s.mission.i + 1, wps)} of ${wps}`;
  let status = s.kind === "pilot" ? (s.ctrl.armed ? `${state.mode} mode` : "on the ground - press T to take off") : s.status;
  if (s.kind === "pilot" && q.t < state.radioDropUntil) status = "radio link down";
  void r; void p;
  $("#readout").innerHTML = `<span class="who"><i style="background:${s.color}"></i>${s.name}</span>
    <span><b>${q.height.toFixed(2)}</b><small>height m</small></span>
    <span><b>${Math.hypot(...q.vel).toFixed(1)}</b><small>speed m/s</small></span>
    <span><b>${tilt.toFixed(0)}°</b><small>tilt</small></span>
    <span><b>${(q.bat.voltage / 2).toFixed(2)}</b><small>V per cell</small></span>
    <span><b>${q.bat.current.toFixed(1)}</b><small>battery A</small></span>
    <span><b>${q.t.toFixed(1)}</b><small>time s</small></span>
    <span class="st">${status} · ${prog}</span>`;
}

function events() {
  for (const s of state.sims) {
    if (!s.primary && state.sims.length > 1) continue;
    const ev = s.quad.events;
    for (; s.evIdx < ev.length; s.evIdx++) {
      const e = ev[s.evIdx];
      if (e.speed > 0.3) log(`${s.kind === "pilot" ? "Hit" : s.name + " hit"} ${e.kind === "obstacle" ? "an obstacle" : "the " + e.kind} at ${e.speed.toFixed(1)} m/s${e.speed > 3 ? " - beyond the 3 m/s design target" : ""}`, "bad");
    }
    if (s.kind === "pilot") {
      const m = s.ctrl.msgs;
      for (; s.msgIdx < m.length; s.msgIdx++) log(m[s.msgIdx], /lost|low|refused/.test(m[s.msgIdx]) ? "bad" : "");
    }
  }
}

let last = performance.now();
function frame(now) {
  const real = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (!state.manual) tick(real, now);
  requestAnimationFrame(frame);
}

/** One display frame: read the sticks, advance the simulation by real * speed, draw. */
function tick(real, now = performance.now()) {
  pilotInput(real);
  stepSims(real * state.speed);
  const prim = state.sims.find((x) => x.primary) || state.sims[0];
  for (const s of state.sims) view.updateDrone(s.drone, s.quad, s.primary && state.rays ? s.quad.tof() : null);
  if (prim && prim.ctrl.lastSamples && state.rays) view.setPlan(prim.ctrl.lastSamples, COLORS()[prim.kind] || COLORS().mpc);
  const mapper = state.sims.find((x) => x.ctrl.map);
  if (mapper && mapper.ctrl.map.n !== view.hitsN) view.setHits(mapper.ctrl.map.points(), COLORS().smpc);
  if (state.tab === "train" && state.train.previewParams && state.sims[0] && state.sims[0].status !== "flying" && now - state.train.previewT > 800) startPreview(state.train.previewParams);
  if (now - state.lastHud > 120) { hud(); events(); state.lastHud = now; }
  view.render(prim ? prim.quad : null, real);
}

// ------------------------------------------------------------------ fly tab
function pilot() { return state.sims.find((x) => x.kind === "pilot"); }
function setMode(m) {
  state.mode = m;
  $$("#modeSeg button").forEach((b) => b.setAttribute("aria-checked", b.dataset.mode === m));
  $("#modeAbout").textContent = MODES[m];
}
function doFlip() {
  const s = pilot(); if (!s) return;
  const st = input.read(state.mode, 0);
  const dir = Math.abs(st.pitch) > 0.4 ? (st.pitch > 0 ? "front" : "back") : Math.abs(st.roll) > 0.4 ? (st.roll > 0 ? "right" : "left") : "back";
  s.ctrl.flip(dir);
}
input.handlers.press = (k) => {
  const s = pilot();
  if (k === "c") { const order = ["chase", "orbit", "top"]; setCam(order[(order.indexOf(view.camMode) + 1) % 3]); return; }
  if (!s) return;
  if (k === "t") s.ctrl.armed ? null : s.ctrl.arm();
  else if (k === "l") s.ctrl.land();
  else if (k === "x" || k === "x-flip") doFlip();
  else if (k === "k") s.ctrl.disarm("motors off (kill)");
  else if (k === "1") setMode("beginner"); else if (k === "2") setMode("sport"); else if (k === "3") setMode("acro");
  else if (k === "m") setMode({ beginner: "sport", sport: "acro", acro: "beginner" }[state.mode]);
};

// ------------------------------------------------------------------ autopilot tab
function buildCtrlList() {
  const c = COLORS();
  $("#ctrlList").innerHTML = '<legend>Controller</legend>' + Object.entries(CONTROLLERS).map(([k, v]) =>
    `<label class="ctrl" style="--swatch:${c[k]}"><input type="radio" name="ctrl" value="${k}" ${k === state.ctrlKind ? "checked" : ""}><span class="sw"></span><span class="n">${v.label}</span></label>`).join("");
  $$('#ctrlList input').forEach((i) => i.addEventListener("change", () => { state.ctrlKind = i.value; ctrlParams(); resetTab(); }));
  ctrlParams();
}
function slider(id, label, min, max, step, val, fmt, on) {
  return { html: `<label>${label}<output id="${id}O">${fmt(val)}</output><input type="range" id="${id}" min="${min}" max="${max}" step="${step}" value="${val}"></label>`, id, fmt, on };
}
function ctrlParams() {
  const k = state.ctrlKind, o = state.ctrlOpts[k];
  $("#ctrlAbout").textContent = CONTROLLERS[k].about;
  let items = [];
  if (k === "pid") items = [slider("pSpeed", "Speed limit", 0.5, 4, 0.25, o.speed, (v) => `${(+v).toFixed(2)} m/s`, (v) => (o.speed = +v)),
    slider("pKp", "Position gain", 0.4, 2.5, 0.1, o.kp, (v) => `×${(+v).toFixed(1)}`, (v) => (o.kp = +v))];
  if (k === "lqr") items = [slider("lQp", "Q position", 0.5, 30, 0.5, o.qp, (v) => (+v).toFixed(1), (v) => (o.qp = +v)),
    slider("lQv", "Q velocity", 0.1, 6, 0.1, o.qv, (v) => (+v).toFixed(1), (v) => (o.qv = +v)),
    slider("lR", "R effort", 0.05, 3, 0.05, o.r, (v) => (+v).toFixed(2), (v) => (o.r = +v))];
  if (k === "mpc" || k === "smpc") items = [slider("mS", "Sampled futures", 16, 160, 8, o.samples, (v) => v, (v) => (o.samples = +v)),
    slider("mH", "Look-ahead", 8, 30, 1, o.horizon, (v) => `${(v * 0.05).toFixed(2)} s`, (v) => (o.horizon = +v)),
    slider("mV", "Speed limit", 1, 4, 0.25, o.vmax, (v) => `${(+v).toFixed(2)} m/s`, (v) => (o.vmax = +v))];
  let extra = "";
  if (k === "lqr") { const K = lqrGains(o.qp, o.qv, o.r); extra = `<p class="hint" id="lqrK">Riccati solution: a = ${K[0].toFixed(2)} × position error − ${K[1].toFixed(2)} × velocity</p>`; }
  if (k === "learned") {
    const b = state.bundled[state.courseName];
    extra = `<label>Policy<select id="polSrc"><option value="bundled">${b ? `Pre-trained for this course (${b.meta.config.trainer.toUpperCase()}, ${b.meta.iterations} iterations, ${Math.round(b.meta.test.success * 100)} % success on 20 new layouts)` : "Untrained: plain PD steering (train one on the Train tab)"}</option><option value="trained" ${state.trained ? "" : "disabled"}>Your trained policy${state.trained ? "" : " (train one first)"}</option></select></label>`;
  }
  $("#ctrlParams").innerHTML = items.map((i) => i.html).join("") + extra;
  for (const it of items) $("#" + it.id).addEventListener("input", (e) => { $("#" + it.id + "O").textContent = it.fmt(e.target.value); it.on(e.target.value); if (k === "lqr") { const K = lqrGains(o.qp, o.qv, o.r); $("#lqrK").textContent = `Riccati solution: a = ${K[0].toFixed(2)} × position error − ${K[1].toFixed(2)} × velocity`; } });
  const ps = $("#polSrc");
  if (ps) { ps.value = state.ctrlOpts.learned.source === "trained" && state.trained ? "trained" : "bundled"; ps.addEventListener("change", () => { state.ctrlOpts.learned.source = ps.value; resetTab(); }); }
}
function flyAuto() { clearSims(); view.setActiveWaypoint(0); state.sims.push(makeSim(state.ctrlKind, COLORS()[state.ctrlKind], { primary: true })); }
function race() {
  clearSims(); view.setActiveWaypoint(0);
  const c = COLORS();
  const kinds = ["pid", "lqr", "mpc", "smpc", "learned"];
  kinds.forEach((k) => state.sims.push(makeSim(k, c[k], { primary: k === "learned", name: CONTROLLERS[k].label })));
  setCam("orbit");
  log("race: every autopilot flies the same course at once", "");
}

// ------------------------------------------------------------------ train tab
function trainCfg() {
  return {
    ...DEFAULT_TRAIN, trainer: $("#trainerSel").value, course: state.courseName, arch: $("#archSel").value, init: $("#initSel").value,
    actionMode: $("#actSel").value, residual: $("#residualChk").checked, population: +$("#popR").value, sigma: +$("#sigR").value,
    lr: +$("#lrR").value, randomize: $("#randChk").checked, episodes: $("#randChk").checked ? 2 : 1,
    wind: state.env.wind, gust: state.env.gust, spec: state.courseName === "custom" ? state.spec : undefined,
  };
}
function startTraining(iterations) {
  const t = state.train;
  if (!t.worker) {
    t.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
    t.worker.onmessage = onTrain;
  }
  const fresh = !t.cfg || JSON.stringify(t.cfg) !== JSON.stringify(trainCfg());
  if (fresh) { t.cfg = trainCfg(); t.hist = []; view.clearGhosts(); }
  t.worker.postMessage({ type: "start", config: t.cfg, fresh, iterations: Number.isFinite(iterations) ? iterations : undefined });
  t.running = true;
  $("#trainBtn").textContent = "Pause";
}
function stopTraining() {
  const t = state.train;
  if (t.worker) t.worker.postMessage({ type: "pause" });
  t.running = false;
  $("#trainBtn").textContent = "Resume training";
}
function onTrain(e) {
  const m = e.data, t = state.train;
  if (m.type !== "progress") return;
  const s = m.stats;
  t.hist.push(s);
  view.setGhosts(m.ghosts, COLORS().learned, 0.35, 36);
  t.best = m.best;
  const pol = new Policy(t.cfg.arch, m.best);
  pol.meta = { config: t.cfg, iterations: s.iter };
  state.trained = pol;
  if (!t.previewParams || s.val >= Math.max(...t.hist.map((h) => h.val))) { t.previewParams = m.best; }
  $("#useBest").disabled = false; $("#savePol").disabled = false;
  $("#trainStats").innerHTML = `Iteration <b>${s.iter}</b> · population mean <b>${s.mean.toFixed(1)}</b> · current policy on 2 test courses <b>${s.val.toFixed(1)}</b> (finished ${Math.round(s.success * 100)} %, crashed ${Math.round(s.crash * 100)} %) · ${s.ms.toFixed(0)} ms per iteration`;
  drawCurve();
}
function drawCurve() {
  const h = state.train.hist, c = COLORS();
  lineChart($("#curve"), [
    { points: h.map((x) => [x.iter, x.mean]), band: h.map((x) => [x.iter, x.min, x.max]), color: c.learned },
    { points: h.map((x) => [x.iter, x.val]), color: c.pid, width: 1.2, dots: true },
  ], { xlabel: "iteration", empty: "The learning curve appears here: return per episode, higher is better." });
}
function startPreview(params) {
  if (state.tab !== "train") return;
  clearSims();
  const cfg = state.train.cfg || trainCfg();
  const pol = new Policy(cfg.arch, params || null);
  if (!params) pol.net.params = cfg.init === "pd" && cfg.arch === "linear" ? pdPrior(pol.net, cfg.actionMode) : pol.net.params;
  pol.meta = { config: cfg };
  state.sims.push(makeSim("learned", COLORS().learned, { primary: true, preview: true, policy: pol, name: params ? "Best policy so far" : "Starting policy" }));
}

// ------------------------------------------------------------------ situations
const SIT = [["windR", "windO", "wind", (v) => `${v} m/s`], ["dirR", "dirO", "dir", (v) => `${v}°`], ["gustR", "gustO", "gust", (v) => `${v} m/s`],
  ["motorR", "motorO", "motor", (v) => `${v} %`], ["payR", "payO", "payload", (v) => `${v} g`], ["noiseR", "noiseO", "noise", (v) => `${Math.round(v * 100)} cm`], ["batR", "batO", "battery", (v) => `${v} %`]];
function bindSituations() {
  for (const [r, o, key, fmt] of SIT) $("#" + r).addEventListener("input", (e) => { state.env[key] = +e.target.value; $("#" + o).textContent = fmt(e.target.value); });
  $("#applySit").addEventListener("click", () => { resetTab(); toast("Situation applied"); });
  $("#clearSit").addEventListener("click", () => {
    Object.assign(state.env, { wind: 0, dir: 90, gust: 0, motor: 100, payload: 0, noise: 0, battery: 100 });
    for (const [r, o, key, fmt] of SIT) { $("#" + r).value = state.env[key]; $("#" + o).textContent = fmt(state.env[key]); }
    resetTab();
  });
}

// ------------------------------------------------------------------ tabs, camera, misc
function selectTab(t) {
  state.tab = t;
  for (const id of ["fly", "auto", "train", "sit"]) {
    $("#t-" + id).setAttribute("aria-selected", id === t);
    $("#p-" + id).hidden = id !== t;
  }
  document.body.classList.toggle("flying", t === "fly");
  if (t !== "train" && state.train.running) stopTraining();
  if (t === "auto") ctrlParams();
  if (t === "train") drawCurve();
  resetTab();
}
function setCam(m) { view.setCamera(m); updateCamButtons(); }
function updateCamButtons() { $$(".cams [data-cam]").forEach((b) => b.classList.toggle("on", b.dataset.cam === view.camMode)); }

const BUNDLED = ["gates", "forest", "window"];   // courses with a policy trained offline by train.mjs
async function loadBundled() {
  for (const name of BUNDLED) {
    try {
      const r = await fetch(`policies/${name}-cem-linear.json`);
      if (!r.ok) continue;
      const j = await r.json();
      const p = Policy.fromJSON(j); p.meta = j;
      state.bundled[name] = p;
    } catch (e) { /* no bundled policy for this course */ }
  }
}

function savePolicy() {
  const p = state.trained; if (!p) return;
  const blob = new Blob([JSON.stringify({ ...p.toJSON(), config: state.train.cfg, history: state.train.hist, note: "MicroScout Flight Lab policy - simulation only" })], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `microscout-${state.courseName}-${state.train.cfg?.trainer || "policy"}.json`; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
async function loadPolicy(file) {
  try {
    const j = JSON.parse(await file.text());
    if (!Array.isArray(j.params) || !j.arch) throw new Error("not a Flight Lab policy file");
    const p = Policy.fromJSON(j);
    if (p.net.sizes[0] !== OBS_DIM) throw new Error("observation size does not match this version");
    p.meta = { config: j.config || {} };
    state.trained = p; state.ctrlOpts.learned.source = "trained";
    toast("Policy loaded - fly it on the Autopilot tab");
    $("#useBest").disabled = false;
  } catch (e) { toast(`Could not load the policy: ${e.message}`); }
}

// ------------------------------------------------------------------ course editor
function setEditing(on) {
  state.editing = on;
  document.body.classList.toggle("editing", on);
  $("#edTools").hidden = !on;
  $("#edToggle").setAttribute("aria-pressed", on);
  $("#edToggle").textContent = on ? "Done editing" : "Edit layout";
  if (on) setCam("top");
}
function setTool(t) {
  state.tool = t;
  $$("#toolSeg button").forEach((b) => b.setAttribute("aria-checked", b.dataset.tool === t));
}
function applySpec(sp, msg) {
  state.spec = sanitizeSpec(sp);
  saveSpec();
  const cam = view.camMode;
  setCourse("custom", state.seed);
  if (cam !== view.camMode) setCam(cam);
  if (msg) log(msg);
}
function editAt(x, y) {
  const sp = JSON.parse(JSON.stringify(state.spec));
  const r1 = (v) => Math.round(v * 10) / 10;
  x = r1(x); y = r1(y);
  if (Math.hypot(x + 5, y) < 0.8) return toast("Keep the take-off spot clear");
  if (state.tool === "pillar") sp.pillars.push([x, y, 0.2]);
  else if (state.tool === "crate") sp.crates.push([x, y, 0.8, 0.8, 1.0]);
  else if (state.tool === "gate") sp.gates.push([x, y, -1.2]);
  else if (state.tool === "goal") sp.goal = [x, y, -1.2];
  else {                                               // erase the nearest thing within 0.6 m
    let best = null, bd = 0.6;
    for (const k of ["pillars", "crates", "gates"]) sp[k].forEach((o, i) => { const d = Math.hypot(o[0] - x, o[1] - y); if (d < bd) { bd = d; best = [k, i]; } });
    if (!best) return;
    sp[best[0]].splice(best[1], 1);
  }
  applySpec(sp);
}

function init() {
  $("#courseSel").innerHTML = COURSES.map(([k, l]) => `<option value="${k}">${l}</option>`).join("");
  $("#courseSel").value = state.courseName;
  $("#courseSel").addEventListener("change", (e) => setCourse(e.target.value, 1));
  $("#reseed").addEventListener("click", () => setCourse(state.courseName, Math.floor(Math.random() * 1e6)));
  $("#trainerSel").innerHTML = Object.entries(TRAINERS).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join("");
  const tAbout = () => ($("#trainerAbout").textContent = TRAINERS[$("#trainerSel").value].about);
  $("#trainerSel").addEventListener("change", tAbout); tAbout();
  for (const id of ["archSel", "initSel", "actSel", "residualChk"])     // show the new starting policy before training starts
    $("#" + id).addEventListener("change", () => { if (!state.train.hist.length && !state.train.running) startPreview(null); });
  for (const [r, o, f] of [["popR", "popO", (v) => v], ["sigR", "sigO", (v) => (+v).toFixed(2)], ["lrR", "lrO", (v) => (+v).toFixed(3)]])
    $("#" + r).addEventListener("input", (e) => ($("#" + o).textContent = f(e.target.value)));
  $$(".tabs button").forEach((b) => b.addEventListener("click", () => selectTab(b.id.slice(2))));
  $(".tabs").addEventListener("keydown", (e) => {                     // arrow keys move between tabs
    const ids = ["fly", "auto", "train", "sit"], i = ids.indexOf(state.tab);
    const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (!d) return;
    const n = ids[(i + d + 4) % 4]; selectTab(n); $("#t-" + n).focus(); e.preventDefault();
  });
  $$("#modeSeg button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  setMode("beginner");
  $("#takeoffBtn").addEventListener("click", () => input.handlers.press("t"));
  $("#landBtn").addEventListener("click", () => input.handlers.press("l"));
  $("#flipBtn").addEventListener("click", () => pilot()?.ctrl.flip("back"));
  for (const id of ["takeoffBtn", "landBtn", "flipBtn", "radioBtn"]) $("#" + id).addEventListener("click", () => $("#view").focus({ preventScroll: true }));   // keys fly the drone again
  $$("#modeSeg button").forEach((b) => b.addEventListener("click", () => $("#view").focus({ preventScroll: true })));
  $("#radioBtn").addEventListener("click", () => { const s = pilot(); if (s) { state.radioDropUntil = s.quad.t + 5; log("radio link dropped for 5 s", "bad"); } });
  $("#flyAuto").addEventListener("click", flyAuto);
  $("#raceBtn").addEventListener("click", race);
  $("#trainBtn").addEventListener("click", () => (state.train.running ? stopTraining() : startTraining()));
  $("#trainReset").addEventListener("click", () => { stopTraining(); state.train.worker?.postMessage({ type: "reset" }); Object.assign(state.train, { hist: [], cfg: null, previewParams: null }); $("#trainBtn").textContent = "Start training"; view.clearGhosts(); drawCurve(); resetTab(); $("#trainStats").textContent = "Reset. Press Start to train from scratch."; });
  $("#useBest").addEventListener("click", () => { state.ctrlKind = "learned"; state.ctrlOpts.learned.source = "trained"; selectTab("auto"); buildCtrlList(); flyAuto(); });
  $("#savePol").addEventListener("click", savePolicy);
  $("#loadPol").addEventListener("change", (e) => e.target.files[0] && loadPolicy(e.target.files[0]));
  $$(".cams [data-cam]").forEach((b) => b.addEventListener("click", () => setCam(b.dataset.cam)));
  $("#raysBtn").addEventListener("click", (e) => { state.rays = !state.rays; e.target.classList.toggle("on", state.rays); e.target.setAttribute("aria-pressed", state.rays); view.drones.forEach((d) => (d.rays.visible = state.rays && d === state.sims.find((s) => s.primary)?.drone)); if (!state.rays) view.clearPlan(); });
  $("#speedBtn").addEventListener("click", (e) => { state.speed = { 1: 2, 2: 0.5, 0.5: 1 }[state.speed]; e.target.textContent = `${state.speed}×`; });
  bindSituations();
  $("#edToggle").addEventListener("click", () => setEditing(!state.editing));
  $$("#toolSeg button").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
  $("#edStarter").addEventListener("click", () => applySpec(DEFAULT_SPEC, "starter layout restored"));
  $("#edClear").addEventListener("click", () => applySpec({ pillars: [], crates: [], gates: [], goal: state.spec.goal }, "layout cleared"));
  $("#edShare").addEventListener("click", async () => {
    const url = `${location.origin}${location.pathname}?course=custom#course=${encodeSpec(state.spec)}`;
    history.replaceState(null, "", url);
    try { await navigator.clipboard.writeText(url); toast("Link copied"); } catch (e) { toast("Copy the link from the address bar"); }
  });
  let down = null;
  $("#view").addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
  $("#view").addEventListener("pointerup", (e) => {
    if (!state.editing || !down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
    const p = view.pickFloor(e.clientX, e.clientY);
    if (p) editAt(p[0], p[1]);
  });
  buildCtrlList();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { view.applyTheme(); setCourse(state.courseName, state.seed); buildCtrlList(); });
  const params = new URLSearchParams(location.search);
  if (params.get("course") && COURSES.some((c) => c[0] === params.get("course"))) state.courseName = params.get("course");
  if (/course=/.test(location.hash)) state.courseName = "custom";
  $("#courseSel").value = state.courseName;
  if (params.has("embed")) document.body.classList.add("embed");      // just the 3D view, for embedding and recordings
  setCourse(state.courseName, 1);
  if (params.get("tab")) selectTab(params.get("tab"));
  if (params.get("demo") === "race") { selectTab("auto"); race(); }
  if (params.get("cam")) setCam(params.get("cam"));
}

(async () => {
  await Promise.all([view.loadModel("../models/microscout_concept.glb"), loadBundled()]);
  $("#loading").remove();
  init();
  window.lab = { tick, state, view, input, pilot, doFlip, setMode, race, flyAuto, selectTab, setCourse, startTraining, stopTraining, setCam };   // for tests and the README renders
  requestAnimationFrame(frame);
})();
