# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Finishing router: connects what Freerouting left open, one connection at a time, on a saved board.

Freerouting 1.9 leaves a handful of connections open on dense boards and does not improve with more passes.
This router takes KiCad's own list of missing connections (the DRC report), and for each one runs an A* search
on a fine grid (0.02 mm) over the signal layers, with vias, using exact clearances:

    a grid point is free on a layer if it lies outside every other-net object grown by
    (larger of the two clearances) + (track width / 2) + 0.005 mm margin;
    a via fits at a point if the via pad grown the same way is free on every copper layer.

Late pours (zones named "late ...") are ignored as obstacles because they are refilled afterwards; routing planes
(the L2 GND plane, the ESC L3 VBAT plane) let vias through but not tracks; other pre-route copper islands block both.
Every result is re-checked by KiCad's DRC after the zones are refilled. Nothing here is a substitute for review.
"""
from __future__ import annotations

import heapq
import math
import re

import numpy as np
import pcbnew
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree

RES = 0.02          # grid step (mm)
MARGIN = 0.005      # extra clearance against rounding (mm)
VIA_COST = 1.2      # mm-equivalent cost of a via
TURN_COST = 0.02
RIP_COST = 0.25    # mm-equivalent cost per grid step through another net's track (rip-up mode)
RIP_REACH = 1.0    # rip-up mode may only remove tracks this close (mm) to the connection's two ends


_LIB = None


def _lib():
    """Compiles astar.c once (into build/) and loads it; None if no C compiler is available."""
    global _LIB
    if _LIB is None:
        import ctypes
        import pathlib
        import subprocess
        src = pathlib.Path(__file__).with_name("astar.c")
        so = pathlib.Path(__file__).resolve().parents[2] / "build" / "astar.so"
        so.parent.mkdir(exist_ok=True)
        if not so.exists() or so.stat().st_mtime < src.stat().st_mtime:
            if subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", str(so), str(src), "-lm"]).returncode:
                _LIB = False
                return None
        lib = ctypes.CDLL(str(so))
        P = np.ctypeslib.ndpointer
        lib.astar.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, P(np.float32), P(np.float32), P(np.uint8),
                              P(np.uint8), P(np.int32), ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                              ctypes.c_long, P(np.int32), ctypes.c_int]
        lib.astar.restype = ctypes.c_int
        _LIB = lib
    return _LIB or None


def _astar(cost, via, start, goal, res, via_base, weight, limit):
    """A* over cost[layer, i, j] (<0 blocked) with vias via[i, j] (<0 none). Returns [(layer, i, j), ...] or None."""
    nl, nx, ny = cost.shape
    gp = np.argwhere(goal.any(axis=0)).astype(np.int32)
    gp = np.ascontiguousarray(gp[:: max(1, len(gp) // 256)])
    lib = _lib()
    if lib is None:
        raise RuntimeError("finisher needs a C compiler (cc) for tools/pcb/astar.c")
    out = np.zeros(nl * nx * ny if nl * nx * ny < 2_000_000 else 2_000_000, np.int32)
    n = lib.astar(nl, nx, ny, np.ascontiguousarray(cost.ravel()), np.ascontiguousarray(via.astype(np.float32).ravel()),
                  np.ascontiguousarray(start.ravel()), np.ascontiguousarray(goal.ravel()), gp.ravel(), len(gp),
                  res, via_base, weight, limit, out, len(out))
    if n <= 0:
        return None
    nn = nx * ny
    return [(int(k // nn), int((k % nn) // ny), int(k % ny)) for k in out[:n][::-1]]


def mm(v):
    return pcbnew.ToMM(v)


def poly_of(shape_poly_set):
    out = []
    for i in range(shape_poly_set.OutlineCount()):
        o = shape_poly_set.Outline(i)
        pts = [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]
        if len(pts) >= 3:
            holes = []
            for h in range(shape_poly_set.HoleCount(i)):
                hh = shape_poly_set.Hole(i, h)
                holes.append([(mm(hh.CPoint(k).x), mm(hh.CPoint(k).y)) for k in range(hh.PointCount())])
            out.append(Polygon(pts, holes).buffer(0))
    return shapely.union_all(out) if out else None


class Finisher:
    def __init__(self, board, rule, signal_layers, plane_zone=lambda z: False, log=print, allow_rip=False):
        """rule(netname) -> (track width, clearance, via diameter, via drill)."""
        self.b, self.rule, self.log = board, rule, log
        self.layers = list(signal_layers)
        self.cu = [l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l) and board.IsLayerEnabled(l)]
        self.plane_zone = plane_zone
        self.allow_rip = allow_rip
        self.rip_zone = None
        self._to_rip = []
        self.edge = poly_of(self._edge_poly())
        self.edge_cl = mm(board.GetDesignSettings().m_CopperEdgeClearance)
        self._collect()

    def _edge_poly(self):
        s = pcbnew.SHAPE_POLY_SET()
        self.b.GetBoardPolygonOutlines(s)
        return s

    # ------------------------------------------------------------------ obstacles
    def _collect(self):
        """items[layer] = list of (net, geometry, clearance)."""
        self.zone_geoms = set()          # zone outlines: obstacles for other nets, but not walkable for their own
        self.track_of = {}               # id(track geometry) -> PCB_TRACK (tracks can be ripped up)
        self.holes = []                  # (x, y, drill) of every via and plated or unplated hole
        self.items = {l: [] for l in self.cu}
        self.via_only_ok = {l: [] for l in self.cu}       # plane copper: blocks tracks, not vias
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetname()
                cl = self.rule(net)[1] if net else 0.1
                for l in self.cu:
                    if pad.IsOnLayer(l):
                        g = poly_of(pad.GetEffectivePolygon())
                        if g is not None:
                            self.items[l].append((net, g, cl))
                if pad.GetDrillSize().x > 0:
                    self.holes.append((mm(pad.GetPosition().x), mm(pad.GetPosition().y), mm(max(pad.GetDrillSize().x, pad.GetDrillSize().y))))
                    hole = Point(mm(pad.GetPosition().x), mm(pad.GetPosition().y)).buffer(mm(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2, 16)
                    for l in self.cu:
                        self.items[l].append((None, hole, 0.25))      # hole edge clearance for everything
        for t in self.b.GetTracks():
            self._add_track(t)
        for z in self.b.Zones():
            if z.GetIsRuleArea():
                g = poly_of(z.Outline())
                for l in self.cu:
                    if z.IsOnLayer(l):
                        if z.GetDoNotAllowTracks():
                            self.via_only_ok[l].append((None, g, 0.0))
                        if z.GetDoNotAllowVias():
                            self.items[l].append(("__via_keepout__", g, 0.0))
                continue
            if z.GetZoneName().startswith("late"):
                continue
            g = poly_of(z.Outline())
            for l in self.cu:
                if z.IsOnLayer(l):
                    if self.plane_zone(z):
                        self.via_only_ok[l].append((z.GetNetname(), g, mm(z.GetLocalClearance())))
                    else:
                        self.items[l].append((z.GetNetname(), g, mm(z.GetLocalClearance())))
                        self.zone_geoms.add(id(g))
        self._index()

    def _add_track(self, t):
        net = t.GetNetname()
        cl = self.rule(net)[1]
        if t.GetClass() == "PCB_VIA":
            self.holes.append((mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetDrillValue())))
            g = Point(mm(t.GetPosition().x), mm(t.GetPosition().y)).buffer(mm(t.GetWidth()) / 2, 16)
            for l in self.cu:
                self.items[l].append((net, g, cl))
        else:
            g = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2, 8)
            self.items[t.GetLayer()].append((net, g, cl))
            self.track_of[id(g)] = t

    def _index(self):
        self.tree = {l: STRtree([g for _, g, _ in self.items[l]]) for l in self.cu}
        self.ptree = {l: STRtree([g for _, g, _ in self.via_only_ok[l]]) if self.via_only_ok[l] else None for l in self.cu}

    def _blocked(self, l, net, grow, win, planes_block=True, via=False):
        """Union of other-net obstacles on layer l inside window win, each grown by its clearance + grow."""
        geoms = []
        for k in self.tree[l].query(win):
            n, g, cl = self.items[l][k]
            if n == "__via_keepout__":
                if via:
                    geoms.append(g)
                continue
            if n == net and n:
                continue
            geoms.append(g.buffer(max(cl, self.rule(net)[1]) + grow, 8))
        if planes_block and self.ptree[l] is not None:
            for k in self.ptree[l].query(win):
                n, g, cl = self.via_only_ok[l][k]
                if n != net or n is None:
                    geoms.append(g.buffer(max(cl, self.rule(net)[1]) + grow, 8) if n else g)
        return shapely.union_all(geoms) if geoms else None

    # ------------------------------------------------------------------ search
    def route(self, net, start_shapes, goal_shapes, pad_win=3.0, plane=None):
        """start/goal: dict layer -> shapely geometry of own-net copper to start from / reach.
        plane: own-net plane outline; a via dropped anywhere inside it also counts as reaching the goal."""
        w, cl, vd, vdr = self.rule(net)
        if plane is not None:          # try the short way first: a via into the plane next to the start
            bx = shapely.union_all(list(start_shapes.values())).bounds
            win = box(bx[0] - 1.5, bx[1] - 1.5, bx[2] + 1.5, bx[3] + 1.5)
            res = self._search(net, w, vd, start_shapes, {}, win, plane)
            if res:
                return res
        allg = [g for d in (start_shapes, goal_shapes) for g in d.values()]
        bx = shapely.union_all(allg).bounds
        self._to_rip = []
        for grow_win in (pad_win, pad_win * 2.5):
            win = box(bx[0] - grow_win, bx[1] - grow_win, bx[2] + grow_win, bx[3] + grow_win)
            res = self._search(net, w, vd, start_shapes, goal_shapes, win, plane)
            if res:
                return res
        if self.allow_rip:
            # local rip-up only: tracks within RIP_REACH of the two ends (a pin boxed in by its neighbours' escapes)
            self.rip_zone = shapely.union_all(allg).buffer(RIP_REACH)
            win = box(bx[0] - pad_win, bx[1] - pad_win, bx[2] + pad_win, bx[3] + pad_win)
            try:
                return self._search(net, w, vd, start_shapes, goal_shapes, win, plane, rip=True)
            finally:
                self.rip_zone = None
        return None

    def _obstacles(self, l, net, grow, win, planes_block=True, via=False, soft_tracks=False):
        """(hard, soft) unions of other-net obstacles on layer l, grown by clearance + grow. With soft_tracks, other
        nets' tracks go to 'soft' (the search may cross them at a cost; the caller then rips them up)."""
        hard, soft = [], []
        cl_n = self.rule(net)[1]
        for k in self.tree[l].query(win):
            n, g, cl = self.items[l][k]
            if n == "__via_keepout__":
                if via:
                    hard.append(g.buffer(grow, 8))
                continue
            if n == net and n:
                continue
            gg = g.buffer(max(cl, cl_n) + grow, 8)
            rip_ok = soft_tracks and id(g) in self.track_of and (self.rip_zone is None or g.intersects(self.rip_zone))
            (soft if rip_ok else hard).append(gg)
        if planes_block and self.ptree[l] is not None:
            for k in self.ptree[l].query(win):
                n, g, cl = self.via_only_ok[l][k]
                if n != net or n is None:
                    hard.append(g.buffer(max(cl, cl_n) + grow, 8) if n else g.buffer(grow, 8))
        u = lambda gs: shapely.union_all(gs) if gs else None
        return u(hard), u(soft)

    def _search(self, net, w, vd, starts, goals, win, plane=None, rip=False):
        x0, y0, x1, y1 = win.bounds
        nx, ny = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
        xs = x0 + np.arange(nx) * RES
        ys = y0 + np.arange(ny) * RES
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        inside_t = self.edge.buffer(-(self.edge_cl + w / 2 + MARGIN))
        inside_v = self.edge.buffer(-(self.edge_cl + vd / 2 + MARGIN))
        cost = {}
        for l in self.layers:
            hard, soft = self._obstacles(l, net, w / 2 + MARGIN, win, soft_tracks=rip)
            c = np.where(shapely.contains_xy(inside_t, X, Y), 0.0, -1.0).astype(np.float32)
            if soft is not None:
                c[shapely.contains_xy(soft, X, Y) & (c >= 0)] = RIP_COST
            if hard is not None:
                c[shapely.contains_xy(hard, X, Y)] = -1.0
            # own-net copper is always walkable: a new track may start, end or run on top of it. (Neighbours
            # packed at exactly the minimum clearance would otherwise block the grid points on an existing track.)
            own = [self.items[l][k][1] for k in self.tree[l].query(win)
                   if self.items[l][k][0] == net and net and id(self.items[l][k][1]) not in self.zone_geoms]
            own += [g for d in (starts, goals) for ll, g in d.items() if ll == l]
            if own:
                # ...but still at the exact clearance (no rounding margin) from everything else
                hard0, _ = self._obstacles(l, net, w / 2, win)
                walk = shapely.contains_xy(shapely.union_all(own).buffer(-0.01), X, Y)
                if hard0 is not None:
                    walk &= ~shapely.contains_xy(hard0, X, Y)
                c[walk] = 0.0
            cost[l] = c
        via = np.where(shapely.contains_xy(inside_v, X, Y), 0.0, -1.0).astype(np.float32)
        for l in self.cu:
            hard, soft = self._obstacles(l, net, vd / 2 + MARGIN, win, planes_block=False, via=True, soft_tracks=rip)
            if soft is not None:
                via[shapely.contains_xy(soft, X, Y) & (via >= 0)] = RIP_COST * 10
            if hard is not None:
                via[shapely.contains_xy(hard, X, Y)] = -1.0
        # drilled holes of any net (own vias included) keep the hole-to-hole distance
        vdr = self.rule(net)[3]
        hh = mm(self.b.GetDesignSettings().m_HoleToHoleMin)
        for hx, hy, hd in self.holes:
            if x0 - 2 < hx < x1 + 2 and y0 - 2 < hy < y1 + 2:
                via[(X - hx) ** 2 + (Y - hy) ** 2 <= (hd / 2 + vdr / 2 + hh + MARGIN) ** 2] = -1.0
        # no via inside own-net SMD pads either (via-in-pad)
        for l in self.layers:
            for k in self.tree[l].query(win):
                n, g, _ = self.items[l][k]
                if n == net and id(g) not in self.track_of:
                    via[shapely.contains_xy(g.buffer(vd / 2), X, Y)] = -1.0
        layers = [l for l in self.layers if (cost[l] >= 0).any()]
        li = {l: i for i, l in enumerate(layers)}
        goal = np.zeros((len(layers), nx, ny), np.uint8)
        start = np.zeros((len(layers), nx, ny), np.uint8)
        for l, g in goals.items():
            if l in li:
                goal[li[l]] = shapely.contains_xy(g, X, Y) & (cost[l] >= 0)
        for l, g in starts.items():
            if l in li:
                start[li[l]] = shapely.contains_xy(g, X, Y) & (cost[l] >= 0)
        plane_goal = None
        if plane is not None:
            plane_goal = (via == 0) & shapely.contains_xy(plane, X, Y)
            for k in range(len(layers)):
                goal[k] |= (plane_goal & (cost[layers[k]] == 0)).astype(np.uint8)
        if not goal.any() or not start.any():
            return None
        C = np.ascontiguousarray(np.stack([cost[l] for l in layers]), dtype=np.float32)
        nodes = _astar(C, via, start, goal, RES, VIA_COST, 1.3, 6_000_000)
        if nodes is None:
            return None
        out = [(layers[L], x0 + i * RES, y0 + j * RES) for L, i, j in nodes]
        Le, ie, je = nodes[-1]
        own = goals.get(layers[Le])
        if plane_goal is not None and plane_goal[ie, je] and not (own is not None and own.contains(Point(out[-1][1], out[-1][2]))):
            out.append(("VIA",) + out[-1][1:])            # end on a via into the plane
        if rip:
            self._to_rip = self._crossed(net, w, vd, out)
        return out

    def _crossed(self, net, w, vd, path):
        """Other-net tracks a (rip-up) path runs through: those whose clearance zone contains a path point."""
        cl_n = self.rule(net)[1]
        hit = set()
        prev = None
        for p in path:
            pts = []
            if p[0] == "VIA" or (prev is not None and prev[0] != p[0]):
                pts = [(l, vd / 2) for l in self.cu]
            if p[0] != "VIA":
                pts.append((p[0], w / 2))
            for l, r in pts:
                q = Point(p[1], p[2])
                for k in self.tree[l].query(q.buffer(1.0)):
                    n, g, cl = self.items[l][k]
                    if id(g) in self.track_of and n != net and g.distance(q) < max(cl, cl_n) + r + MARGIN:
                        hit.add(id(g))
            prev = p
        return [self.track_of[i] for i in hit]

    # ------------------------------------------------------------------ output
    def commit(self, net, path):
        if self._to_rip:
            for t in self._to_rip:
                self.b.Delete(t)
            self.log(f"finisher: ripped up {len(self._to_rip)} track segments of other nets for {net}")
            self.ripped = getattr(self, "ripped", 0) + len(self._to_rip)
            self._to_rip = []
            self._collect()
        w, cl, vd, vdr = self.rule(net)
        code = self.b.GetNetInfo().GetNetItem(net).GetNetCode()
        new = []
        end_via = path[-1][0] == "VIA"
        if end_via:
            path = path[:-1]
        # split into runs on one layer; vias between runs
        runs, cur = [], [path[0]]
        for p in path[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur)
                cur = [p]
            else:
                cur.append(p)
        runs.append(cur)
        for k, run in enumerate(runs):
            pts = [(x, y) for _, x, y in run]
            simp = [pts[0]]
            for a, b2 in zip(pts[1:-1], pts[2:]):
                p0 = simp[-1]
                d1 = (round((a[0] - p0[0]) / RES), round((a[1] - p0[1]) / RES))
                d2 = (round((b2[0] - a[0]) / RES), round((b2[1] - a[1]) / RES))
                g1, g2 = math.gcd(*d1) or 1, math.gcd(*d2) or 1
                if (d1[0] // g1, d1[1] // g1) != (d2[0] // g2, d2[1] // g2):
                    simp.append(a)
            if len(pts) > 1:
                simp.append(pts[-1])
            for (xa, ya), (xb, yb) in zip(simp[:-1], simp[1:]):
                t = pcbnew.PCB_TRACK(self.b)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(xa), pcbnew.FromMM(ya)))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(xb), pcbnew.FromMM(yb)))
                t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(run[0][0]); t.SetNetCode(code)
                self.b.Add(t); new.append(t)
            if k + 1 < len(runs):
                v = pcbnew.PCB_VIA(self.b)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(run[-1][1]), pcbnew.FromMM(run[-1][2])))
                v.SetWidth(pcbnew.FromMM(vd)); v.SetDrill(pcbnew.FromMM(vdr)); v.SetNetCode(code)
                self.b.Add(v); new.append(v)
        if end_via:
            v = pcbnew.PCB_VIA(self.b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(path[-1][1]), pcbnew.FromMM(path[-1][2])))
            v.SetWidth(pcbnew.FromMM(vd)); v.SetDrill(pcbnew.FromMM(vdr)); v.SetNetCode(code)
            self.b.Add(v); new.append(v)
        bad = self._violations(net, new)
        if bad:
            for t in new:
                self.b.Delete(t)
            self.log(f"finisher: dropped a {net} route that broke clearance ({bad})")
            return None
        for t in new:
            self._add_track(t)
        self._index()
        return new

    def _violations(self, net, new):
        """Exact clearance check of new tracks and vias against every other-net object (and the hole spacing)."""
        cl_n = self.rule(net)[1]
        for t in new:
            if t.GetClass() == "PCB_VIA":
                g = Point(mm(t.GetPosition().x), mm(t.GetPosition().y)).buffer(mm(t.GetWidth()) / 2, 32)
                layers = self.cu
            else:
                g = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2, 16)
                layers = [t.GetLayer()]
            for l in layers:
                for k in self.tree[l].query(g.buffer(0.5)):
                    n, og, cl = self.items[l][k]
                    if n == net and n:
                        continue
                    if n == "__via_keepout__":
                        if t.GetClass() == "PCB_VIA" and og.intersects(g):
                            return "via keep-out"
                        continue
                    if og.distance(g) < max(cl, cl_n) - 0.001:
                        return f"{og.distance(g):.3f} mm on {self.b.GetLayerName(l)}"
                if t.GetClass() != "PCB_VIA" and self.ptree[l] is not None:
                    for k in self.ptree[l].query(g):
                        n, og, cl = self.via_only_ok[l][k]
                        if (n is None or n != net) and og.intersects(g):
                            return "track in a no-track area or across another net's plane"
        return None


