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
    (f"ESC motor {ch} phase {ph}: low-side FET drain -> motor pad", "hardware/esc-pcb/microscout-esc.kicad_pcb",
     f"/Motor {ch}/M{ch}_PH_{ph}", (f"Q{ch}0{2 * i + 2}", "5"), (f"J{ch}0{i + 1}", "1"), [pcbnew.F_Cu, pcbnew.B_Cu])
    for ch in (1, 2) for i, ph in enumerate("ABC")
]


def main():
    rows = []
    for name, pcb, net, a, c, layers in PATHS:
        try:
            per, tot, length = measure(pcb, net, a, c, layers)
        except Exception as e:          # board not routed yet
            rows.append(f"| {name} | - | - | not measured: {str(e)[:60]} |")
            continue
        rows.append(f"| {name} | {length:.1f} mm | " + ", ".join(f"{k} {v:.2f}" for k, v in per.items()) + f" | {tot:.2f} mm |")
    md = REPO / "review/G3/trace-widths.md"
    txt = md.read_text()
    txt = txt.split("\n## Measured copper")[0].rstrip() + "\n"
    txt += ("\n## Measured copper (from the routed boards)\n\nGenerated by `tools/pcb/copper.py`: the narrowest cross-section of "
            "the path's own copper (pours, tracks and pads) on each layer, measured on 39 cuts across the straight line "
            "between the two pad centres, and the narrowest sum over layers. Channels 3 and 4 of the ESC are copies of 2 and 1. "
            "Compare the sum with the IPC-2221 width above times the number of layers it assumes. A short path can run hotter "
            "or cooler than this estimate: **UNCONFIRMED until measured at G6.**\n\n"
            "| Path | Pad-to-pad distance | Narrowest point per layer (mm) | Sum over layers |\n|---|---:|---|---:|\n" + "\n".join(rows) + "\n")
    md.write_text(txt)
    print("\n".join(rows))


if __name__ == "__main__":
    main()
