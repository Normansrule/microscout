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


# channel template in (u, p): high-side FETs inner row, low-side FETs outer row, motor pads at the notch,
# gate driver under the FETs and the MCU nearer the centre (bottom side).
CH = [
    ("J01", 18.7, -5.6, "T"), ("J02", 18.7, -1.6, "T"), ("J03", 18.4, 6.4, "T"),
    ("Q01", 10.0, -5.0, "T"), ("Q03", 10.0, -0.7, "T"), ("Q05", 10.0, 3.6, "T"),
    ("Q02", 14.6, -6.3, "T"), ("Q04", 14.6, -1.9, "T"), ("Q06", 14.6, 7.6, "T"),
]
# MCU (U01) and gate driver (U02) sit side by side on the bottom in the same orientation, the driver's input corner
# (pins 1-3 and 22-24) facing the MCU's PWM pins (13-15 and 18-20) so the six PWM lines need no crossings.
DRIVER_OFFSET = (5.2, 2.4)          # driver centre in the MCU's own footprint frame (mm)


def to_board(back, rot, lx, ly):
    """Footprint-local vector -> board vector (KiCad 7: a bottom-side part is mirrored in y, then rotated)."""
    if back:
        ly = -ly
    t = math.radians(rot)
    return lx * math.cos(t) + ly * math.sin(t), -lx * math.sin(t) + ly * math.cos(t)


def fet_rot(ch):
    """Orientation (KiCad degrees) that points a PowerPAK's drain pad (local +x) back toward the board centre, so the
    high-side sources and the low-side drain (the phase node) face each other between the two FET rows."""
    (dx, dy), _ = FRAMES[ch]
    return (round(math.degrees(math.atan2(dy, -dx)) / 90.0 - 0.01) * 90) % 360


PWM = [("13", "3"), ("14", "2"), ("15", "1"), ("18", "24"), ("19", "23"), ("20", "22")]   # MCU pin -> driver pin


def pads_local(L, ref):
    fp = L.fps[ref]
    L.place(ref, 0, 0, 0, False)
    return {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x) - L.org[0], pcbnew.ToMM(p.GetPosition().y) - L.org[1]) for p in fp.Pads()}


def place_mcu_driver(L, P, ch):
    """MCU (U01) and gate driver (U02) on the bottom, posed so the six PWM lines between them do not cross (each
    crossing needs two vias, and the space under the power FETs has no room for vias)."""
    from shapely.geometry import LineString
    mref, dref = f"U{ch}01", f"U{ch}02"
    ml, dl = pads_local(L, mref), pads_local(L, dref)
    mx0, my0 = to_xy(ch, 7.5, 0.0)
    best = None
    for mr in (0, 90, 180, 270):
        for mdx in (-2.0, -1.0, 0.0, 1.0, 2.0):
            for mdy in (-2.0, -1.0, 0.0, 1.0, 2.0):
                mx, my = mx0 + mdx, my0 + mdy
                ms = P.shape(mref, mx, my, mr, True)
                if not P.legal(ms, True) or not P.legal(P.shape(twin_ref(mref), -mx, -my, (mr + 180) % 360, True), True):
                    continue
                mp = {k: (mx + to_board(True, mr, *v)[0], my + to_board(True, mr, *v)[1]) for k, v in ml.items()}
                for dr in (0, 90, 180, 270):
                    for k in range(24):
                        a = 2 * math.pi * k / 24
                        for r in (5.0, 5.5, 6.0, 6.5):
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
                            (fx, fy), _ = FRAMES[ch]
                            outward = (dx - mx) * fx + (dy - my) * fy
                            score = 100 * (cross + body) + sum(sg.length for sg in segs) - 0.5 * outward + 0.3 * (abs(mdx) + abs(mdy))
                            if best is None or score < best[0]:
                                best = (score, mx, my, mr, dx, dy, dr, cross, body)
    if best is None:
        raise ValueError(f"no legal MCU/driver pose for channel {ch}")
    _, mx, my, mr, dx, dy, dr, cross, body = best
    P.near(mref, mx, my, back=True, rots=(mr,), rmax=1, twin=(twin_ref(mref), rot180))
    P.near(dref, dx, dy, back=True, rots=(dr,), rmax=1, twin=(twin_ref(dref), rot180))
    L.log.append(f"channel {ch}: MCU/driver PWM lines with {cross} crossings, {body} across a chip body")


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
    # channels 2 and 1 are placed from the template; channels 3 and 4 are their 180-degree copies
    # right angles only: Freerouting connects poorly to pads turned by 45 degrees (it routed ~20 fewer connections per channel)
    any45 = (0, 90, 180, 270)
    for ch in (2, 1):
        for suffix, u, p, side in CH:
            ref = f"{suffix[0]}{ch}{suffix[1:]}"
            hx, hy = to_xy(ch, u, p)
            if ref.startswith("Q"):
                r0 = fet_rot(ch)
                rots = (r0, (r0 + 180) % 360) + tuple(r for r in any45 if r not in (r0, (r0 + 180) % 360))
            else:
                rots = any45
            P.near(ref, hx, hy, back=(side == "B"), rots=rots, twin=(twin_ref(ref), rot180))
        place_mcu_driver(L, P, ch)
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


