# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""4-in-1 ESC layout (4 layers, 1.0 mm). Run with KiCad's Python: python3 tools/pcb/esc.py

Board frame: x forward, y right, origin = frame centre, top view (D-060). Each motor channel sits in
the quadrant facing its motor (Betaflight order 1 RR, 2 FR, 3 RL, 4 FL): power FETs and motor pads on
top near the duct notch, MCU and gate driver on the bottom.
Stackup: L1 FETs + phase pours, L2 solid GND plane, L3 solid VBAT plane, L4 logic + GND pour.
"""
import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pcbnew  # noqa: E402
from shapely.geometry import MultiPoint, Point, box  # noqa: E402
from layout import Layout, REPO  # noqa: E402
from placer import Placer  # noqa: E402
from report import finish  # noqa: E402

A = 95 / math.sqrt(2) / 2
W, NOTCH = 40.0, 28.0
HOLES = [(sx * 8.0, sy * 12.5, 3.0) for sx in (-1, 1) for sy in (-1, 1)]
# quadrant of each channel: rotation k (x 90 deg) that maps the front-right quadrant onto it
QUAD = {1: 1, 2: 0, 3: 2, 4: 3}                 # 1 RR, 2 FR, 3 RL, 4 FL

CLASSES = {
    # FET-to-motor-pad copper is a late pour per phase (planes()); Freerouting draws the connection at this width first
    # (Freerouting cannot neck a track down at a fine-pitch pin, so this must fit the 0.5 mm driver pitch)
    "Phase": dict(track=0.25, clearance=0.12, nets=[r"/Motor \d/M\d_PH_[ABC]"]),
    "Power": dict(track=0.6, clearance=0.2, nets=[r"VBAT"]),
    "Supply": dict(track=0.2, clearance=0.1, nets=[r"VDRV", r"\+3V3_ESC"]),
    "Switch": dict(track=0.3, clearance=0.12, nets=[r"/Power.*/.*SW.*"]),
    "Gate": dict(track=0.15, clearance=0.1, nets=[r"/Motor \d/M\d_G[HL]_[ABC]", r"/Motor \d/M\d_[HL]O_[ABC]", r"/Motor \d/M\d_VB_[ABC]"]),
}
DEFAULT = dict(track=0.1, clearance=0.1, via_d=0.45, via_drill=0.25)   # same as the FC (JLCPCB price tier UNCONFIRMED)
CHAN = re.compile(r"([A-Z]+)([1-4])(\d\d)")
TWIN = {2: 3, 1: 4}            # channel 3 is channel 2 turned 180 degrees about the centre, channel 4 is channel 1


def chan(ref):
    m = CHAN.fullmatch(ref)
    return int(m.group(2)) if m else None


def twin_ref(ref):
    m = CHAN.fullmatch(ref)
    return f"{m.group(1)}{TWIN[int(m.group(2))]}{m.group(3)}"


def rot180(x, y, rot):
    return -x, -y, (rot + 180) % 360


def outline():
    b = box(-W / 2, -W / 2, W / 2, W / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.difference(Point(sx * A, sy * A).buffer(NOTCH, 256))
    return b


S2 = math.sqrt(0.5)
# Each channel uses a frame (u outward along its motor diagonal, p across it). The p direction is chosen
# per quadrant so that the quadrant's mounting hole always sits at u = 14.5, p = +3.2 mm.
FRAMES = {   # channel: (d, p)
    2: ((S2, S2), (-S2, S2)),      # front-right
    4: ((S2, -S2), (-S2, -S2)),    # front-left (p mirrored)
    1: ((-S2, S2), (S2, S2)),      # rear-right (p mirrored)
    3: ((-S2, -S2), (S2, -S2)),    # rear-left
}


def to_xy(ch, u, p):
    (dx, dy), (px, py) = FRAMES[ch]
    return u * dx + p * px, u * dy + p * py


# Power cells (D-063 rev 2). One cell per motor phase, in its own frame (x along the cell, y toward the gates):
#   [GND strip | low-side FET | motor pad | high-side FET | VBAT strip]
# The low-side drain, the motor pad and the high-side sources face each other, so the whole phase node is one
# solid copper block drawn before routing (PH_POLY). Both gates (pin 4) point to +y, away from the power copper.
CELL_PARTS = [("LS", 0.0, 0.0, 0), ("J", 2.86, 0.0, 0), ("HS", 5.72, 0.0, 0)]   # (role, x, y, rot) in the cell frame
PH_POLY = [(-0.35, -1.9), (4.78, -1.9), (4.78, 0.58), (3.55, 0.58), (3.55, 1.2), (-0.35, 1.2)]
GND_POLY = [(-3.4, -1.9), (-0.94, -1.9), (-0.94, 0.58), (-3.4, 0.58)]
VBAT_POLY = [(5.3, -1.9), (8.3, -1.9), (8.3, 1.9), (5.3, 1.9)]
# where the strips' stitching vias go (clear of the FET pads; no via in a pad): kept free of parts on the bottom
GND_VIAS = [(-3.4, -1.9), (-1.95, -1.9), (-1.95, 0.58), (-3.4, 0.58)]
VBAT_VIAS = [(7.15, -1.9), (8.3, -1.9), (8.3, 1.9), (7.15, 1.9)]
TAP = (1.9, -0.5)          # phase tap via, between the low-side drain pad and the motor pad
# Cell poses (origin x, y, KiCad rotation) per channel, phases A, B, C. Channels 3 and 4 are 180-degree copies.
CELLS = {
    2: [(11.0, 2.4, 0), (10.4, 7.4, 0), (2.5, 13.9, 90)],
    1: [(-15.9, 2.4, 0), (-15.3, 7.4, 0), (-2.5, 9.0, 270)],
}


def cell_xy(pose, x, y):
    ox, oy, r = pose
    t = math.radians(r)
    return ox + x * math.cos(t) + y * math.sin(t), oy - x * math.sin(t) + y * math.cos(t)


def cell_refs(ch, i):
    return {"HS": f"Q{ch}0{2 * i + 1}", "LS": f"Q{ch}0{2 * i + 2}", "J": f"J{ch}0{i + 1}"}


def all_cells():
    """(channel, phase index, pose) for all four channels; 3 and 4 are the 180-degree copies of 2 and 1."""
    out = []
    for ch, poses in CELLS.items():
        for i, (ox, oy, r) in enumerate(poses):
            out.append((ch, i, (ox, oy, r)))
            out.append((TWIN[ch], i, (-ox, -oy, (r + 180) % 360)))
    return out


def place_cells(P, ch):
    """Exact poses (the parts of one cell sit closer than the placer's spacing); L.overlaps() checks the result."""
    for i, pose in enumerate(CELLS[ch]):
        refs = cell_refs(ch, i)
        for role, x, y, rot in CELL_PARTS:
            px, py = cell_xy(pose, x, y)
            r = (pose[2] + rot) % 360
            P.fix(refs[role], px, py, r, back=False, check=False)
            P.fix(twin_ref(refs[role]), -px, -py, (r + 180) % 360, back=False, check=False)


# MCU (U01) and gate driver (U02) sit side by side on the bottom in the same orientation, the driver's input corner
# (pins 1-3 and 22-24) facing the MCU's PWM pins (13-15 and 18-20) so the six PWM lines need no crossings.
DRIVER_OFFSET = (5.2, 2.4)          # driver centre in the MCU's own footprint frame (mm)


def to_board(back, rot, lx, ly):
    """Footprint-local vector -> board vector (KiCad 7: a bottom-side part is mirrored in y, then rotated)."""
    if back:
        ly = -ly
    t = math.radians(rot)
    return lx * math.cos(t) + ly * math.sin(t), -lx * math.sin(t) + ly * math.cos(t)


PWM = [("13", "3"), ("14", "2"), ("15", "1"), ("18", "24"), ("19", "23"), ("20", "22")]   # MCU pin -> driver pin


def pads_local(L, ref):
    fp = L.fps[ref]
    L.place(ref, 0, 0, 0, False)
    return {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x) - L.org[0], pcbnew.ToMM(p.GetPosition().y) - L.org[1]) for p in fp.Pads()}


