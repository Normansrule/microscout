# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Shared helpers for the MicroScout PCB layout scripts (KiCad 7 pcbnew Python API).

Runs with the system Python that ships KiCad's `pcbnew` module (not the project venv).
Every board script builds its .kicad_pcb from the G2 netlist, so the layout always matches
the approved schematic: footprints, values, nets and the schematic UUID links are copied over.
"""
from __future__ import annotations

import math
import pathlib
import sys

import pcbnew

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "sch"))
import sexpr  # noqa: E402

FP_DIRS = [REPO / "hardware/libraries/kicad7-footprints", REPO / "hardware/libraries"]
MM = pcbnew.FromMM


def mm(v):
    return pcbnew.ToMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


# ------------------------------------------------------------------ netlist
def _find(node, key):
    for c in node[1:] if isinstance(node, list) else []:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def _all(node, key):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


def read_netlist(path):
    """Returns (components, nets). components: ref -> dict(value, footprint, fields, path); nets: name -> [(ref, pin)]."""
    root = sexpr.parse(pathlib.Path(path).read_text())[0]
    comps = {}
    for c in _all(_find(root, "components"), "comp"):
        ref = _find(c, "ref")[1]
        d = dict(value=_find(c, "value")[1], footprint=_find(c, "footprint")[1] if _find(c, "footprint") else "", fields={})
        fl = _find(c, "fields")
        for f in _all(fl, "field") if fl else []:
            d["fields"][_find(f, "name")[1]] = f[2] if len(f) > 2 else ""
        for p in _all(c, "property"):
            d["fields"].setdefault(_find(p, "name")[1], _find(p, "value")[1] if _find(p, "value") else "")
        sp = _find(c, "sheetpath")
        d["path"] = (_find(sp, "tstamps")[1] if sp else "/") + _find(c, "tstamps")[1]
        d["sheet"] = _find(sp, "names")[1] if sp else "/"
        comps[ref] = d
    nets = {}
    for n in _all(_find(root, "nets"), "net"):
        nets[_find(n, "name")[1]] = [(_find(x, "ref")[1], _find(x, "pin")[1]) for x in _all(n, "node")]
    return comps, nets


# ------------------------------------------------------------------ footprints
def load_footprint(libref):
    lib, name = libref.split(":", 1)
    for d in FP_DIRS:
        p = d / f"{lib}.pretty"
        if (p / f"{name}.kicad_mod").exists():
            fp = pcbnew.FootprintLoad(str(p), name)
            if fp is not None:
                return fp
    raise FileNotFoundError(f"footprint {libref} not found in {', '.join(str(d) for d in FP_DIRS)}")


def courtyard(fp, layer=None):
    """Courtyard outline of a footprint as a shapely polygon (mm, board coordinates)."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    polys = []
    for lay in ([layer] if layer is not None else [pcbnew.F_CrtYd, pcbnew.B_CrtYd]):
        try:
            sh = fp.GetCourtyard(lay)
        except Exception:
            continue
        for i in range(sh.OutlineCount()):
            o = sh.Outline(i)
            pts = [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]
            if len(pts) >= 3:
                polys.append(Polygon(pts).buffer(0))
    if polys:
        return unary_union(polys)
    bb = fp.GetBoundingBox(False, False)
    return box(mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))


def new_board(stackup_layers=4, thickness_mm=1.0):
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(stackup_layers)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(MM(thickness_mm))
    return b


def build_from_netlist(board, netlist_path, fp_override=None):
    """Adds every footprint and net from the netlist. Returns {ref: FOOTPRINT}."""
    comps, nets = read_netlist(netlist_path)
    fp_override = fp_override or {}
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = netinfo[name]
    fps = {}
    for ref, c in comps.items():
        lib = fp_override.get(ref, c["footprint"])
        fp = load_footprint(lib)
        fp.SetFPID(pcbnew.LIB_ID(*lib.split(":", 1)))
        fp.SetReference(ref)
        fp.Reference().SetVisible(False)        # dense boards: designators live on the assembly drawing (Fab layer)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        for k, v in c["fields"].items():
            if k in ("LCSC", "MPN", "Manufacturer", "DNP"):
                fp.SetField(k, v) if hasattr(fp, "SetField") else None
                f = fp.GetFieldByName(k) if hasattr(fp, "GetFieldByName") else None
                if f:
                    f.SetVisible(False)
        if c["fields"].get("DNP") or "DNP" in c["fields"].values():
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        for pad in fp.Pads():
            n = pin_net.get((ref, pad.GetNumber()))
            if n is not None:
                pad.SetNet(n)
        board.Add(fp)
        fps[ref] = fp
    return fps, comps, nets


def place(fp, x, y, rot=0.0, back=False):
    if back and not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)


def add_outline(board, poly, width=0.1):
    """Edge.Cuts from a shapely polygon (exterior and holes)."""
    rings = [poly.exterior] + list(poly.interiors)
    for ring in rings:
        pts = list(ring.coords)
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(width))
            board.Add(s)


def add_npth(board, x, y, d, ref="H"):
    """A mounting hole (microscout:MountingHole_3.0mm_NPTH for the 3.0 mm grommet holes)."""
    fp = load_footprint("microscout:MountingHole_3.0mm_NPTH")
    fp.SetFPID(pcbnew.LIB_ID("microscout", "MountingHole_3.0mm_NPTH"))
    fp.SetReference(ref)
    fp.SetPosition(V(x, y))
    board.Add(fp)
    return fp


def text(board, s, x, y, size=0.8, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(V(size, size)); t.SetTextThickness(MM(size * 0.15))
    if mirror:
        t.SetMirrored(True)
    board.Add(t)
    return t