def planes(L):
    full = L.local
    L.zone("GND", pcbnew.In1_Cu, full, clearance=0.2, solid=True)
    # VBAT plane on L3 only under the power stages, so the rest of L3 stays free for logic routing
    from shapely.ops import unary_union
    from shapely.affinity import translate
    fets = []
    for ref, fp in L.fps.items():
        if ref.startswith("Q") or ref in ("C1", "J2", "J3"):
            bb = fp.GetBoundingBox(False, False)
            ox, oy = L.org
            fets.append(box(pcbnew.ToMM(bb.GetLeft()) - ox, pcbnew.ToMM(bb.GetTop()) - oy, pcbnew.ToMM(bb.GetRight()) - ox,
                            pcbnew.ToMM(bb.GetBottom()) - oy).buffer(1.2, join_style=2))
    power = unary_union(fets).intersection(full.buffer(-0.3))
    for part in getattr(power, "geoms", [power]):
        if part.area > 4:
            L.zone("VBAT", pcbnew.In2_Cu, part.simplify(0.05), clearance=0.2, solid=True, priority=2)
    # fat copper for each motor phase on both outer layers, around the parts that carry it
    for name in L.nets:
        if "_PH_" in name:
            # pour over the power pads (FETs + motor pad), added after routing on top of the routed connection
            ppts = []
            for ref, pin in L.nets[name]:
                if not ref.startswith(("Q", "J")):
                    continue
                for pad in L.fps[ref].Pads():
                    if pad.GetNumber() == pin:
                        ppts.append((pcbnew.ToMM(pad.GetPosition().x) - L.org[0], pcbnew.ToMM(pad.GetPosition().y) - L.org[1]))
            region = MultiPoint(ppts).convex_hull.buffer(0.7, join_style=2).intersection(full.buffer(-0.3))
            if region.geom_type == "Polygon" and region.area > 1:
                L.zone(name, pcbnew.F_Cu, region, clearance=0.2, priority=3, solid=True, late=True)
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


if __name__ == "__main__" and "--finish-only" in sys.argv:
    from report import refinish
    L = Layout(BOARD_NAME, NETLIST, OUT_PCB, layers=LAYERS, thickness=1.0)
    L.rules(CLASSES, default=DEFAULT)
    refinish(L, PLANE_ZONE)
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
    finish(L, route=False, plane_zone=lambda z: (z.GetNetname() == "GND" and z.IsOnLayer(pcbnew.In1_Cu))
           or (z.GetNetname() == "VBAT" and z.IsOnLayer(pcbnew.In2_Cu)))