def place_mcu_driver(L, P, ch, avoid=()):
    """MCU (U01) and gate driver (U02) on the bottom, posed so the six PWM lines between them do not cross (each
    crossing needs two vias, and the space under the power FETs has no room for vias)."""
    from shapely.geometry import LineString
    mref, dref = f"U{ch}01", f"U{ch}02"
    ml, dl = pads_local(L, mref), pads_local(L, dref)
    # the driver should sit near the six FET gates of its channel
    gates = []
    for i in range(3):
        for role in ("HS", "LS"):
            for pad in L.fps[cell_refs(ch, i)[role]].Pads():
                if pad.GetNumber() == "4":
                    gates.append((pcbnew.ToMM(pad.GetPosition().x) - L.org[0], pcbnew.ToMM(pad.GetPosition().y) - L.org[1]))
    gx, gy = sum(g[0] for g in gates) / 6, sum(g[1] for g in gates) / 6
    sx = 1 if ch in (2, 4) else -1                    # quadrant of this channel (x sign); all four are y > 0 or y < 0
    sy = 1 if ch in (1, 2) else -1
    from shapely.ops import unary_union
    from shapely.affinity import translate
    av = translate(unary_union(list(avoid)), *L.org) if avoid else None
    best = None
    grid = [(sx * x, sy * y) for x in range(1, 19) for y in range(1, 19)]
    for mr in (0, 90, 180, 270):
        for mx, my in grid:
                mdx = mdy = 0.0
                ms = P.shape(mref, mx, my, mr, True)
                if not P.legal(ms, True) or not P.legal(P.shape(twin_ref(mref), -mx, -my, (mr + 180) % 360, True), True):
                    continue
                mp = {k: (mx + to_board(True, mr, *v)[0], my + to_board(True, mr, *v)[1]) for k, v in ml.items()}
                for dr in (0, 90, 180, 270):
                    for k in range(24):
                        a = 2 * math.pi * k / 24
                        for r in (4.5, 5.0, 5.5, 6.0, 6.5, 7.0):
                            dx, dy = mx + r * math.cos(a), my + r * math.sin(a)
                            ds = P.shape(dref, dx, dy, dr, True)
                            if ds.buffer(P.gap).intersects(ms) or not P.legal(ds, True):
                                continue
                            ts = P.shape(twin_ref(dref), -dx, -dy, (dr + 180) % 360, True)
                            if not P.legal(ts, True) or ts.buffer(P.gap).intersects(ms):
                                continue
                            dp = {k2: (dx + to_board(True, dr, *v)[0], dy + to_board(True, dr, *v)[1]) for k2, v in dl.items()}
                            segs = [LineString([mp[m], dp[d]]) for m, d in PWM]
                            cross = sum(1 for i in range(6) for j in range(i + 1, 6) if segs[i].crosses(segs[j]))
                            # lines must not run across either chip body
                            body = sum(1 for sg in segs if sg.crosses(ms.buffer(-0.6)) or sg.crosses(ds.buffer(-0.6)))
                            hit = 0.0 if av is None else (ms.intersection(av).area + ds.intersection(av).area)
                            score = (100 * (cross + body) + sum(sg.length for sg in segs) + 1.5 * math.hypot(dx - gx, dy - gy)
                                     + 20 * hit)
                            if best is None or score < best[0]:
                                best = (score, mx, my, mr, dx, dy, dr, cross, body, hit)
    if best is None:
        raise ValueError(f"no legal MCU/driver pose for channel {ch}")
    _, mx, my, mr, dx, dy, dr, cross, body, _hit = best
    P.near(mref, mx, my, back=True, rots=(mr,), rmax=1, twin=(twin_ref(mref), rot180))
    P.near(dref, dx, dy, back=True, rots=(dr,), rmax=1, twin=(twin_ref(dref), rot180))
    L.log.append(f"channel {ch}: MCU/driver PWM lines with {cross} crossings, {body} across a chip body, "
                 f"{best[9]:.2f} mm2 over via areas")


