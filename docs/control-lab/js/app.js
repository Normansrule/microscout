// SPDX-License-Identifier: MIT
// Wisp Control Lab, Phase 1: the roll-rate loop against three sources of data.
//   Model      the loop model (loop.js) on a fitted SITL plant or the Wisp Follow estimate
//   Recording  roll-rate steps recorded from ArduCopter 4.7.2 SITL through the bridge (data/sitl-roll-steps.json)
//   Live SITL  a running bridge (software/wisp_gcs/bridge.py): telemetry, PID terms, commands
// STATUS: Phase 1 draft. Simulation only; nothing here has flown.

import { closedLoop, shapedStep, bode, margins, score, ARDU_DEFAULTS, WISP_PLANT, RAD } from "./loop.js";
import { chart, fmt } from "./chart.js";
import { diagramSVG, setDiagram, equationHTML } from "./diagram.js";

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const DEG = 180 / Math.PI;
const PRE = 0.3, POST = 1.4, MODEL_AMP = 90;
// Used until data/sitl-roll-steps.json loads (and if it cannot): the same fit, rounded.
const SITL_FALLBACK = { b: 280.5, a: 2.33, tau: 0.0001, td: 0.003, gyro_hz: 20 };
const BRIDGE_PORT = 8765;
const bridgeURL = (() => {
  const local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname) && location.port === String(BRIDGE_PORT);
  return local ? `ws://${location.host}/ws` : `ws://127.0.0.1:${BRIDGE_PORT}/ws`;
})();

const S = {
  source: null,
  plantKey: "sitl",
  gyro: { sitl: 20, wisp: WISP_PLANT.gyro_hz },
  gains: { ...ARDU_DEFAULTS },
  data: null,
  sitlPlant: { ...SITL_FALLBACK },
  stepIdx: 0,
  t: 0.05,
  playing: false,
  view: null,
  live: { ws: null, connected: false, state: null, ring: [], params: {}, steps: [], pending: null, appRtt: null, retry: null, ping: null },
};

// ---------------------------------------------------------------------------------------------------------
function plant() {
  if (S.source !== "model") return S.sitlPlant;
  return S.plantKey === "wisp" ? { ...WISP_PLANT, gyro_hz: S.gyro.wisp } : { ...S.sitlPlant, gyro_hz: S.gyro.sitl };
}

function stepFromRows(rows, gains, amp, name, meta = {}) {
  const t = rows.map((r) => r[0]), des = rows.map((r) => r[1]), ach = rows.map((r) => r[2]);
  const ff = rows.map((r) => r[3]), p = rows.map((r) => r[4]), i = rows.map((r) => r[5]), d = rows.map((r) => r[6]);
  return { name, t, des, ach, ff, p, i, d, gains, amp, ...meta };
}

function buildView() {
  const g = S.gains, pl = plant();
  let rec = null;
  if (S.source === "replay" && S.data) {
    const s = S.data.steps[S.stepIdx];
    rec = stepFromRows(s.rows, s.gains, s.amp_dps, s.name, { prediction: s.prediction, state: s.state });
  } else if (S.source === "live" && S.live.steps.length) {
    rec = S.live.steps[S.stepIdx] || S.live.steps[S.live.steps.length - 1];
  }
  if (rec) {
    const sim = closedLoop(rec.t, rec.des.map((v) => v * RAD), g, pl, { w0: rec.ach[0] * RAD, i0: rec.i[0] });
    S.view = { kind: "recorded", rec, amp: rec.amp, sim, model: [...sim.t].map((t, k) => [t, sim.wf[k] * DEG]) };
  } else {
    const tgt = shapedStep({ ampDps: MODEL_AMP, dur: 0.4, pre: PRE, post: 1.0 });
    const sim = closedLoop(tgt.t, tgt.des, g, pl);
    S.view = { kind: "model", rec: null, amp: MODEL_AMP, sim, model: [...sim.t].map((t, k) => [t, sim.wf[k] * DEG]) };
  }
  const peak = Math.max(...S.view.model.map((p) => Math.abs(p[1])));
  S.view.unstable = !Number.isFinite(peak) || peak > 3 * S.view.amp;
}

