// SPDX-License-Identifier: MIT
// Small SVG chart for the Control Lab mockups: few gridlines, no chart chrome, marks labelled in place.

export function chart(o) {
  const { w, h, pad = { l: 40, r: 12, t: 10, b: 24 }, xLog = false } = o;
  const [x0, x1] = o.x, [y0, y1] = o.y;
  const fx = xLog ? (x) => (Math.log10(x) - Math.log10(x0)) / (Math.log10(x1) - Math.log10(x0)) : (x) => (x - x0) / (x1 - x0);
  const X = (x) => pad.l + fx(x) * (w - pad.l - pad.r);
  const Y = (y) => pad.t + (1 - (y - y0) / (y1 - y0)) * (h - pad.t - pad.b);
  const g = [];
  for (const t of o.yTicks || []) {
    g.push(`<line x1="${pad.l}" x2="${w - pad.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="${o.grid}" stroke-width="1"/>`);
    g.push(`<text x="${pad.l - 6}" y="${Y(t) + 4}" text-anchor="end">${o.yFmt ? o.yFmt(t) : t}</text>`);
  }
  for (const t of o.xTicks || []) g.push(`<text x="${X(t)}" y="${h - 6}" text-anchor="middle">${o.xFmt ? o.xFmt(t) : t}</text>`);
  if (o.xLabel) g.push(`<text x="${w - pad.r}" y="${h - 6}" text-anchor="end">${o.xLabel}</text>`);
  for (const s of o.series) {
    let d = "", pen = false;                       // points outside the y range lift the pen instead of clamping
    for (const p of s.pts) {
      if (p[0] < x0 || p[0] > x1 || p[1] < y0 || p[1] > y1) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)} `; pen = true;
    }
    g.push(`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""} stroke-linejoin="round"/>`);
  }
  for (const m of o.marks || []) {
    g.push(`<circle cx="${X(m.x)}" cy="${Y(m.y)}" r="${m.r || 4}" fill="${m.color}"/>`);
    if (m.label) g.push(`<text x="${X(m.x) + (m.dx ?? 8)}" y="${Y(m.y) + (m.dy ?? -8)}" class="mk" style="fill:${m.color}" text-anchor="${m.anchor || "start"}">${m.label}</text>`);
  }
  for (const v of o.vlines || []) g.push(`<line x1="${X(v.x)}" x2="${X(v.x)}" y1="${pad.t}" y2="${h - pad.b}" stroke="${v.color}" stroke-dasharray="3 3"/>`);
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${o.aria || "chart"}">${g.join("")}</svg>`;
}