BOARD_NAME, LAYERS = "esc", 4
NETLIST, OUT_PCB = REPO / "review/G2/netlists/microscout-esc.net", REPO / "hardware/esc-pcb/microscout-esc.kicad_pcb"


def build():
    L = Layout(BOARD_NAME, NETLIST, OUT_PCB, layers=LAYERS, thickness=1.0)
    poly = outline()
    L.outline(poly, holes=HOLES)
    L.rules(CLASSES, default=DEFAULT)
    P = Placer(L, margin=0.3, gap=0.3)    # room for escape vias between parts
    for x, y, d in HOLES:
        P.block(Point(x, y).buffer(d / 2 + 0.6, 32))
    # centre parts (the battery pads sit on the forward/back axis, mirror images of each other)
    P.fix("C1", 0.0, 0.0, 90, back=False)
    P.fix("J2", -5.7, 0.0, 0, back=False)
    P.fix("J3", 5.7, 0.0, 0, back=False)
    P.near("J1", 0.0, 0.0, back=True, rots=(0, 180, 90, 270))          # link cable leaves from the bottom centre
    P.near("U1", 0.0, 5.0, back=True)
    P.near("L1", 0.0, -5.0, back=True)
    # channels 2 and 1: power cells, then MCU + driver; channels 3 and 4 are their 180-degree copies
    for ch in (2, 1):
        place_cells(P, ch)
    # keep other parts off the cells' copper on the top (the vias on the bottom are placed later, around the parts)
    for ch, i, pose in all_cells():
        for pts in (PH_POLY, GND_POLY, VBAT_POLY):
            P.block(cell_poly(pose, pts).buffer(0.2), sides=(False,))
    # room for the cells' vias on the bottom: the MCU/driver search avoids the strips' via areas and the phase taps
    # where it can (a penalty), then all other parts are kept off them
    via_areas = []
    for ch, i, pose in all_cells():
        via_areas += [cell_poly(pose, GND_VIAS), cell_poly(pose, VBAT_VIAS), Point(*cell_xy(pose, *TAP)).buffer(0.5)]
    for ch in (2, 1):
        place_mcu_driver(L, P, ch, avoid=via_areas)
    for g in via_areas:
        P.block(g, sides=(True,))
    failed = []
    for ch in (2, 1):
        rest = [r for r in L.fps if chan(r) == ch and r not in P.placed_refs()]
        for ref in sorted(rest, key=lambda r: (not r.startswith(("C", "R", "D")), r)):
            tgt = P.target(ref, max_net=12)
            if tgt is None:
                o = L.fps[f"U{ch}01"].GetPosition()
                tgt = (pcbnew.ToMM(o.x) - L.org[0], pcbnew.ToMM(o.y) - L.org[1])
            for back in (True, False):
                try:
                    P.near(ref, tgt[0], tgt[1], back=back, twin=(twin_ref(ref), rot180))
                    break
                except ValueError as e:
                    err = e
            else:
                failed.append(ref)
                print("could not place", ref, err)
    for ref in sorted(r for r in L.fps if r not in P.placed_refs()):
        tgt = P.target(ref, max_net=30) or (0.0, 0.0)
        try:
            P.near(ref, tgt[0], tgt[1], back=True)
        except ValueError:
            try:
                P.near(ref, tgt[0], tgt[1], back=False)
            except ValueError as e:
                failed.append(ref)
                print("could not place", ref, e)
    L.placer = P
    return L, P, failed