// value of every wire at time t (s from the step)
function valuesAt(t) {
  const v = S.view;
  if (v.rec) {
    const r = v.rec;
    let k = 0;
    while (k < r.t.length - 1 && r.t[k + 1] <= t) k++;
    return { r: r.des[k], w: r.ach[k], e: r.des[k] - r.ach[k], p: r.p[k], i: r.i[k], d: r.d[k],
      u: r.ff[k] + r.p[k] + r.i[k] + r.d[k], ff: r.ff[k], tk: r.t[k] };
  }
  const s = v.sim, k = Math.max(0, Math.min(s.t.length - 1, Math.round((t - s.t[0]) * 400)));
  return { r: s.r[k] * DEG, w: s.wf[k] * DEG, e: (s.r[k] - s.wf[k]) * DEG, p: s.p[k], i: s.i[k], d: s.d[k], u: s.u[k],
    ff: s.u[k] - s.p[k] - s.i[k] - s.d[k], tk: s.t[k] };
}

// ---------------------------------------------------------------------------------------------------------
let stepX = null;
function renderStep() {
  const v = S.view, A = v.amp;
  const series = [];
  const tgt = v.rec ? v.rec.t.map((t, k) => [t, v.rec.des[k]]) : [...v.sim.t].map((t, k) => [t, v.sim.r[k] * DEG]);
  series.push({ pts: tgt, cls: "target" });
  series.push({ pts: v.model, cls: "model" });
  if (v.rec) series.push({ pts: v.rec.t.map((t, k) => [t, v.rec.ach[k]]), cls: "measured" });
  const marks = [];
  const all0 = series.flatMap((s) => s.pts.map((p) => p[1])).filter(Number.isFinite);
  const hi0 = Math.min(2 * A, Math.max(1.3 * A, Math.max(...all0) * 1.1));
  if (v.unstable) marks.push({ x: 1.38, y: hi0 * 0.9, r: 0.01, cls: "bad", label: "model: unstable", dx: 0, dy: 4, anchor: "end" });
  const all = series.flatMap((s) => s.pts.map((p) => p[1])).filter(Number.isFinite);
  const lo = Math.max(-2 * A, Math.min(-0.3 * A, Math.min(...all) * 1.1));
  const hi = Math.min(2 * A, Math.max(1.3 * A, Math.max(...all) * 1.1));
  const w = Math.max(300, $("#step").clientWidth || 560);
  const c = chart({
    w, h: Math.round(Math.max(260, w * 0.62)), x: [-0.1, 1.4], y: [lo, hi], yTicks: [-A, 0, A / 2, A].filter((y) => y >= lo && y <= hi), zeroLine: true,
    xTicks: [0, 0.4, 0.8, 1.2], xFmt: (t) => `${t} s`, yFmt: (y) => `${fmt(y, 0)} °/s`,
    bands: [{ x0: 0, x1: 0.4 }], vlines: [{ x: S.t, cls: "playhead", id: "ph-line" }],
    series, marks, aria: "Step response: target, model and, when recorded, the simulator's measured roll rate",
  });
  stepX = c.X;
  $("#step").innerHTML = c.svg;

  const k = (cls, text) => `<span class="k-${cls}">${text}</span>`;
  let note;
  if (v.rec) {
    const sc = score(v.rec.t, v.rec.des, v.rec.ach, 0, A);
    v.score = sc;
    const pr = v.rec.prediction;
    const same = ["P", "I", "D", "FLTD"].every((q) => Math.abs((v.rec.gains[q] ?? 0) - S.gains[q]) < 1e-6);
    note = `${k("target", "Target")} dashed, ${k("measured", "SITL measured")}, ${k("model", same ? "model at the recorded gains" : "model at the gains set here")}. ` +
      (sc ? `SITL rose 10-90 % in ${fmt(sc.rise_s * 1000, 0)} ms, peaked at ${fmt(sc.peak_dps, 0)} °/s.` : "");
    if (pr && same) note += pr.diverges ? " The model, not fitted on this step, diverges here: SITL oscillates instead." : ` Model error ${fmt(pr.rms_dps, 1)} °/s RMS${pr.fitted_on_this_step ? " (fitted on this step)" : " (not fitted on this step)"}.`;
  } else {
    const s = v.sim;
    const sc = score([...s.t], [...s.r].map((x) => x * DEG), [...s.wf].map((x) => x * DEG), 0, A);
    v.score = sc;
    note = `${k("target", "Target")} dashed: a ${A} °/s step, slewed the way ArduPilot shapes it. ${k("model", "Model")} response` +
      (sc && !v.unstable ? `: 10-90 % in ${fmt(sc.rise_s * 1000, 0)} ms, ${fmt(sc.overshoot_pct, 1)} % overshoot.` : ".");
    if (S.source === "live") note += " Run a step test to add SITL's own response.";
  }
  $("#step-note").innerHTML = note;
}

