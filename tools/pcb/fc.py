# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Flight-controller layout (4 layers, 1.0 mm). Run with KiCad's Python: python3 tools/pcb/fc.py

Board frame: x = forward (nose), y = right, origin = frame centre, top view (D-060).
Stackup (6 layers, D-062): L1 signals + parts, L2 solid GND plane, L3 and L4 signals (late +3V3 pour on L4),
L5 solid GND plane, L6 signals + parts. The 4-layer version left 24-66 connections unrouted.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "sch"))
import pcbnew  # noqa: E402
import sexpr  # noqa: E402
from shapely.geometry import Point, box  # noqa: E402
from layout import Layout, REPO  # noqa: E402
from placer import Placer  # noqa: E402
from report import finish  # noqa: E402

A = 95 / math.sqrt(2) / 2          # motor offset on x and y (mm)
W, NOTCH, REAR = 52.0, 27.1, -18.5  # D-060
HOLES = [(sx * 8.0, sy * 12.5, 3.0) for sx in (-1, 1) for sy in (-1, 1)]
MODULE = (-5.75, 0.0)               # ESP32-S3 module centre; antenna end flush with the rear edge

GND_LIKE = {"GND"}
RAILS = {"+3V3", "VBAT", "VLOGIC", "+5V", "VDRV", "VBUS", "VBAT_RAW", "+2V8", "+1V2"}

CLASSES = {
    # the 30 A path itself is copper pours on all layers (planes() below); these widths are for the branches
    "HighCurrent": dict(track=0.6, clearance=0.2, nets=[r"/Power/VBAT_RAW"]),
    "Power": dict(track=0.25, clearance=0.1, nets=[r"VBAT", r"VLOGIC", r"\+5V", r"\+3V3", r"VDRV", r"VBUS", r"/Power/CHG_.*(SW|PMID|SNS)",
                                                     r"/Power/SW_.*", r"/Power/BOOST_SW", r"/Power/VDRV_SW", r"\+2V8", r"\+1V2"]),
    "USB": dict(track=0.2, clearance=0.15, nets=[r".*USB_(C_)?D[PN]"]),
}
DEFAULT = dict(track=0.1, clearance=0.1, via_d=0.45, via_drill=0.25)   # 0.25 mm vias: JLCPCB price tier UNCONFIRMED (G4)