def cell_poly(pose, pts):
    from shapely.geometry import Polygon
    return Polygon([cell_xy(pose, x, y) for x, y in pts])


def planes(L):
    """Copper drawn before routing: per power cell a phase block, a GND strip and a VBAT strip on L1 (with stitching
    vias to the L2 GND plane and the L3 VBAT plane, and one phase tap via); no-tracks areas over them on L1 and L3."""
    from shapely.ops import unary_union
    full = L.local
    inside = full.buffer(-0.3)
    L.zone("GND", pcbnew.In1_Cu, full, clearance=0.2, solid=True)
    vbat_in2, keep = [], []
    for ch, i, pose in all_cells():
        ph = f"/Motor {ch}/M{ch}_PH_{'ABC'[i]}"
        for net, pts in ((ph, PH_POLY), ("GND", GND_POLY), ("VBAT", VBAT_POLY)):
            g = cell_poly(pose, pts).intersection(inside)
            L.zone(net, pcbnew.F_Cu, g, clearance=0.2, priority=5, solid=True, name=f"cell {net}")
            keep.append(g)
        # one tap via from the phase block to the bottom, at the first spot clear of the bottom parts
        # (at TAP if the bottom is clear there, else anywhere in the phase block clear of every pad)
        if not (L.stitch(ph, Point(*cell_xy(pose, *TAP)).buffer(0.6), pitch=0.25, max_vias=1, step=0.05)
                or L.stitch(ph, cell_poly(pose, PH_POLY).buffer(-0.05), pitch=0.25, max_vias=1, step=0.05)):
            raise SystemExit(f"no room for the {ph} tap via")
        L.stitch("GND", cell_poly(pose, GND_POLY).buffer(-0.1), pitch=0.75, step=0.05)
        L.stitch("VBAT", cell_poly(pose, VBAT_POLY).buffer(-0.1), pitch=0.75, step=0.05)
        vbat_in2.append(cell_poly(pose, [(-3.4, -1.9), (8.3, -1.9), (8.3, 1.9), (-3.4, 1.9)]).buffer(0.6, join_style=2))
    # L3 VBAT plane: under every cell and the centre (battery pads, bulk capacitor), closed into one piece
    centre = box(-7.6, -3.6, 7.6, 3.6)
    v = unary_union(vbat_in2 + [centre]).buffer(1.6, join_style=2).buffer(-1.6, join_style=2).intersection(inside)
    for part in getattr(v, "geoms", [v]):
        if part.area > 4:
            L.zone("VBAT", pcbnew.In2_Cu, part.simplify(0.05), clearance=0.2, solid=True, priority=2, name="cell VBAT plane")
    # battery pads and bulk capacitor: short copper to their stitching vias
    for ref, net in (("J2", "VBAT"), ("J3", "GND")):
        bb = L.fps[ref].GetBoundingBox(False, False)
        ox, oy = L.org
        g = box(pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy, pcbnew.ToMM(bb.GetRight()) - ox,
                pcbnew.ToMM(bb.GetBottom()) - oy).buffer(0.8, join_style=2)
        L.zone(net, pcbnew.F_Cu, g.intersection(inside), clearance=0.2, priority=5, solid=True, name=f"centre {net}")
        L.stitch(net, g.difference(g.buffer(-0.8, join_style=2)).buffer(-0.05), pitch=0.9)
    # no tracks of any net across the power copper on L1 and L3 (the cells' own vias are already placed)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.In2_Cu)
    for g in keep:
        if g.area > 0.5:
            L.keepout(ls, g, tracks=True, vias=False, pours=False, name="power cell: no tracks")
    L.zone("VBAT", pcbnew.F_Cu, full, clearance=0.25, priority=1, solid=True, late=True)
    L.zone("GND", pcbnew.B_Cu, full, clearance=0.25, priority=1, solid=True, late=True)
    L.zone("GND", pcbnew.In2_Cu, full, clearance=0.25, priority=0, solid=True, late=True)   # fills what the logic leaves on L3


