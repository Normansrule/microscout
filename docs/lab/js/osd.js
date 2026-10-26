// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// On-screen display (OSD) for the FPV view: the flight data a pilot would see over the camera picture.
// Drawn on a 2D canvas laid over the 4:3 picture. The artificial horizon uses the camera geometry from
// render.js (FPV), so it lies on the real horizon of the simulated room.

import { qrot, mulRv, mulRTv } from "./math.js";
import { FPV } from "./render.js";

const D2R = Math.PI / 180;

export function drawOSD(canvas, rect, info) {
  const dpr = Math.min(2, devicePixelRatio || 1);
  const W = canvas.clientWidth, H = canvas.clientHeight;
  if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
  const c = canvas.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, W, H);
  if (!info) return;
  const { quad, mode, armed, warnings = [], throttle = 0, radioDown = false } = info;
  const { x, y, w, h } = rect;
  const s = Math.max(0.7, Math.min(1.4, h / 420));          // text scale with the picture size
  const fs = Math.round(15 * s);
  c.save();
  c.beginPath(); c.rect(x, y, w, h); c.clip();
  c.lineJoin = "round";
  // White glyphs with a dark outline, as on an analogue OSD chip: readable over any background.
  const text = (t, tx, ty, align = "left", size = fs, color = "#fff") => {
    c.font = `700 ${size}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`;
    c.textAlign = align; c.textBaseline = "middle";
    c.lineWidth = Math.max(2, size / 5); c.strokeStyle = "rgba(0,0,0,0.85)"; c.strokeText(t, tx, ty);
    c.fillStyle = color; c.fillText(t, tx, ty);
  };
  const line = (pts, color = "#fff", lw = 2) => {
    c.beginPath(); pts.forEach(([px, py], i) => (i ? c.lineTo(px, py) : c.moveTo(px, py)));
    c.lineWidth = lw + 2.5; c.strokeStyle = "rgba(0,0,0,0.75)"; c.stroke();
    c.lineWidth = lw; c.strokeStyle = color; c.stroke();
  };
  const cx = x + w / 2, cy = y + h / 2;

  // artificial horizon and pitch ladder: world directions at elevation e (and azimuths around where the camera
  // looks) projected through the camera exactly, so roll, pitch and the uptilt combine correctly at any attitude.
  // Camera axes in the body frame (FRD): forward (cos a, 0, -sin a), right (0, 1, 0), down (sin a, 0, cos a).
  const R = qrot(info.att || quad.q);
  const ua = FPV.uptiltDeg * D2R, f = h / 2 / Math.tan((FPV.vFovDeg / 2) * D2R);
  const cf = [Math.cos(ua), 0, -Math.sin(ua)], cr = [0, 1, 0], cd = [Math.sin(ua), 0, Math.cos(ua)];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const project = (dw) => {                          // world direction -> picture point, or null if behind
    const b = mulRTv(R, dw), zf = dot(b, cf);
    return zf > 0.05 ? [cx + (f * dot(b, cr)) / zf, cy + (f * dot(b, cd)) / zf] : null;
  };
  const fw = mulRv(R, cf), psi = Math.atan2(fw[1], fw[0]);     // azimuth the camera looks along
  const dirAt = (e, az) => [Math.cos(e) * Math.cos(psi + az), Math.cos(e) * Math.sin(psi + az), -Math.sin(e)];
  const seg = (e, a0, a1, color, lw) => {
    const n = 8, pts = [];
    for (let i = 0; i <= n; i++) { const p = project(dirAt(e, a0 + ((a1 - a0) * i) / n)); if (p) pts.push(p); }
    if (pts.length > 1) line(pts, color, lw);
    return pts;
  };
  seg(0, -28 * D2R, -4 * D2R, "#fff", 2);
  seg(0, 4 * D2R, 28 * D2R, "#fff", 2);
  for (const deg of [-20, -10, 10, 20]) {
    const e = deg * D2R;
    seg(e, -10 * D2R, -3 * D2R, "rgba(255,255,255,0.75)", 1.2);
    const right = seg(e, 3 * D2R, 10 * D2R, "rgba(255,255,255,0.75)", 1.2);
    if (right.length) { const [tx, ty] = right[right.length - 1]; text(String(deg), tx + 16 * s, ty, "center", Math.round(fs * 0.7)); }
  }
  // crosshair (where the camera points, not where the drone flies)
  line([[cx - 9 * s, cy], [cx + 9 * s, cy]], "#fff", 1.6);
  line([[cx, cy - 6 * s], [cx, cy + 6 * s]], "#fff", 1.6);

  // corners
  const m = 12 * s, row = fs * 1.35;
  const v = quad.bat.voltage, cells = 2;
  const low = v / cells < 3.5;
  text(`${v.toFixed(2)}V`, x + m, y + m + row * 0.4, "left", fs, low ? "#ff6b5e" : "#fff");
  text(`${(v / cells).toFixed(2)}V/c`, x + m, y + m + row * 1.4, "left", Math.round(fs * 0.85), low ? "#ff6b5e" : "#fff");
  text(`${quad.bat.current.toFixed(1)}A`, x + m, y + m + row * 2.4, "left", fs, quad.limiting ? "#ffc34d" : "#fff");
  text(`${Math.round(quad.usedMah)}mAh`, x + m, y + m + row * 3.4, "left", Math.round(fs * 0.85));
  const mm = Math.floor(quad.t / 60), ss = Math.floor(quad.t % 60);
  const ry = y + Math.max(m, 58 - y);          // right column starts below the view buttons
  text(`${mm}:${String(ss).padStart(2, "0")}`, x + w - m, ry + row * 0.4, "right");
  text(armed ? mode.toUpperCase() : "DISARMED", x + w - m, ry + row * 1.4, "right", Math.round(fs * 0.85), armed ? "#fff" : "#ffc34d");
  text(`THR ${Math.round(throttle * 100)}%`, x + w - m, ry + row * 2.4, "right", Math.round(fs * 0.85));
  const spd = Math.hypot(quad.vel[0], quad.vel[1], quad.vel[2]);
  text(`${quad.height.toFixed(1)}m`, x + m, y + h - m - row * 0.4, "left");
  text(`${spd.toFixed(1)}m/s`, x + w - m, y + h - m - row * 0.4, "right");

  // warnings, most serious first
  const warn = [];
  if (quad.cutoff) warn.push("POWER CUT");
  if (radioDown) warn.push("RX LOSS");
  if (low && !quad.cutoff) warn.push("LOW BATTERY");
  if (quad.limiting) warn.push("CURRENT LIMIT");
  warn.push(...warnings);
  warn.slice(0, 2).forEach((t, i) => text(t, cx, y + h * 0.68 + i * row, "center", Math.round(fs * 1.1), i === 0 && (quad.cutoff || radioDown) ? "#ff6b5e" : "#ffc34d"));
  c.restore();
}