# ---------------------------------------------------------------------- driving it from a DRC report
ITEM = re.compile(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (Pad (\S+) \[(.*?)\] of (\S+) on ([\w.]+)|Track \[(.*?)\] on ([\w.]+)|Via \[(.*?)\]|Zone \[(.*?)\] on ([\w.]+))")


def unconnected(report_text):
    u = report_text[report_text.index("unconnected pads"):] if "unconnected pads" in report_text else ""
    out = []
    for blk in u.split("[unconnected_items]")[1:]:
        its = ITEM.findall(blk)[:2]
        if len(its) == 2:
            out.append(its)
    return out


def item_shapes(b, it):
    """DRC item -> (net, {layer: copper geometry})."""
    x, y = float(it[0]), float(it[1])
    lay = {b.GetLayerName(l): l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l)}
    if it[2].startswith("Pad"):
        fp = b.FindFootprintByReference(it[5])
        for pad in fp.Pads():
            if pad.GetNumber() == it[3] and abs(mm(pad.GetPosition().x) - x) < 0.01 and abs(mm(pad.GetPosition().y) - y) < 0.01:
                g = poly_of(pad.GetEffectivePolygon())
                return pad.GetNetname(), {l: g for l in lay.values() if pad.IsOnLayer(l)}
        return None, {}
    if it[2].startswith("Track"):
        net, L = it[7], lay[it[8]]
        best = None
        for t in b.GetTracks():
            if t.GetClass() != "PCB_VIA" and t.GetNetname() == net and t.GetLayer() == L:
                s = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))])
                d = s.distance(Point(x, y))
                if best is None or d < best[0]:
                    best = (d, s.buffer(mm(t.GetWidth()) / 2 - 0.005, 8))
        return net, {L: best[1]} if best else {}
    if it[2].startswith("Via"):
        net = it[9]
        g = Point(x, y).buffer(0.2, 16)
        return net, {l: g for l in lay.values()}
    if it[2].startswith("Zone"):
        net, L = it[10], lay[it[11]]
        best = None
        for z in b.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net or not z.IsOnLayer(L):
                continue
            g = poly_of(z.GetFilledPolysList(L))
            if g is None:
                continue
            for part in getattr(g, "geoms", [g]):
                d = part.distance(Point(x, y))
                if best is None or d < best[0]:
                    best = (d, part.buffer(-0.05))
        return net, {L: best[1]} if best else {}
    return None, {}