def outline():
    b = box(-W / 2, -W / 2, W / 2, W / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.difference(Point(sx * A, sy * A).buffer(NOTCH, 256))
    return b.intersection(box(REAR, -40, 40, 40))


def schematic_positions():
    pos = {}
    for f in (REPO / "hardware/drone-pcb").glob("*.kicad_sch"):
        root = sexpr.parse(f.read_text())[0]
        for s in root[1:]:
            if isinstance(s, list) and s and s[0] == "symbol":
                at = next(c for c in s if isinstance(c, list) and c[0] == "at")
                ref = next((c[2] for c in s if isinstance(c, list) and c[0] == "property" and c[1] == "Reference"), None)
                if ref and not ref.startswith("#"):
                    pos[ref] = (f.stem, float(at[1]), float(at[2]))
    return pos


# Hand-placed parts: ref -> (x, y, rot, back, exact?)
FIXED = {
    "U1": (MODULE[0], MODULE[1], 90, False, True),
    "J3": (14.0, 0.0, 90, False, True),        # FPC, insertion side forward (UNCONFIRMED: FH12 front/back)
    "J1": (0.0, -22.35, 180, False, True),     # USB-C, mouth flush with the left edge
}
# Anchors: ref -> (x, y, side 'T'/'B', rotations)
ANCHORS = [
    ("J2", -1.5, 21.0, "T", (0,)), ("RS1", -1.5, 15.2, "T", (0,)), ("J8", 1.0, 15.5, "B", (90,)), ("J9", 1.0, 21.5, "B", (90,)),
    ("U9", 5.5, 15.5, "T", (0, 90)), ("J6", 5.5, 21.0, "T", (0,)), ("J7", -7.0, 19.0, "B", (0, 180)),
    ("U2", 10.5, -12.0, "T", (0, 90)), ("L1", 14.0, -9.0, "T", (0, 90)),
    ("U22", 5.0, -16.5, "T", (0, 90)), ("SW1", -11.0, -16.0, "T", (0, 90)), ("SW2", -11.0, -20.0, "T", (0, 90)),
    ("SW3", -11.0, 17.0, "T", (0, 90)),
    ("U6", 9.5, 11.5, "T", (0, 90)), ("U7", 9.5, -8.0, "T", (0, 90)),
    ("LED1", 9.0, -22.0, "T", (0,)), ("LED2", 9.0, 22.0, "T", (0,)), ("LED3", -11.0, 15.0, "T", (0,)), ("LED4", -11.0, -14.0, "T", (0,)),
    ("U12", 0.0, 0.0, "B", (0,)), ("U13", -4.5, 3.5, "B", (0, 90)), ("U14", -7.0, -7.0, "B", (0, 90)),
    ("U10", 3.5, -8.0, "B", (0, 90)), ("U11", 8.0, -5.0, "B", (0, 90)),
    ("U3", 10.0, 7.0, "B", (0, 90)), ("L2", 13.0, 7.0, "B", (0, 90)), ("U4", 14.5, 2.0, "B", (0, 90)), ("L3", 18.0, 2.0, "B", (0, 90)),
    ("U25", 10.0, 13.0, "B", (0, 90)), ("L4", 13.0, 13.5, "B", (0, 90)), ("U24", 6.0, 12.0, "B", (0, 90)),
    ("D2", 6.5, -17.0, "B", (0, 90)), ("D3", 11.0, -14.0, "B", (0, 90)),
    ("U8", -10.0, 16.0, "B", (0, 90)), ("U23", -6.5, 11.0, "B", (0, 90)), ("Q5", -9.0, 9.0, "B", (0, 90)),
    ("J10", 17.0, -4.0, "B", (90,)), ("J14", 22.5, 0.0, "B", (90,)), ("J11", -2.0, -15.0, "B", (0,)),
    ("J12", 3.0, 24.0, "B", (0,)), ("J13", -11.0, 0.0, "B", (90,)), ("J4", 17.0, 7.5, "B", (90,)), ("J5", -9.5, -5.0, "B", (90,)),
    ("BZ1", 14.5, -11.5, "B", (0,)), ("Q3", 11.5, -9.0, "B", (0, 90)), ("D1", 17.5, -9.5, "B", (0, 90)),
    ("U21", 5.0, 20.0, "B", (0, 90)), ("D4", 13.0, -15.0, "T", (0, 90)),
]


BOARD_NAME, LAYERS = "fc", 6
NETLIST, OUT_PCB = REPO / "review/G2/netlists/microscout-fc.net", REPO / "hardware/drone-pcb/microscout-fc.kicad_pcb"


def build():
    L = Layout(BOARD_NAME, NETLIST, OUT_PCB, layers=LAYERS, thickness=1.0)
    poly = outline()
    L.outline(poly, holes=HOLES)
    L.rules(CLASSES, default=DEFAULT)
    P = Placer(L, margin=0.3, gap=0.35)   # room for escape vias between parts (0.1 left 20+ connections unroutable)
    for x, y, d in HOLES:
        P.block(Point(x, y).buffer(d / 2 + 0.6, 32))
    # antenna keep-out (the module footprint carries the same rule area; block it for placement on both sides)
    P.block(box(-40, -40, MODULE[0] - 6.75, 40), sides=(True,))
    for ref, (x, y, rot, back, exact) in FIXED.items():
        P.fix(ref, x, y, rot, back, check=False)
    # the USB-C shell legs go through the board: keep the bottom clear under it
    P.block(box(-5.4, -26.0, 5.4, -17.0), sides=(True,))
    for ref, x, y, side, rots in ANCHORS:
        try:
            P.near(ref, x, y, back=(side == "B"), rots=rots)
        except ValueError:
            P.near(ref, x, y, back=(side == "B"), rots=(0, 90, 180, 270), rmax=40)

    # remaining parts (passives): next to the part they belong to
    spos = schematic_positions()
    owners = [r for r in L.fps if r in P.placed_refs()]
    rest = [r for r in L.fps if r not in P.placed_refs()]

    def owner(ref):
        best, score = None, 0.0
        for pad in L.fps[ref].Pads():
            n = pad.GetNetname()
            if not n or n in GND_LIKE:
                continue
            nodes = L.nets.get(n, [])
            w = 1.0 / len(nodes) if n not in RAILS else 0.02 / len(nodes)
            for r2, _ in nodes:
                if r2 in owners and r2 != ref:
                    # schematic proximity breaks ties between rails shared by many parts
                    if ref in spos and r2 in spos and spos[ref][0] == spos[r2][0]:
                        dd = math.hypot(spos[ref][1] - spos[r2][1], spos[ref][2] - spos[r2][2])
                        ww = w + 0.5 / (1.0 + dd / 5.0) * (0.02 if n in RAILS else 0.0) + (0.3 / (1.0 + dd / 5.0) if n in RAILS else 0.0)
                    else:
                        ww = w
                    if ww > score:
                        best, score = r2, ww
        if best is None and ref in spos:          # only GND + rails: nearest owner on the schematic sheet
            sh, sx, sy = spos[ref]
            cands = [(math.hypot(sx - spos[o][1], sy - spos[o][2]), o) for o in owners if o in spos and spos[o][0] == sh]
            if cands:
                best = min(cands)[1]
        return best

    # place in order of how strongly they are tied to an owner
    order = sorted(rest, key=lambda r: (not r.startswith(("C", "R")), r))
    failed = []
    for ref in order:
        own = owner(ref)
        tgt = P.target(ref)
        back = P.side_of(own) if own else True
        if tgt is None and own:
            o = L.fps[own].GetPosition()
            tgt = (pcbnew.ToMM(o.x) - L.org[0], pcbnew.ToMM(o.y) - L.org[1])
        if tgt is None:
            tgt = (0.0, 0.0)
        try:
            P.near(ref, tgt[0], tgt[1], back=back)
        except ValueError:
            try:
                P.near(ref, tgt[0], tgt[1], back=not back)
            except ValueError as e:
                failed.append(ref)
                print("could not place", ref, e)
    return L, P, failed


def pad_xy(L, ref, num):
    for pad in L.fps[ref].Pads():
        if pad.GetNumber() == num:
            return (pcbnew.ToMM(pad.GetPosition().x) - L.org[0], pcbnew.ToMM(pad.GetPosition().y) - L.org[1])
    raise KeyError((ref, num))


def planes(L):
    full = L.local
    # 30 A battery path (review/G3/trace-widths.md): copper islands on L1, L3, L4 and L6 joining the pigtail pad,
    # the shunt and the ESC wire pad. They are routing planes for Freerouting and get stitched with vias.
    from shapely.geometry import MultiPoint
    raw = MultiPoint([pad_xy(L, "J2", "1"), pad_xy(L, "RS1", "1")]).convex_hull.buffer(2.6, join_style=2)
    bat = MultiPoint([pad_xy(L, "RS1", "2"), pad_xy(L, "J8", "1")]).convex_hull.buffer(2.6, join_style=2)
    inside = full.buffer(-0.3)
    for layer in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu):
        L.zone("/Power/VBAT_RAW", layer, raw.intersection(inside), clearance=0.2, priority=5, solid=True)
        L.zone("VBAT", layer, bat.difference(raw.buffer(0.4)).intersection(inside), clearance=0.2, priority=5, solid=True)
    L.power_islands = (raw, bat)
    L.zone("GND", pcbnew.In1_Cu, full, clearance=0.2, priority=0, solid=True)      # solid reference plane for L1
    L.zone("GND", pcbnew.In4_Cu, full, clearance=0.2, priority=0, solid=True)      # solid reference plane for L6
    L.zone("GND", pcbnew.F_Cu, full, clearance=0.2, solid=True, late=True)
    L.zone("GND", pcbnew.B_Cu, full, clearance=0.2, solid=True, late=True)
    L.zone("+3V3", pcbnew.In3_Cu, full, clearance=0.2, solid=True, late=True)
    L.zone("GND", pcbnew.In2_Cu, full, clearance=0.2, solid=True, late=True)
    # antenna keep-out on every copper layer: the module footprint's own rule area leaves In2 out on a 4-layer board,
    # and Espressif asks for no copper under or beside the antenna (ESP32-S3-WROOM-1 datasheet, PCB layout section)
    cu = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu):
        cu.AddLayer(layer)
    L.keepout(cu, box(-40, -40, MODULE[0] - 6.75, 40).intersection(full.buffer(1.0)), name="antenna keep-out")


