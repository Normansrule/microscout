# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Measures the copper actually drawn on the high-current paths of the routed boards and appends it to
review/G3/trace-widths.md. Run after the board scripts: python3 tools/pcb/copper.py

Method (per copper layer): take the path net's own copper (filled zones, tracks, pads) and find the widest
"pipe" that still joins pad A to pad B: the largest w for which the copper shrunk by w/2 still has one piece
reaching within w/2 of both pads (a binary search on w). That w is the narrowest point of the best route on that
layer, whatever shape the route takes. 0 means the layer has no continuous copper between the pads on its own.
Vias joining the layers are not modelled.
"""
import math
import pathlib

import pcbnew
import shapely
from shapely.geometry import LineString, Point, Polygon

REPO = pathlib.Path(__file__).resolve().parents[2]
MM = pcbnew.ToMM


def copper(b, net, layer):
    geoms = []
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != net or not z.IsOnLayer(layer):
            continue
        f = z.GetFilledPolysList(layer)
        for i in range(f.OutlineCount()):
            o = f.Outline(i)
            pts = [(MM(o.CPoint(k).x), MM(o.CPoint(k).y)) for k in range(o.PointCount())]
            holes = [[(MM(f.Hole(i, h).CPoint(k).x), MM(f.Hole(i, h).CPoint(k).y)) for k in range(f.Hole(i, h).PointCount())]
                     for h in range(f.HoleCount(i))]
            if len(pts) > 2:
                geoms.append(Polygon(pts, holes).buffer(0))
    for t in b.GetTracks():
        if t.GetNetname() == net and t.GetClass() != "PCB_VIA" and t.GetLayer() == layer:
            geoms.append(LineString([(MM(t.GetStart().x), MM(t.GetStart().y)), (MM(t.GetEnd().x), MM(t.GetEnd().y))]).buffer(MM(t.GetWidth()) / 2))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.IsOnLayer(layer):
                s = p.GetEffectivePolygon()
                o = s.Outline(0)
                geoms.append(Polygon([(MM(o.CPoint(k).x), MM(o.CPoint(k).y)) for k in range(o.PointCount())]).buffer(0))
    return shapely.union_all(geoms) if geoms else None


def pad_xy(b, ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            return MM(p.GetPosition().x), MM(p.GetPosition().y)
    raise KeyError((ref, num))


def bottleneck(geom, pa, pb, hi=8.0):
    """Largest w such that geom shrunk by w/2 still joins the two pad shapes (each grown by w/2)."""
    if geom is None:
        return 0.0

    def joins(w):
        e = geom.buffer(-w / 2, 16)
        for part in getattr(e, "geoms", [e]):
            if not part.is_empty and part.distance(pa) <= w / 2 + 1e-6 and part.distance(pb) <= w / 2 + 1e-6:
                return True
        return False
    if not joins(0.01):
        return 0.0
    lo = 0.01
    for _ in range(18):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if joins(mid) else (lo, mid)
    return lo


def pad_shape(b, ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            o = p.GetEffectivePolygon().Outline(0)
            return Polygon([(MM(o.CPoint(k).x), MM(o.CPoint(k).y)) for k in range(o.PointCount())]).buffer(0)
    raise KeyError((ref, num))


def measure(pcb, net, a, c, layers):
    b = pcbnew.LoadBoard(str(REPO / pcb))
    A, C = pad_xy(b, *a), pad_xy(b, *c)
    pa, pc = pad_shape(b, *a), pad_shape(b, *c)
    per = {b.GetLayerName(l): bottleneck(copper(b, net, l), pa, pc) for l in layers}
    return per, sum(per.values()), math.hypot(C[0] - A[0], C[1] - A[1])


PATHS = [
    ("FC battery in: XT30 pigtail pad J2 -> shunt RS1", "hardware/drone-pcb/microscout-fc.kicad_pcb", "/Power/VBAT_RAW",
     ("J2", "1"), ("RS1", "1"), [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu]),
    ("FC battery out: shunt RS1 -> ESC pad J8", "hardware/drone-pcb/microscout-fc.kicad_pcb", "VBAT",
     ("RS1", "2"), ("J8", "1"), [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu]),
] + [
    (f"ESC motor {ch} phase {ph}: {side} -> motor pad", "hardware/esc-pcb/microscout-esc.kicad_pcb",
     f"/Motor {ch}/M{ch}_PH_{ph}", (f"Q{ch}0{2 * i + q}", pad), (f"J{ch}0{i + 1}", "1"), [pcbnew.F_Cu, pcbnew.B_Cu])
    for ch in (1, 2) for i, ph in enumerate("ABC")
    for side, q, pad in (("low-side FET drain", 2, "5"), ("high-side FET source", 1, "2"))
]

# IPC-2221 outer-layer formula applied to a via barrel (a conservative, commonly used bound):
# A = pi (drill + t) t, I = 0.048 dT^0.44 A^0.725 with A in square mils.
PLATING_MM = 0.018          # ASSUMPTION: 18 um barrel plating (JLCPCB's stated minimum; the real value is UNCONFIRMED)


def via_amps(drill_mm, dT=10.0, t=PLATING_MM):
    a_mil2 = math.pi * (drill_mm + t) * t / 0.0254 ** 2
    return 0.048 * dT ** 0.44 * a_mil2 ** 0.725


def cell_vias(pcb="hardware/esc-pcb/microscout-esc.kicad_pcb"):
    """Stitching vias inside each ESC power-cell strip (zones named 'cell GND' / 'cell VBAT' on F.Cu)."""
    b = pcbnew.LoadBoard(str(REPO / pcb))
    vias = [(t.GetNetname(), Point(MM(t.GetPosition().x), MM(t.GetPosition().y)), MM(t.GetDrillValue()))
            for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    out = {"GND": [], "VBAT": []}
    for z in b.Zones():
        net = z.GetNetname()
        if z.GetIsRuleArea() or z.GetZoneName() != f"cell {net}" or net not in out:
            continue
        o = z.Outline().Outline(0)
        poly = Polygon([(MM(o.CPoint(k).x), MM(o.CPoint(k).y)) for k in range(o.PointCount())])
        out[net].append(sum(1 for n, pt, _ in vias if n == net and poly.contains(pt)))
    drill = min((d for n, _, d in vias if n in out), default=0.25)
    return out, drill


def main():
    rows = []
    for name, pcb, net, a, c, layers in PATHS:
        try:
            per, tot, length = measure(pcb, net, a, c, layers)
        except Exception as e:          # board not routed yet
            rows.append(f"| {name} | - | - | not measured: {str(e)[:60]} |")
            continue
        rows.append(f"| {name} | {length:.1f} mm | " + ", ".join(f"{k} {v:.2f}" for k, v in per.items()) + f" | {tot:.2f} mm |")
    vias_md = ""
    try:
        counts, drill = cell_vias()
        if counts["GND"]:
            amps = via_amps(drill)
            vias_md = ("\n## Stitching vias in the ESC power cells\n\nEach power cell's GND strip reaches the L2 GND plane, and its "
                       "VBAT strip the L3 VBAT plane, only through its stitching vias (no via sits in a FET pad). "
                       f"One via of {drill:.2f} mm drill with {PLATING_MM * 1000:.0f} um plating (ASSUMPTION): barrel area "
                       f"A = pi (d + t) t = {math.pi * (drill + PLATING_MM) * PLATING_MM:.4f} mm2 = "
                       f"{math.pi * (drill + PLATING_MM) * PLATING_MM / 0.0254 ** 2:.1f} mil2; I = 0.048 x 10^0.44 x A^0.725 = "
                       f"**{amps:.2f} A per via for a 10 C rise** (IPC-2221 outer-layer formula, a conservative bound).\n\n"
                       "| Strip | Vias per cell (fewest - most, 12 cells) | Current for a 10 C rise, fewest | Peak current through it |\n|---|---|---:|---:|\n"
                       f"| GND (low-side source) | {min(counts['GND'])} - {max(counts['GND'])} | {min(counts['GND']) * amps:.1f} A | 9.2 A (full throttle, S15) |\n"
                       f"| VBAT (high-side drain) | {min(counts['VBAT'])} - {max(counts['VBAT'])} | {min(counts['VBAT']) * amps:.1f} A | 9.2 A; the L1 VBAT pour also feeds it |\n\n"
                       "The GND strips are the weak point: a strip carries the low-side current only while that FET conducts, so the "
                       "RMS current is lower than the peak (about 9.2 x sqrt(1/3) = 5.3 A in six-step drive at full duty, ESTIMATE), "
                       "but cells with few vias are below even that. Options for G4: vias in the FET source pads (filled and capped, "
                       "extra cost), a thicker plating option, or a wider GND strip. **UNCONFIRMED until measured at G6.**\n")
    except Exception as e:          # ESC not built with power cells
        vias_md = f"\n## Stitching vias in the ESC power cells\n\nnot measured: {str(e)[:80]}\n"
    md = REPO / "review/G3/trace-widths.md"
    txt = md.read_text()
    txt = txt.split("\n## Measured copper")[0].rstrip() + "\n"
    txt += ("\n## Measured copper (from the routed boards)\n\nGenerated by `tools/pcb/copper.py`: the narrowest cross-section of "
            "the path's own copper (pours, tracks and pads) on each layer: the widest pipe that still joins the two pads, "
            "found by shrinking the copper until it splits (binary search on the width). Vias between layers are not "
            "counted. Channels 3 and 4 of the ESC are copies of 2 and 1. "
            "Compare the sum with the IPC-2221 width above times the number of layers it assumes. A short path can run hotter "
            "or cooler than this estimate: **UNCONFIRMED until measured at G6.**\n\n"
            "| Path | Pad-to-pad distance | Narrowest point per layer (mm) | Sum over layers |\n|---|---:|---|---:|\n" + "\n".join(rows) + "\n"
            + vias_md)
    md.write_text(txt)
    print("\n".join(rows))


if __name__ == "__main__":
    main()