def rule_from_layout(L):
    """netname -> (track, clearance, via diameter, via drill) from the board script's net classes."""
    d = getattr(L, "default_rule", None) or dict(track=0.127, clearance=0.127, via_d=0.5, via_drill=0.3)

    def rule(net):
        for cname, (_, pats, c) in L.classes.items():
            if any(p.fullmatch(net or "") for p in pats):
                return c["track"], c["clearance"], c.get("via_d", d["via_d"]), c.get("via_drill", d["via_drill"])
        return d["track"], d["clearance"], d["via_d"], d["via_drill"]
    return rule


def finish_open(L, report_path, plane_zone=lambda z: False, rounds=8, log=print, rip_rounds=()):
    """Load the saved board, route every open connection KiCad reports, refill, re-check; repeat. From the second
    round on, a connection with no free path may rip up other nets' tracks (they are re-routed in the next round).
    The best board seen (fewest open connections) is kept."""
    import pathlib
    import shutil
    rule = rule_from_layout(L)
    best, stale = None, 0
    bestfile = pathlib.Path(str(L.out) + ".best")
    for rnd in range(rounds + 1):
        b = pcbnew.LoadBoard(str(L.out))
        pcbnew.WriteDRCReport(b, str(report_path), pcbnew.EDA_UNITS_MILLIMETRES, True)
        pairs = unconnected(pathlib.Path(report_path).read_text())
        pairs = [p for p in pairs if not (p[0][2].startswith("Zone") and p[1][2].startswith("Zone"))]
        if best is None or len(pairs) < best:
            best, stale = len(pairs), 0
            shutil.copy(L.out, bestfile)
        else:
            stale += 1
        log(f"finisher: round {rnd}: {len(pairs)} open connections (best {best})")
        if not pairs or stale >= 3 or rnd == rounds:
            break
        sig = [l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l) and b.IsLayerEnabled(l)
               and b.GetLayerType(l) == pcbnew.LT_SIGNAL]
        # global rip-up diverged in tests (18 -> 136 open); only local rip-up near the two ends, in the listed rounds
        F = Finisher(b, rule, sig, plane_zone=plane_zone, log=log, allow_rip=rnd in rip_rounds)
        planes = {}
        for z in b.Zones():
            if not z.GetIsRuleArea() and plane_zone(z):
                g = poly_of(z.Outline())
                planes[z.GetNetname()] = g if z.GetNetname() not in planes else planes[z.GetNetname()].union(g)
        ok = 0
        for a, c in pairs:
            try:
                na, sa = item_shapes(b, a)
                nc, sc = item_shapes(b, c)
            except Exception:           # an item ripped up earlier in this round
                continue
            if not sa or not sc or na != nc or not na:
                continue
            path = F.route(na, sa, sc, plane=planes.get(na))
            if path and F.commit(na, path):
                ok += 1
            elif not path:
                log(f"finisher: no path for {na} between {a[2][:40]} and {c[2][:40]}")
        log(f"finisher: round {rnd}: routed {ok} of {len(pairs)}" + (f", ripped up {F.ripped} track segments" if getattr(F, "ripped", 0) else ""))
        if ok == 0 and not any(r > rnd for r in rip_rounds):
            break
        pcbnew.SaveBoard(str(L.out), b)
        b = pcbnew.LoadBoard(str(L.out))
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        pcbnew.SaveBoard(str(L.out), b)
    if bestfile.exists():
        b = pcbnew.LoadBoard(str(L.out))
        pcbnew.WriteDRCReport(b, str(report_path), pcbnew.EDA_UNITS_MILLIMETRES, True)
        now = len([p for p in unconnected(pathlib.Path(report_path).read_text())
                   if not (p[0][2].startswith("Zone") and p[1][2].startswith("Zone"))])
        if now > best:
            shutil.copy(bestfile, L.out)
            log(f"finisher: kept the best round ({best} open instead of {now})")
        bestfile.unlink()