def ISLAND(z):
    """Pre-route battery-path islands (planes())."""
    return z.GetNetname() in ("/Power/VBAT_RAW", "VBAT") and z.GetAssignedPriority() == 5


PLANE_ZONE = lambda z: z.GetNetname() == "GND" and (z.IsOnLayer(pcbnew.In1_Cu) or z.IsOnLayer(pcbnew.In4_Cu))


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
    L.plane_layers = [pcbnew.In1_Cu, pcbnew.In4_Cu]   # Freerouting: tracks on the GND planes cost 50x (layout._rules_file)
    # stitch the battery-path islands together before routing, so the vias get the space they need
    raw, bat = L.power_islands
    L.stitch("/Power/VBAT_RAW", raw, pitch=0.9)
    L.stitch("VBAT", bat, pitch=0.9)
    for t in L.board.GetTracks():
        t.SetLocked(True)
    # Other nets' tracks that Freerouting runs through the islands are removed after routing (finisher.clear_islands)
    # and re-routed around them. (No-track rule areas over the islands made Freerouting about 20x slower.)
    route = "--no-route" not in sys.argv
    passes = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--passes=")), 30))
    more = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--more=")), 0))

    def extra(L):
        if route and more and L.unrouted():
            L.continue_route(passes=more)
        L.clear_plane_layers([pcbnew.In1_Cu, pcbnew.In4_Cu])   # L2 and L5 stay solid GND planes
    finish(L, passes=passes, route=route, before_fill=extra, island=ISLAND,
           plane_zone=lambda z: z.GetNetname() == "GND" and (z.IsOnLayer(pcbnew.In1_Cu) or z.IsOnLayer(pcbnew.In4_Cu)))