function renderBode() {
  const g = S.gains, pl = plant();
  const pts = bode(g, pl, 300), m = margins(g, pl);
  S.margins = m;
  const mag = pts.map((p) => [p.f, 20 * Math.log10(p.mag)]), ph = pts.map((p) => [p.f, p.ph * DEG]);
  const bad = m.pmDeg !== null && m.pmDeg < 0;
  const w = Math.max(300, $("#bode").clientWidth || 520);
  const top = chart({
    w, h: Math.round(Math.max(150, w * 0.34)), pad: { l: 52, r: 14, t: 10, b: 6 }, x: [0.5, 190], xLog: true, y: [-40, 40], yTicks: [-20, 0, 20], zeroLine: true,
    yFmt: (y) => `${fmt(y, 0)} dB`, series: [{ pts: mag, cls: "gain" }], aria: "Loop gain in decibels against frequency",
    marks: m.fcHz ? [{ x: m.fcHz, y: 0, label: `crossover ${fmt(m.fcHz, 1)} Hz`, dy: -9, anchor: m.fcHz > 30 ? "end" : "start", dx: m.fcHz > 30 ? -8 : 8 }] : [],
  });
  const bottom = chart({
    w, h: Math.round(Math.max(170, w * 0.4)), pad: { l: 52, r: 14, t: 6, b: 26 }, x: [0.5, 190], xLog: true, y: [-300, -60], yTicks: [-270, -180, -90],
    xTicks: [1, 10, 100], xFmt: (f) => (f === 100 ? "100 Hz" : `${f}`), yFmt: (y) => `${fmt(y, 0)}°`,
    series: [{ pts: ph, cls: "phase" }], aria: "Loop phase in degrees against frequency",
    marks: m.fcHz ? [{ x: m.fcHz, y: -180 + m.pmDeg, cls: bad ? "bad" : "", label: `${fmt(m.pmDeg, 0)}° ${m.pmDeg >= 0 ? "above" : "below"} −180°`, dy: m.pmDeg >= 0 ? -9 : 18, anchor: m.fcHz > 30 ? "end" : "start", dx: m.fcHz > 30 ? -8 : 8 }] : [],
  });
  $("#bode").innerHTML = top.svg + bottom.svg;
  const name = S.source === "model" && S.plantKey === "wisp" ? "Wisp Follow estimate" : "SITL quad, fitted";
  let bn = `Open loop: PID, motors, airframe and gyro filter (${name}: b ${Math.round(pl.b)}, delay ${(pl.td * 1000).toFixed(1)} ms, gyro ${pl.gyro_hz} Hz).`;
  const ho = S.data?.holdout?.steps?.[S.view.rec?.name];
  if (S.source === "replay" && ho && !ho.diverges) bn += ` A fit on the default step alone puts the delay at ${(S.data.holdout.plant.td * 1000).toFixed(1)} ms and these margins at ${fmt(ho.margins.pm_deg, 0)}° and ${fmt(ho.margins.gm_db, 1)} dB: samples at 100 a second pin the delay down only loosely.`;
  $("#bode-note").textContent = bn;
}

function renderMargins() {
  const m = S.margins, sc = S.view.score;
  const cls = (v, warn, bad) => (v === null ? "" : v < bad ? "bad" : v < warn ? "warn" : "");
  const item = (label, value, c = "") => `<div><dt>${label}</dt><dd class="${c}">${value}</dd></div>`;
  $("#margins").innerHTML =
    item("Phase margin", m.pmDeg === null ? "–" : `${fmt(m.pmDeg, 0)}°`, cls(m.pmDeg, 45, 0)) +
    item("Gain margin", m.gmDb === null ? "–" : `${fmt(m.gmDb, 1)} dB`, cls(m.gmDb, 6, 0)) +
    item(S.view.rec ? "SITL overshoot" : "Model overshoot", sc && !(S.view.unstable && !S.view.rec) ? `${fmt(sc.overshoot_pct, 1)} %` : "–") +
    item(S.view.rec ? "SITL rise, 10-90 %" : "Model rise, 10-90 %", sc && sc.rise_s !== null && !(S.view.unstable && !S.view.rec) ? `${fmt(sc.rise_s * 1000, 0)} ms` : "–");
}