def clear_islands(board_path, is_island, log=print):
    """Removes other nets' tracks and vias that cross a pre-route copper island (is_island(zone) is True), with
    the zone's clearance. Freerouting treats such islands as planes it may route through, which cuts the copper the
    island is there for (the FC battery path). The finisher then routes those connections around the islands."""
    b = pcbnew.LoadBoard(str(board_path))
    zones = [(z, poly_of(z.Outline())) for z in b.Zones() if not z.GetIsRuleArea() and is_island(z)]
    doomed = []
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            g = Point(mm(t.GetPosition().x), mm(t.GetPosition().y)).buffer(mm(t.GetWidth()) / 2, 16)
        else:
            g = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2, 8)
        for z, zg in zones:
            if z.GetNetname() == net:
                continue
            if (t.GetClass() == "PCB_VIA" or z.IsOnLayer(t.GetLayer())) and zg.distance(g) < mm(z.GetLocalClearance()):
                doomed.append(t)
                break
    gone = len(doomed)
    for t in doomed:
        b.Delete(t)          # Delete, not Remove: a removed item left to Python's GC corrupts the next LoadBoard
    del doomed
    pcbnew.SaveBoard(str(board_path), b)        # zones are refilled by the finisher's first round
    log(f"removed {gone} other-net track segments and vias that crossed the battery-path islands")
    return gone


