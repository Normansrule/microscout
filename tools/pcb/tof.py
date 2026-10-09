# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""ToF satellite boards (2-layer, 0.8 mm): the sensor faces outward on the top side, while the
passives and the wire pads sit on the back. Run with KiCad's Python: python3 tools/pcb/tof.py"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pcbnew  # noqa: E402
from shapely.geometry import box  # noqa: E402
from layout import Layout, REPO  # noqa: E402
from report import finish  # noqa: E402

RULES = {"Power": dict(track=0.25, clearance=0.127, nets=[r"\+3V3", r"GND"])}


def side():
    L = Layout("tof-side", REPO / "review/G2/netlists/microscout-tof-side.net",
               REPO / "hardware/tof-satellites/side/microscout-tof-side.kicad_pcb", layers=2, thickness=0.8)
    W, H = 8.5, 7.0
    L.outline(box(-W / 2, -H / 2, W / 2, H / 2))
    L.rules(RULES)
    L.place("U1", 0, -1.3)                        # sensor, apertures outward
    L.place("J1", 0, 2.25, back=True)             # wire pads on the back edge
    L.place("C1", -2.6, -2.2, back=True)
    L.place("C2", 0.0, -2.2, back=True)
    L.place("R1", 2.6, -2.2, back=True)
    full = box(-W / 2, -H / 2, W / 2, H / 2)
    L.zone("GND", pcbnew.B_Cu, full, clearance=0.2, solid=True, late=True)
    L.zone("GND", pcbnew.F_Cu, full, clearance=0.2, solid=True, late=True)
    return L


def front():
    L = Layout("tof-front", REPO / "review/G2/netlists/microscout-tof-front.net",
               REPO / "hardware/tof-satellites/front/microscout-tof-front.kicad_pcb", layers=2, thickness=0.8)
    W, H = 10.0, 9.0
    L.outline(box(-W / 2, -H / 2, W / 2, H / 2))
    L.rules(RULES)
    L.place("U1", 0, -1.9)
    L.place("J1", 0, 3.15, back=True)
    xs = (-3.3, -1.1, 1.1, 3.3)
    for ref, x in zip(("C1", "C2", "C3", "C4"), xs):
        L.place(ref, x, -3.3, back=True)
    for ref, x in zip(("R1", "R2", "R3", "R4"), xs):
        L.place(ref, x, -1.0, back=True)
    full = box(-W / 2, -H / 2, W / 2, H / 2)
    L.zone("GND", pcbnew.B_Cu, full, clearance=0.2, solid=True, late=True)
    L.zone("GND", pcbnew.F_Cu, full, clearance=0.2, solid=True, late=True)
    return L


if __name__ == "__main__":
    for make in (side, front):
        L = make()
        finish(L)