function renderFinding() {
  const m = S.margins;
  let t;
  if (m.pmDeg === null) t = "The loop gain never reaches 1, so these gains are too low to track a step.";
  else if (m.pmDeg < 0 || (m.gmDb !== null && m.gmDb < 0))
    t = `<b>Unstable at these gains.</b> At ${fmt(m.f180Hz, 0)} Hz the loop's phase reaches −180° while its gain is still above 1, so any wobble there grows${S.view.rec?.name === "double" ? "; SITL shows it as an oscillation near 20 Hz" : ""}.`;
  else if (m.pmDeg < 15 || (m.gmDb !== null && m.gmDb < 3))
    t = `<b>Barely stable:</b> ${fmt(m.pmDeg, 0)}° phase margin and ${fmt(m.gmDb, 1)} dB gain margin. It rings for a long time, and a little more delay or a heavier battery would tip it into oscillation.`;
  else if (m.pmDeg < 45 || (m.gmDb !== null && m.gmDb < 6))
    t = `<b>Stable, close to the edge:</b> ${fmt(m.pmDeg, 0)}° phase margin and ${fmt(m.gmDb, 1)} dB gain margin, under the usual 45° and 6 dB. Expect ringing and hot motors.`;
  else t = `<b>Comfortable:</b> ${fmt(m.pmDeg, 0)}° phase margin and ${fmt(m.gmDb, 1)} dB gain margin, crossing over at ${fmt(m.fcHz, 1)} Hz.`;
  if (S.source === "model" && S.plantKey === "wisp") t += " The Wisp plant is an estimate until it is identified from flight logs.";
  $("#finding").innerHTML = t;
}

function renderPlayhead() {
  const v = valuesAt(S.t);
  $(".diagram").classList.toggle("is-model", !S.view.rec && S.source !== "live");
  setDiagram($("#diagram-host"), v, plant(), S.gains);
  const label = S.source === "live" && !S.view.rec ? "latest sample:" : `at ${fmt(v.tk * 1000, 0)} ms${S.view.rec ? ", recorded" : ", model"}:`;
  $("#eq").innerHTML = equationHTML(v, S.view.rec ? S.view.rec.gains : S.gains, label);
  $("#playhead").value = S.t;
  $("#playhead-out").textContent = `${fmt(S.t * 1000, 0)} ms`;
  const line = $("#ph-line");
  if (line && stepX) { const x = stepX(Math.max(-0.1, Math.min(1.4, S.t))).toFixed(1); line.setAttribute("x1", x); line.setAttribute("x2", x); }
  if (S.source === "replay") renderRecordedState();
}

// ---------------------------------------------------------------------------------------------------------
function readouts(items) {
  $("#readouts").innerHTML = items.map(([k, v, wide]) => `<div${wide ? ' class="wide"' : ""}><dt>${k}</dt><dd>${v}</dd></div>`).join("");
}

function ekfBars(ekf) {
  if (!ekf) { $("#ekf").innerHTML = ""; return; }
  const rows = [["Velocity", ekf.vel], ["Position", ekf.pos_h], ["Height", ekf.pos_v], ["Compass", ekf.compass]];
  $("#ekf").innerHTML = rows.map(([n, x]) => {
    const pct = Math.min(1, x / 1.5) * 100;
    return `<div class="bar${x > 1 ? " over" : ""}"><span>${n}</span><span class="track"><span class="fill" style="width:${pct.toFixed(1)}%"></span><span class="limit" style="left:${(100 / 1.5).toFixed(1)}%"></span></span><output>${x.toFixed(2)}</output></div>`;
  }).join("") + "<p>EKF (extended Kalman filter) test ratios. Past the line, 1.0, it rejects that sensor.</p>";
}