def remove_violators(board_path, report_path, log=print):
    """Deletes tracks named in KiCad's clearance / hole-clearance violations (the other item is usually a pad, a
    stitching via or a plane). The finisher then routes those connections again."""
    import pathlib
    txt = pathlib.Path(report_path).read_text()
    b = pcbnew.LoadBoard(str(board_path))
    lay = {b.GetLayerName(l): l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l)}
    doomed = {}
    for blk in re.split(r"\n(?=\[)", txt):
        if not blk.startswith(("[clearance]", "[hole_clearance]", "[hole_near_hole]", "[tracks_crossing]", "[shorting_items]")):
            continue
        for x, y, net, layer, length in re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): Track \[(.*?)\] on ([\w.]+), length ([\d.]+) mm", blk):
            p = Point(float(x), float(y))
            for t in b.GetTracks():
                if t.GetClass() == "PCB_VIA" or t.GetNetname() != net or t.GetLayer() != lay[layer]:
                    continue
                if abs(mm(t.GetLength()) - float(length)) < 0.002:
                    s = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))])
                    if s.distance(p) < 0.01:
                        doomed[t.m_Uuid.AsString()] = t
    for t in doomed.values():
        b.Delete(t)
    n = len(doomed)
    doomed.clear()
    pcbnew.SaveBoard(str(board_path), b)
    log(f"removed {n} track segments named in clearance violations")
    return n


def remove_dangling(board_path, log=print, passes=20):
    """Deletes track stubs and vias with a free end (left over after rip-ups and removals); refills the zones."""
    total = 0
    for _ in range(passes):
        b = pcbnew.LoadBoard(str(board_path))
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        b.BuildConnectivity()
        c = b.GetConnectivity()
        doomed = [t for t in b.GetTracks() if not t.IsLocked() and c.TestTrackEndpointDangling(t, False)]
        if not doomed:
            pcbnew.SaveBoard(str(board_path), b)
            break
        total += len(doomed)
        for t in doomed:
            b.Delete(t)
        del doomed
        pcbnew.SaveBoard(str(board_path), b)
    log(f"removed {total} dangling track segments and vias")
    return total
