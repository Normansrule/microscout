// SPDX-License-Identifier: MIT
// The rate loop as a block diagram whose wires carry the current numbers: target, error, the three PID terms,
// the command u, and the measured rate coming back through the gyro filter.

import { fmt } from "./chart.js";

const W = 1000, H = 172;

export function diagramSVG() {
  const box = (x, w, t1, t2, id) => `<g><rect x="${x}" y="40" width="${w}" height="58" rx="6" class="blk"/>
    <text x="${x + w / 2}" y="64" text-anchor="middle" class="blk-t">${t1}</text>
    <text x="${x + w / 2}" y="84" text-anchor="middle" class="blk-s"${id ? ` id="${id}"` : ""}>${t2}</text></g>`;
  const wire = (x1, x2, id, cls = "") => `<path d="M${x1} 69 H${x2 - 8}" class="wire ${cls}"/><path d="M${x2 - 9} 63 L${x2} 69 L${x2 - 9} 75 Z" class="head ${cls}"/>` +
    (id ? `<text x="${(x1 + x2) / 2}" y="56" text-anchor="middle" class="val ${cls}" id="${id}"></text>` : "");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="diag-title" id="diag">
    <title id="diag-title">Rate loop block diagram with the current values on each wire</title>
    <text x="0" y="73" class="blk-s">target</text>
    ${wire(48, 150, "v-r")}
    <circle cx="164" cy="69" r="14" class="blk"/><text x="164" y="75" text-anchor="middle" class="blk-t">Σ</text>
    <text x="146" y="100" class="blk-s">−</text>
    ${wire(178, 290, "v-e")}
    ${box(290, 200, "PID controller", "P + I + D", "v-terms")}
    ${wire(490, 590, "v-u", "wisp")}
    ${box(590, 150, "Motors", "delay, lag", "v-motor")}
    ${wire(740, 800, "")}
    ${box(800, 130, "Airframe", "b / (s + a)", "v-air")}
    ${wire(930, 1000, "v-w", "wisp")}
    <path d="M968 69 V138 H164 V91" class="wire air"/><path d="M158 92 L164 83 L170 92 Z" class="head air"/>
    <text x="566" y="132" text-anchor="middle" class="val air" id="v-m"></text>
    <text x="566" y="160" text-anchor="middle" class="blk-s" id="v-gyro">gyro filter</text>
  </svg>`;
}

/** Fill the diagram's numbers. v: {r, w, e, p, i, d, u} with rates in deg/s; plant and gains for labels. */
export function setDiagram(root, v, plant, gains) {
  const set = (id, text) => { const el = root.querySelector("#" + id); if (el && el.textContent !== text) el.textContent = text; };
  set("v-r", `${fmt(v.r)} °/s`);
  set("v-e", `e = ${fmt(v.e)} °/s`);
  set("v-terms", `${fmt(v.p, 3)} + ${fmt(v.i, 3)} + ${fmt(v.d, 3)}`);
  set("v-u", `u = ${fmt(v.u, 3)}`);
  set("v-w", `${fmt(v.w)} °/s`);
  set("v-m", `measured ${fmt(v.w)} °/s`);
  if (plant) {
    set("v-motor", `${(plant.td * 1000).toFixed(1)} ms, τ ${(plant.tau * 1000).toFixed(1)} ms`);
    set("v-air", `${Math.round(plant.b)} / (s + ${plant.a.toFixed(1)})`);
    set("v-gyro", `gyro filter, ${plant.gyro_hz} Hz low-pass`);
  }
}

/** The PID equation with this instant's numbers substituted. */
export function equationHTML(v, g, label) {
  const e = v.e * Math.PI / 180;
  return `<span class="eq-sym">u = P × e + I + D</span>` +
    `<span class="eq-at">${label}</span>` +
    `<span class="eq-num">${g.P.toFixed(3)} × ${fmt(e, 3)} rad/s + ${fmt(v.i, 3)} + ${fmt(v.d, 3)}${Math.abs(v.ff || 0) > 5e-4 ? ` + FF ${fmt(v.ff, 3)}` : ""} = <b>${fmt(v.u, 3)}</b></span>`;
}