function renderRecordedState() {
  const st = S.view.rec?.state;
  if (!st || !st.length) return;
  let f = st[0];
  for (const x of st) if (x.t <= S.t) f = x;
  readouts([["Mode", f.mode.toLowerCase().replace(/^./, (c) => c.toUpperCase())], ["Height", `${fmt(f.alt, 1)}<small>m</small>`],
    ["Roll", `${fmt(f.roll, 1)}<small>°</small>`], ["Vehicle round trip", `${fmt(f.vehicle_rtt_ms, 1)}<small>ms</small>`]]);
  ekfBars(f.ekf);
}

function renderRail() {
  const note = $("#link-note");
  if (S.source === "model") {
    const pl = plant();
    $("#veh-h").textContent = "Model plant";
    readouts([["Control power b", `${Math.round(pl.b)}<small>/s²</small>`], ["Damping a", `${fmt(pl.a, 1)}<small>/s</small>`],
      ["Delay", `${fmt(pl.td * 1000, 1)}<small>ms</small>`], ["Motor lag", `${fmt(pl.tau * 1000, 1)}<small>ms</small>`]]);
    ekfBars(null);
    note.innerHTML = S.plantKey === "wisp"
      ? "<b>Wisp Follow, placeholder.</b> UNCONFIRMED numbers carried over from the Phase 0 concept model, not derived from the parts or measured; Phase 3 replaces them with a fit to real logs."
      : `<b>SITL quad, fitted</b> (ESTIMATE) from the recorded default and half-gain steps (r² ${S.data ? S.data.plant.r2.toFixed(4) : "–"}).`;
  } else if (S.source === "replay") {
    $("#veh-h").textContent = "Vehicle, recorded";
    const L = S.data?.latency || {};
    note.innerHTML = S.data
      ? `<b>Recorded</b> from ArduCopter 4.7.2 SITL (software in the loop) through the Wisp bridge. Vehicle round trip ${fmt(L.vehicle_rtt_ms, 1)} ms, app round trip ${fmt(L.app_rtt_ms, 1)} ms.`
      : "Loading the recording…";
    renderRecordedState();
  } else {
    $("#veh-h").textContent = "Vehicle, live";
    renderLiveState();
  }
  const live = S.source === "live" && S.live.connected;
  for (const b of $$("#actions button")) b.disabled = !live;
  $("#amp").disabled = !live;
  $("#send").disabled = !live;
  $("#actions").hidden = S.source !== "live";
}

function renderLiveState() {
  const L = S.live, s = L.state, note = $("#link-note");
  if (!L.connected) {
    note.innerHTML = `<b>No bridge</b> at <code>${bridgeURL}</code>. Start one on this computer, retrying every 3 s:<br><code>python3 -m wisp_gcs.bridge --sitl ~/ardupilot</code>`;
    readouts([["Link", "waiting", true]]);
    ekfBars(null);
    return;
  }
  const vr = s?.latency?.vehicle_rtt_ms, ar = L.appRtt, held = s?.att_age_ms;
  const age = [vr, ar, held].every((x) => x !== null && x !== undefined) ? held + (vr + ar) / 2 : null;
  note.innerHTML = `<b>Live</b> on <code>${bridgeURL}</code>. Attitude on screen is about <b>${fmt(age, 0)} ms</b> old: ${fmt(held, 0)} ms waiting in the bridge, plus half the vehicle round trip (${fmt(vr, 1)} ms) and half the app round trip (${fmt(ar, 1)} ms).`;
  if (!s) return;
  const mode = s.mode.toLowerCase().replace(/^./, (c) => c.toUpperCase()).replace("_", " ");
  readouts([["Mode", `${mode}${s.armed ? "" : "<small>disarmed</small>"}`], ["Height", `${fmt(s.alt_rel, 1)}<small>m</small>`],
    ["Battery", s.batt ? `${fmt(s.batt.v, 1)}<small>V</small>` : "–"], ["GPS", s.gps ? `${s.gps.sats}<small>sats</small>` : "–"],
    ["Roll", `${fmt(s.att.roll, 1)}<small>°</small>`], ["Heartbeat", `${fmt(s.heartbeat_age, 1)}<small>s ago</small>`]]);
  ekfBars(s.ekf);
}