def centre_images(L, P):
    """Keep-outs at the 180-degree images of the centre parts, so channel copper copied by rotation cannot land on them."""
    from shapely.affinity import rotate
    from shapely.affinity import translate
    zs = []
    ox, oy = L.org
    for back in (False, True):
        for ref, poly in P.placed[back]:
            if chan(ref) is not None or ref.startswith(("MH", "H")) or ref not in L.fps:
                continue
            img = translate(rotate(translate(poly, -ox, -oy), 180, origin=(0, 0)), 0, 0).buffer(0.15)
            ls = pcbnew.LSET()
            ls.AddLayer(pcbnew.B_Cu if back else pcbnew.F_Cu)
            zs.append(L.keepout(ls, img, tracks=True, vias=True, pours=False, name=f"image of {ref}"))
    return zs


PLANE_ZONE = lambda z: (z.GetNetname() == "GND" and z.IsOnLayer(pcbnew.In1_Cu)) or (z.GetNetname() == "VBAT" and z.IsOnLayer(pcbnew.In2_Cu))
# power copper on L1 that no other net may cross (Freerouting may drop vias through it; they are removed and re-routed)
ISLAND = lambda z: z.GetZoneName().startswith(("cell ", "centre ")) and "plane" not in z.GetZoneName()


if __name__ == "__main__" and "--finish-only" in sys.argv:
    from report import refinish
    L = Layout(BOARD_NAME, NETLIST, OUT_PCB, layers=LAYERS, thickness=1.0)
    L.rules(CLASSES, default=DEFAULT)
    refinish(L, PLANE_ZONE, island=ISLAND)
    sys.exit(0)

if __name__ == "__main__":
    L, P, failed = build()
    if failed:
        raise SystemExit(f"placement failed for {failed}")
    planes(L)
    L.plane_layers = [pcbnew.In1_Cu]           # Freerouting: tracks on the L2 GND plane cost 50x (layout._rules_file)
    passes = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--passes=")), 25))
    if "--no-route" not in sys.argv:
        # route channel 2, copy it onto channel 3; route channel 1, copy it onto channel 4; then the shared nets.
        # In the channel stages the shared nets (GND, VBAT, VDRV, +3V3_ESC) are routed only between that channel's pins.
        imgs = centre_images(L, P)
        for ch in (2, 1):
            before = L.track_ids()
            L.autoroute(passes=passes, timeout=3600, attempts=1, pin_ok=lambda n, r, ch=ch: chan(r) == ch)
            new = L.track_ids() - before
            for t in L.board.GetTracks():
                t.SetLocked(True)
            L.copy_rotated(new, lambda n, ch=ch: n.replace(f"/Motor {ch}/M{ch}_", f"/Motor {TWIN[ch]}/M{TWIN[ch]}_"))
            L.log.append(f"channel {ch} stage: {L.unrouted()} connections open on the board after the copy")
            print(L.log[-1], flush=True)
        for z in imgs:
            L.board.Remove(z)
        L.autoroute(passes=passes, timeout=3600, attempts=2)
        L.routed_nets = sorted({t.GetNetname() for t in L.board.GetTracks() if t.GetNetname()})
    L.clear_plane_layers([pcbnew.In1_Cu])     # L2 stays a solid GND plane (Freerouting may have used it)
    finish(L, route=False, plane_zone=PLANE_ZONE, island=ISLAND)
