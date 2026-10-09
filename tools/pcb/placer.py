# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""A small legalising placer for dense boards.

Big parts are placed by hand (exact coordinates in the board script). Everything else gets a hint
(a point, or "near the pads I connect to") and is moved to the nearest legal spot: inside the outline
with an edge margin, clear of every courtyard on the same side, clear of keepouts and holes.
"""
from __future__ import annotations

import math

import pcbnew
from shapely.affinity import rotate as srotate, translate as stranslate
from shapely.geometry import Point
from shapely.ops import unary_union

from common import courtyard, mm


class Placer:
    def __init__(self, L, margin=0.3, gap=0.08, power_nets=("GND",)):
        self.L = L
        self.inside = L.poly.buffer(-margin)
        self.gap = gap
        self.placed = {False: [], True: []}        # side (flipped?) -> list of (ref, polygon)
        self.blocked = {False: [], True: []}       # extra keepouts per side
        self.power_nets = set(power_nets)
        self.local = {}                            # ref -> courtyard in footprint-local coordinates (rot 0)

    def block(self, poly, sides=(False, True)):
        """poly in board-relative coordinates (same frame as L.place)."""
        P = self.L.P(poly)
        for s in sides:
            self.blocked[s].append(P)

    def _local_cy(self, ref, back):
        """Courtyard at the origin with orientation 0 on the given side, read from KiCad itself."""
        key = (ref, back)
        if key not in self.local:
            fp = self.L.fps[ref]
            pos, rot, flip = fp.GetPosition(), fp.GetOrientationDegrees(), fp.IsFlipped()
            if flip != back:
                fp.Flip(pos, False)
            fp.SetPosition(pcbnew.VECTOR2I(0, 0)); fp.SetOrientationDegrees(0)
            self.local[key] = courtyard(fp, pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
            if flip != back:
                fp.Flip(fp.GetPosition(), False)
            fp.SetPosition(pos); fp.SetOrientationDegrees(rot)
        return self.local[key]

    def shape(self, ref, x, y, rot, back):
        """Courtyard polygon (board coordinates incl. page origin) for a candidate pose."""
        c = srotate(self._local_cy(ref, back), -rot, origin=(0, 0))   # KiCad angles: counter-clockwise, y down
        ox, oy = self.L.org
        return stranslate(c, x + ox, y + oy)

    def legal(self, poly, back, ignore_edge=False):
        if not ignore_edge and not self.inside.contains(poly):
            return False
        g = poly.buffer(self.gap)
        for _, p in self.placed[back]:
            if g.intersects(p):
                return False
        for p in self.blocked[back]:
            if g.intersects(p):
                return False
        return True

    def _block_holes(self, ref, back):
        """Plated or unplated holes of a part also occupy the other side of the board."""
        from shapely.geometry import Point
        for pad in self.L.fps[ref].Pads():
            if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                p = pad.GetPosition()
                r = max(mm(pad.GetSize().x), mm(pad.GetSize().y)) / 2 + 0.25
                self.blocked[not back].append(Point(mm(p.x), mm(p.y)).buffer(r, 16))

    def fix(self, ref, x, y, rot=0, back=False, check=True, ignore_edge=False):
        """Place exactly; complain if illegal."""
        poly = self.shape(ref, x, y, rot, back)
        if check and not self.legal(poly, back, ignore_edge):
            raise ValueError(f"{ref} at ({x}, {y}) rot {rot} {'back' if back else 'top'} is not legal")
        self.L.place(ref, x, y, rot, back)
        self.placed[back].append((ref, poly))
        self._block_holes(ref, back)
        return poly

    def near(self, ref, x, y, back=False, rots=(0, 90, 180, 270), step=0.25, rmax=25.0, twin=None):
        """Nearest legal pose to (x, y). twin = (ref2, f): f maps a pose (x, y, rot) to the pose of ref2 (same side);
        both must be legal and clear of each other, and both are placed (used for 180-degree channel copies)."""
        best = None
        n = int(rmax / step)
        for r in range(0, n + 1):
            ring = [(0, 0)] if r == 0 else [(dx, dy) for dx in range(-r, r + 1) for dy in (-r, r)] + \
                [(dx, dy) for dx in (-r, r) for dy in range(-r + 1, r)]
            ring.sort(key=lambda d: d[0] ** 2 + d[1] ** 2)
            for dx, dy in ring:
                px, py = x + dx * step, y + dy * step
                for rot in rots:
                    poly = self.shape(ref, px, py, rot, back)
                    if not self.legal(poly, back):
                        continue
                    if twin:
                        tx, ty, trot = twin[1](px, py, rot)
                        tpoly = self.shape(twin[0], tx, ty, trot, back)
                        if not self.legal(tpoly, back) or tpoly.buffer(self.gap).intersects(poly):
                            continue
                    d = math.hypot(dx * step, dy * step)
                    if best is None or d < best[0]:
                        best = (d, px, py, rot)
                if best and best[0] <= r * step:
                    break
            if best and best[0] <= r * step:
                break
        if not best:
            raise ValueError(f"no legal spot for {ref} near ({x:.1f}, {y:.1f})")
        _, px, py, rot = best
        self.L.place(ref, px, py, rot, back)
        self.placed[back].append((ref, self.shape(ref, px, py, rot, back)))
        self._block_holes(ref, back)
        if twin:
            tx, ty, trot = twin[1](px, py, rot)
            self.L.place(twin[0], tx, ty, trot, back)
            self.placed[back].append((twin[0], self.shape(twin[0], tx, ty, trot, back)))
            self._block_holes(twin[0], back)
        return px, py, rot

    # ---------------------------------------------------------------- connectivity helpers
    def placed_refs(self):
        return {r for side in self.placed.values() for r, _ in side}

    def target(self, ref, max_net=10):
        """Mean position of already-placed pads sharing a (non-ground, small) net with ref."""
        fp = self.L.fps[ref]
        done = self.placed_refs()
        pts = []
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not net or net in self.power_nets:
                continue
            nodes = self.L.nets.get(net, [])
            if len(nodes) > max_net:
                continue
            for r2, pin in nodes:
                if r2 == ref or r2 not in done:
                    continue
                for p2 in self.L.fps[r2].Pads():
                    if p2.GetNumber() == pin:
                        pts.append((mm(p2.GetPosition().x) - self.L.org[0], mm(p2.GetPosition().y) - self.L.org[1]))
        if not pts:
            return None
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    def side_of(self, ref):
        return any(r == ref for r, _ in self.placed[True])