function renderPicker() {
  const host = $("#picker");
  let items = [];
  if (S.source === "replay" && S.data) items = S.data.steps.map((s) => ({ "default": "Default gains", half: "Half gains", double: "Double gains" }[s.name] || s.name));
  if (S.source === "live") items = S.live.steps.map((s, k) => `Step ${k + 1}, ${s.amp} °/s`);
  host.innerHTML = items.map((t, k) => `<button aria-pressed="${k === S.stepIdx}" data-k="${k}">${t}</button>`).join("");
  host.setAttribute("aria-label", "Recorded steps");
}

function syncGainInputs() {
  for (const q of ["P", "I", "D", "FLTD"]) {
    $(`#g-${q}`).value = S.gains[q];
    $(`#o-${q}`).textContent = q === "FLTD" ? `${S.gains[q]} Hz` : S.gains[q].toFixed(q === "D" ? 4 : 3);
  }
  const pk = S.plantKey, model = S.source === "model";
  const gh = model ? S.gyro[pk] : S.sitlPlant.gyro_hz;
  $("#g-gyro").value = gh;
  $("#o-gyro").textContent = `${gh} Hz`;
  $("#g-gyro").disabled = !model;
  $("#gyro-row").classList.toggle("off", !model);
  $("#plant-pick").hidden = !model;
  $("#plant-pick").innerHTML = model
    ? [["sitl", "SITL quad"], ["wisp", "Wisp estimate"]].map(([k, t]) => `<button role="radio" aria-checked="${k === pk}" data-plant="${k}">${t}</button>`).join("")
    : "";
  $("#send").hidden = S.source !== "live";
}

function renderAll() {
  buildView();
  renderStep();
  renderBode();
  renderMargins();
  renderFinding();
  renderPicker();
  syncGainInputs();
  renderRail();
  $("#scrub").hidden = !S.view.rec && S.source === "live";
  $("#strip").classList.toggle("on", S.source === "live");
  renderPlayhead();
}

// ---------------------------------------------------------------------------------------------------------
function setSource(src) {
  S.source = src;
  S.playing = false;
  S.stepIdx = 0;
  for (const b of $$(".seg button")) b.setAttribute("aria-checked", String(b.dataset.source === src));
  if (src === "replay" && S.data) S.gains = { ...ARDU_DEFAULTS, ...S.data.steps[0].gains };
  if (src === "live") connect(); else disconnect();
  try { history.replaceState(null, "", `?source=${src}`); } catch { /* file:// */ }
  renderAll();
}

function connect() {
  const L = S.live;
  if (L.ws) return;
  let ws;
  try { ws = new WebSocket(bridgeURL); } catch { scheduleRetry(); return; }
  L.ws = ws;
  ws.onopen = () => {
    L.connected = true;
    const ping = () => ws.send(JSON.stringify({ cmd: "ping", t: performance.now() }));
    ping();
    L.ping = setInterval(ping, 2000);
    ws.send(JSON.stringify({ cmd: "pid_axis", axis: "roll" }));
    renderRail();
  };
  ws.onmessage = (ev) => onFrame(JSON.parse(ev.data));
  ws.onclose = () => {
    clearInterval(L.ping);
    const was = L.connected;
    L.ws = null; L.connected = false;
    if (S.source === "live") { if (was) log("Bridge disconnected.", true); scheduleRetry(); renderRail(); }
  };
}
function scheduleRetry() { clearTimeout(S.live.retry); S.live.retry = setTimeout(() => S.source === "live" && connect(), 3000); }
function disconnect() { const L = S.live; clearTimeout(L.retry); if (L.ws) { L.ws.onclose = null; L.ws.close(); } L.ws = null; L.connected = false; clearInterval(L.ping); }

