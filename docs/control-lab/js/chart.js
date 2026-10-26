// SPDX-License-Identifier: MIT
// Small SVG charts for the Control Lab: few gridlines, no legend box, every line labelled where it ends.

export function chart(o) {
  const { w, h, pad = { l: 46, r: 14, t: 10, b: 26 }, xLog = false } = o;
  const [x0, x1] = o.x, [y0, y1] = o.y;
  const fx = xLog ? (x) => (Math.log10(x) - Math.log10(x0)) / (Math.log10(x1) - Math.log10(x0)) : (x) => (x - x0) / (x1 - x0);
  const X = (x) => pad.l + fx(x) * (w - pad.l - pad.r);
  const Y = (y) => pad.t + (1 - (y - y0) / (y1 - y0)) * (h - pad.t - pad.b);
  const g = [];
  for (const t of o.yTicks || []) {
    g.push(`<line x1="${pad.l}" x2="${w - pad.r}" y1="${Y(t).toFixed(1)}" y2="${Y(t).toFixed(1)}" class="${t === 0 && o.zeroLine ? "zero" : "grid"}"/>`);
    g.push(`<text x="${pad.l - 6}" y="${(Y(t) + 4).toFixed(1)}" text-anchor="end">${o.yFmt ? o.yFmt(t) : t}</text>`);
  }
  for (const t of o.xTicks || []) g.push(`<text x="${X(t).toFixed(1)}" y="${h - 7}" text-anchor="middle">${o.xFmt ? o.xFmt(t) : t}</text>`);
  for (const b of o.bands || []) {
    g.push(`<rect x="${X(b.x0).toFixed(1)}" y="${pad.t}" width="${(X(b.x1) - X(b.x0)).toFixed(1)}" height="${h - pad.t - pad.b}" class="band"/>`);
  }
  for (const v of o.vlines || []) g.push(`<line x1="${X(v.x).toFixed(1)}" x2="${X(v.x).toFixed(1)}" y1="${pad.t}" y2="${h - pad.b}" class="${v.cls || "vline"}"${v.id ? ` id="${v.id}"` : ""}/>`);
  for (const s of o.series) {
    let d = "", pen = false;                       // points outside the y range lift the pen instead of clamping
    for (const p of s.pts) {
      if (!Number.isFinite(p[1]) || p[0] < x0 || p[0] > x1 || p[1] < y0 || p[1] > y1) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; pen = true;
    }
    g.push(`<path d="${d}" class="${s.cls}" fill="none"/>`);
    if (s.label && s.labelAt) {
      const [lx, ly] = s.labelAt;
      g.push(`<text x="${X(lx).toFixed(1)}" y="${Y(ly).toFixed(1)}" class="lbl ${s.cls}" text-anchor="${s.anchor || "start"}">${s.label}</text>`);
    }
  }
  for (const m of o.marks || []) {
    g.push(`<circle cx="${X(m.x).toFixed(1)}" cy="${Y(m.y).toFixed(1)}" r="${m.r || 3.5}" class="mark ${m.cls || ""}"/>`);
    if (m.label) g.push(`<text x="${(X(m.x) + (m.dx ?? 8)).toFixed(1)}" y="${(Y(m.y) + (m.dy ?? -8)).toFixed(1)}" class="lbl ${m.cls || ""}" text-anchor="${m.anchor || "start"}">${m.label}</text>`);
  }
  return { svg: `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${o.aria || "chart"}">${g.join("")}</svg>`, X, Y };
}

export const minus = (s) => String(s).replace(/^-/, "−");
export const fmt = (v, d = 1) => {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  const s = v.toFixed(d);
  return /^-0(\.0*)?$/.test(s) ? s.slice(1) : minus(s);       // no "−0.0"
};
