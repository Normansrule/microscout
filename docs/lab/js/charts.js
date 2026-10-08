// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// A small canvas line chart (learning curves, telemetry). Colours come from CSS variables.

const css = (n, f) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f;

/** Round tick values (1, 2, 5 x 10^n) covering [a, b] with about n steps. */
function ticks(a, b, n = 4) {
  const raw = (b - a) / n, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const out = [];
  for (let v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}

export function lineChart(canvas, series, opts = {}) {
  const dpr = Math.min(2, devicePixelRatio || 1);
  const W = canvas.clientWidth, H = canvas.clientHeight;
  if (canvas.width !== W * dpr) { canvas.width = W * dpr; canvas.height = H * dpr; }
  const c = canvas.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, W, H);
  const pad = { l: 40, r: 10, t: 10, b: 22 };
  const all = series.flatMap((s) => s.points.map((p) => p[1]).concat(s.band ? s.band.flatMap((b) => [b[1], b[2]]) : []));
  const xs = series.flatMap((s) => s.points.map((p) => p[0]));
  if (!all.length) {
    c.fillStyle = css("--muted", "#5c6773"); c.font = "13px Archivo, sans-serif";
    c.fillText(opts.empty || "No data yet", pad.l, H / 2);
    return;
  }
  let y0 = Math.min(...all), y1 = Math.max(...all);
  if (y1 - y0 < 1e-6) { y0 -= 1; y1 += 1; }
  const yt = ticks(y0, y1); const st = yt.length > 1 ? yt[1] - yt[0] : 1;
  y0 = Math.min(y0, Math.floor(y0 / st) * st); y1 = Math.max(y1, Math.ceil(y1 / st) * st);
  const x0 = Math.min(...xs), x1 = Math.max(x0 + 1, ...xs);
  const X = (x) => pad.l + ((x - x0) / (x1 - x0)) * (W - pad.l - pad.r);
  const Y = (y) => H - pad.b - ((y - y0) / (y1 - y0)) * (H - pad.t - pad.b);
  c.strokeStyle = css("--line", "#cdd3d9"); c.lineWidth = 1;
  c.fillStyle = css("--muted", "#5c6773"); c.font = "11px Archivo, sans-serif";
  for (const v of ticks(y0, y1)) {
    const y = Y(v);
    c.beginPath(); c.moveTo(pad.l, y); c.lineTo(W - pad.r, y); c.stroke();
    const t = String(v); c.fillText(t, pad.l - 6 - c.measureText(t).width, y + 4);
  }
  const xl = opts.xlabel || "", xlw = c.measureText(xl).width;
  for (const v of ticks(x0, x1, 4).filter(Number.isInteger)) {
    const x = X(v), t = String(v), w = c.measureText(t).width;
    if (x + w / 2 < W - pad.r - xlw - 8) c.fillText(t, x - w / 2, H - 6);
  }
  c.fillText(xl, W - pad.r - xlw, H - 6);
  if (y0 < 0 && y1 > 0) { c.strokeStyle = css("--muted", "#5c6773"); c.setLineDash([3, 3]); c.beginPath(); c.moveTo(pad.l, Y(0)); c.lineTo(W - pad.r, Y(0)); c.stroke(); c.setLineDash([]); }
  for (const s of series) {
    if (s.band) {
      c.fillStyle = s.color; c.globalAlpha = 0.14; c.beginPath();
      s.band.forEach((b, i) => (i ? c.lineTo(X(b[0]), Y(b[2])) : c.moveTo(X(b[0]), Y(b[2]))));
      [...s.band].reverse().forEach((b) => c.lineTo(X(b[0]), Y(b[1])));
      c.closePath(); c.fill(); c.globalAlpha = 1;
    }
    c.strokeStyle = s.color; c.lineWidth = s.width || 2; c.setLineDash(s.dash || []);
    c.beginPath();
    s.points.forEach((p, i) => (i ? c.lineTo(X(p[0]), Y(p[1])) : c.moveTo(X(p[0]), Y(p[1]))));
    c.stroke(); c.setLineDash([]);
    if (s.dots && s.points.length < 60) { c.fillStyle = s.color; for (const p of s.points) { c.beginPath(); c.arc(X(p[0]), Y(p[1]), 2.2, 0, 7); c.fill(); } }
  }
}