let railDue = 0;
function onFrame(f) {
  const L = S.live;
  switch (f.type) {
    case "hello":
    case "params": {
      const vals = f.params || f.values || {};
      Object.assign(L.params, vals);
      const map = { P: "ATC_RAT_RLL_P", I: "ATC_RAT_RLL_I", D: "ATC_RAT_RLL_D", FLTD: "ATC_RAT_RLL_FLTD" };
      for (const [k, n] of Object.entries(map)) if (vals[n] !== undefined && vals[n] !== null) S.gains[k] = +(+vals[n]).toFixed(6);
      renderAll();
      break;
    }
    case "state":
      L.state = f;
      if (performance.now() > railDue) { railDue = performance.now() + 100; renderLiveState(); }
      break;
    case "pid":
      for (const r of f.rows) if (r[1] === "roll") L.ring.push([r[0], r[2], r[3], r[4], r[5], r[6], r[7]]);
      if (L.ring.length > 1200) L.ring.splice(0, L.ring.length - 1200);
      break;
    case "step_start":
      L.pending = f;
      log(`Step test running: ${f.amp} °/s on ${f.axis}.`);
      break;
    case "step_end":
      setTimeout(() => finishLiveStep(f), (POST - 0.9) * 1000);
      break;
    case "result":
      log(f.text, !f.ok);
      if (f.name && f.value !== undefined && f.value !== null) L.params[f.name] = f.value;
      break;
    case "event":
      log(`Vehicle: ${f.text}`, f.level === "warn");
      break;
    case "pong":
      L.appRtt = performance.now() - f.t;
      break;
  }
}

function finishLiveStep(end) {
  const L = S.live, st = L.pending;
  if (!st) return;
  L.pending = null;
  const rows = L.ring.filter((r) => r[0] >= st.t_step - PRE && r[0] <= st.t_step + POST).map((r) => [r[0] - st.t_step, ...r.slice(1)]);
  if (rows.length < 20) { log("Too few samples from that step to plot.", true); return; }
  const gk = { P: "ATC_RAT_RLL_P", I: "ATC_RAT_RLL_I", D: "ATC_RAT_RLL_D", FF: "ATC_RAT_RLL_FF", FLTD: "ATC_RAT_RLL_FLTD" };
  const gains = Object.fromEntries(Object.entries(gk).map(([k, n]) => [k, st.gains?.[n] ?? S.gains[k] ?? 0]));
  L.steps.push(stepFromRows(rows, gains, st.amp, `live-${L.steps.length + 1}`));
  S.stepIdx = L.steps.length - 1;
  S.t = 0.05;
  renderAll();
}

function send(cmd) {
  const L = S.live;
  if (!L.ws || L.ws.readyState !== 1) { log("Not connected to a bridge.", true); return; }
  L.ws.send(JSON.stringify(cmd));
}

function log(text, bad = false) {
  const el = $("#log");
  el.textContent = text;
  el.classList.toggle("bad", bad);
}

// ---------------------------------------------------------------------------------------------------------
let last = 0;
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  if (S.playing) {
    S.t += dt * ($("#slow").checked ? 0.25 : 1);
    if (S.t >= POST) { S.t = POST; S.playing = false; $("#play").textContent = "Play"; }
    renderPlayhead();
  } else if (S.source === "live" && !S.view?.rec && S.live.ring.length) {
    const r = S.live.ring[S.live.ring.length - 1];
    const v = { r: r[1], w: r[2], e: r[1] - r[2], p: r[4], i: r[5], d: r[6], u: r[3] + r[4] + r[5] + r[6], ff: r[3], tk: 0 };
    setDiagram($("#diagram-host"), v, plant(), S.gains);
    $("#eq").innerHTML = equationHTML(v, S.gains, "latest sample:");
  }
  if (S.source === "live") drawStrip();
  requestAnimationFrame(frame);
}

function drawStrip() {
  const cv = $("#strip"), ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height, ring = S.live.ring;
  ctx.clearRect(0, 0, W, H);
  const css = getComputedStyle(document.documentElement);
  ctx.font = '22px "Overpass", system-ui, sans-serif';
  ctx.fillStyle = css.getPropertyValue("--muted");
  if (!ring.length) { ctx.fillText("Waiting for rate-loop samples", 16, H / 2); return; }
  const tEnd = ring[ring.length - 1][0], t0 = tEnd - 4;
  const ys = ring.filter((r) => r[0] >= t0).flatMap((r) => [r[1], r[2]]);
  const span = Math.max(30, ...ys.map(Math.abs)) * 1.15;
  const X = (t) => ((t - t0) / 4) * W, Y = (v) => H / 2 - (v / span) * (H / 2 - 8);
  ctx.strokeStyle = css.getPropertyValue("--line"); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(W, Y(0)); ctx.stroke();
  const line = (idx, color, dash, width) => {
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash); ctx.beginPath();
    let first = true;
    for (const r of ring) { if (r[0] < t0) continue; const x = X(r[0]), y = Y(r[idx]); if (first) { ctx.moveTo(x, y); first = false; } else ctx.lineTo(x, y); }
    ctx.stroke(); ctx.setLineDash([]);
  };
  line(1, css.getPropertyValue("--ink"), [10, 8], 3);
  line(2, css.getPropertyValue("--wisp"), [], 4.5);
  ctx.fillStyle = css.getPropertyValue("--muted");
  ctx.fillText(`last 4 s, ±${Math.round(span)} °/s`, 12, 26);
}

// ---------------------------------------------------------------------------------------------------------
function wire() {
  $("#diagram-host").innerHTML = diagramSVG();
  for (const b of $$(".seg button")) b.addEventListener("click", () => setSource(b.dataset.source));
  $("#picker").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    S.stepIdx = +b.dataset.k;
    const rec = S.source === "replay" ? S.data.steps[S.stepIdx] : S.live.steps[S.stepIdx];
    if (rec) S.gains = { ...S.gains, ...rec.gains };
    S.t = 0.05; S.playing = false; $("#play").textContent = "Play";
    renderAll();
  });
  $("#plant-pick").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    S.plantKey = b.dataset.plant; renderAll();
  });
  for (const q of ["P", "I", "D", "FLTD"]) {
    $(`#g-${q}`).addEventListener("input", (e) => { S.gains[q] = +e.target.value; renderAll(); });
  }
  $("#g-gyro").addEventListener("input", (e) => { S.gyro[S.plantKey] = +e.target.value; renderAll(); });
  $("#reset").addEventListener("click", () => { S.gains = { ...ARDU_DEFAULTS }; renderAll(); });
  $("#send").addEventListener("click", () => {
    const names = { P: "ATC_RAT_RLL_P", I: "ATC_RAT_RLL_I", D: "ATC_RAT_RLL_D", FLTD: "ATC_RAT_RLL_FLTD" };
    for (const [k, n] of Object.entries(names)) send({ cmd: "set_param", name: n, value: S.gains[k] });
  });
  $("#playhead").addEventListener("input", (e) => { S.t = +e.target.value; S.playing = false; $("#play").textContent = "Play"; renderPlayhead(); });
  $("#play").addEventListener("click", () => {
    if (S.playing) { S.playing = false; $("#play").textContent = "Play"; return; }
    if (S.t >= POST - 0.01) S.t = -PRE;
    S.playing = true; $("#play").textContent = "Pause";
  });
  for (const b of $$("#actions button")) {
    b.addEventListener("click", () => {
      const c = b.dataset.cmd;
      if (c === "takeoff") send({ cmd: "takeoff", alt: 10 });
      else if (c === "step") send({ cmd: "step", axis: "roll", amp: +$("#amp").value, dur: 0.4 });
      else send({ cmd: c });
    });
  }
  addEventListener("keydown", (e) => {          // Escape always stops, wherever focus is
    if (e.key === "Escape" && S.source === "live" && S.live.connected) { send({ cmd: "stop" }); log("Stop sent."); }
  });
}

async function start() {
  wire();
  let due = false;
  new ResizeObserver(() => {
    if (due || !S.view) return;
    due = true;
    requestAnimationFrame(() => { due = false; renderStep(); renderBode(); renderPlayhead(); });
  }).observe($(".grid"));
  const q = new URLSearchParams(location.search).get("source");
  const served = /^(127\.0\.0\.1|localhost)$/.test(location.hostname) && location.port === String(BRIDGE_PORT);
  setSource(q || (served ? "live" : "replay"));
  try {
    const r = await fetch("data/sitl-roll-steps.json");
    S.data = await r.json();
    S.sitlPlant = { b: S.data.plant.b, a: S.data.plant.a, tau: S.data.plant.tau, td: S.data.plant.td, gyro_hz: S.data.plant.gyro_hz };
    if (S.source === "replay") S.gains = { ...ARDU_DEFAULTS, ...S.data.steps[0].gains };
  } catch {
    log("Could not load the recorded SITL steps; showing the model only.", true);
  }
  renderAll();
  requestAnimationFrame((t) => { last = t; frame(t); });
}

start();
