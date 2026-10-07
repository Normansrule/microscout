#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G5 (concept model, pre-G5)
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Parametric CONCEPT model of MicroScout rev B (CadQuery).

This is a look-and-fit concept made ahead of milestone M6 at the owner's request:
the one-piece ducted frame and canopy are real parametric geometry; motors, props,
battery, boards, camera and sensors are SIMPLIFIED ENVELOPES (labelled APPROXIMATE)
from datasheet or vendor dimensions where known. No manufacturer STEP files are used.

Frame: CAD Z up, X forward, Y left, origin at the frame centre on the duct-bottom plane.
Outputs (mechanical/concept/out/): one STEP per part, one STL per printable part,
an assembly STEP and a coloured GLB for the web viewer, plus a mass/clearance report.

Run: python3 mechanical/concept/microscout_concept.py
"""
import json
import math
import pathlib
import sys

import cadquery as cq
from cadquery.occ_impl.exporters.assembly import exportAssembly, exportGLTF

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(REPO / "review" / "G1" / "calc"))
import budgets as B  # noqa: E402

# ------------------------------------------------------------------ parameters
P = dict(
    motor_to_motor=B.MOTOR_TO_MOTOR_MM.value,     # 95 mm
    prop_d=B.PROP_MM.value,                       # 51 mm
    duct_clear=B.DUCT_CLEAR_MM,                   # 1.0 mm
    duct_wall=B.DUCT_WALL_MM,                     # 0.9 mm
    duct_h=B.DUCT_H_MM,                           # 11 mm
    lip=2.0,                                      # inlet flare (mm)
    mount_t=1.8, boss_r=5.5, spoke_w=2.6,
    tray=(30.0, 30.0, 1.6), tray_z=2.0,
    hole_pitch=25.5, hole_d=3.0,                  # whoop-standard 25.5 mm pattern
    esc=(29.0, 29.0, 1.0), esc_z=6.0,
    fc=(40.0, 40.0, 1.0), fc_z=13.5,
    canopy_wall=1.0, canopy_h=8.5,
    battery=(69.0, 18.0, 12.0),                   # GNB 2S 550 (S14)
    motor_bell=(14.0, 7.0), motor_base=(14.0, 1.5),   # EX1103 envelope (APPROXIMATE, not from a drawing)
    tolerance=0.2,                                # printer fit allowance (mm)
)
A = P["motor_to_motor"] / math.sqrt(2) / 2       # motor offset on X and Y
R_IN = P["prop_d"] / 2 + P["duct_clear"]
R_OUT = R_IN + P["duct_wall"]
MOTORS = [(-A, -A), (+A, -A), (-A, +A), (+A, +A)]  # Betaflight order: 1 RR, 2 FR, 3 RL, 4 FL (CAD Y = left)
SPIN_CW = {(+A, +A): True, (+A, -A): False, (-A, +A): False, (-A, -A): True}  # Betaflight default, placeholder


def duct_ring():
    r0, r1, h, lip, w = R_IN, R_OUT, P["duct_h"], P["lip"], P["duct_wall"]
    pts = [(r0, 0), (r1, 0), (r1, h - 2.5), (r1 + lip * 0.7, h - 0.6), (r1 + lip, h),
           (r0 + lip, h), (r0 + lip * 0.45, h - 1.0), (r0, h - 2.6)]
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))


def motor_mount(cx, cy):
    t = P["mount_t"]
    m = cq.Workplane("XY").circle(P["boss_r"]).extrude(t).faces(">Z").workplane().hole(1.6)
    ang0 = math.degrees(math.atan2(-cy, -cx))       # first spoke points at the frame centre
    for k in range(3):
        a = math.radians(ang0 + 120 * k)
        L = R_IN - P["boss_r"] + 0.6
        mid = P["boss_r"] + L / 2 - 0.3
        sp = (cq.Workplane("XY").box(L, P["spoke_w"], t, centered=(True, True, False))
              .rotate((0, 0, 0), (0, 0, 1), math.degrees(a)).translate((mid * math.cos(a), mid * math.sin(a), 0)))
        m = m.union(sp)
    for k in range(4):                                # M1.4 motor screw holes (APPROXIMATE pattern)
        a = math.radians(45 + 90 * k)
        m = m.cut(cq.Workplane("XY").center(3.3 * math.cos(a), 3.3 * math.sin(a)).circle(0.55).extrude(t))
    return m.translate((cx, cy, 0))


def frame():
    f = None
    for (x, y) in MOTORS:
        d = duct_ring().translate((x, y, 0)).union(motor_mount(x, y))
        f = d if f is None else f.union(d)
    # bridges between neighbouring ducts (continuous outer bumper)
    h = P["duct_h"] - 1.0
    for (x, y), (x2, y2) in (((+A, +A), (+A, -A)), ((-A, +A), (-A, -A)), ((+A, +A), (-A, +A)), ((+A, -A), (-A, -A))):
        mx, my = (x + x2) / 2, (y + y2) / 2
        along_x = abs(x - x2) > 1
        L = 2 * A - 2 * R_IN + 1.0
        br = cq.Workplane("XY").box(L if along_x else 2.2, 2.2 if along_x else L, h, centered=(True, True, False))
        out = 1.0 if not along_x else 1.0
        off = (0, math.copysign(R_OUT * 0.55, my)) if along_x else (math.copysign(R_OUT * 0.55, mx), 0)
        f = f.union(br.translate((mx + off[0] * out, my + off[1] * out, 0)))
    # centre tray with grommet holes and a sensor window, plus arms to the ducts
    tx, ty, tt = P["tray"]
    tray = (cq.Workplane("XY").rect(tx, ty).extrude(tt).edges("|Z").fillet(4.0)
            .translate((0, 0, P["tray_z"])))
    for (x, y) in MOTORS:
        a = math.atan2(y, x)
        L = math.hypot(x, y) - R_IN + 0.5
        arm = (cq.Workplane("XY").box(L, 4.0, tt, centered=(True, True, False))
               .rotate((0, 0, 0), (0, 0, 1), math.degrees(a))
               .translate((L / 2 * math.cos(a), L / 2 * math.sin(a), P["tray_z"])))
        tray = tray.union(arm)
    p = P["hole_pitch"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            tray = tray.cut(cq.Workplane("XY").center(sx * p, sy * p).circle(P["hole_d"] / 2).extrude(10).translate((0, 0, -1)))
    tray = tray.cut(cq.Workplane("XY").rect(12, 10).extrude(10).translate((0, 0, -1)))   # down-sensor window
    f = f.union(tray)
    # keep every duct bore clear of bridges and arms
    for (x, y) in MOTORS:
        f = f.cut(cq.Workplane("XY").circle(R_IN).extrude(P["duct_h"] + 2).translate((x, y, P["mount_t"])))
        f = f.union(motor_mount(x, y))
    return f


def notched_board(w, l, t, z, notch_r):
    b = cq.Workplane("XY").rect(w, l).extrude(t).edges("|Z").fillet(2.0)
    for (x, y) in MOTORS:
        b = b.cut(cq.Workplane("XY").circle(notch_r).extrude(t + 2).translate((x, y, -1)))
    p = P["hole_pitch"] / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.cut(cq.Workplane("XY").center(sx * p, sy * p).circle(1.1).extrude(t + 2).translate((0, 0, -1)))
    return b.translate((0, 0, z))


def canopy():
    w, l, t = P["fc"]
    z0 = P["fc_z"] + t + 0.4
    h = P["canopy_h"]
    outer = (cq.Workplane("XY").sketch().rect(l - 6, w - 8).vertices().fillet(6.0).finalize()
             .extrude(h, taper=18))
    try:
        outer = outer.faces(">Z").edges().fillet(2.5)
    except Exception:
        pass
    c = outer.faces("<Z").shell(-P["canopy_wall"])
    c = c.cut(cq.Workplane("YZ").center(0, 3.6).rect(10, 7).extrude(20).translate((10, 0, 0)))   # camera window
    # battery saddle ridges on top
    for sy in (-1, 1):
        c = c.union(cq.Workplane("XY").box(l - 20, 1.6, 1.2, centered=(True, True, False)).translate((0, sy * 9.6, h - 0.2)))
    return c.translate((0, 0, z0))


def motor(x, y):
    bd, bh = P["motor_bell"]
    base_d, base_h = P["motor_base"]
    z = P["mount_t"]
    m = cq.Workplane("XY").circle(base_d / 2).extrude(base_h)
    m = m.union(cq.Workplane("XY").circle(bd / 2).extrude(bh).edges(">Z").fillet(1.2).translate((0, 0, base_h)))
    m = m.union(cq.Workplane("XY").circle(0.75).extrude(2.5).translate((0, 0, base_h + bh)))
    return m.translate((x, y, z))


def prop(x, y, cw):
    z = P["mount_t"] + P["motor_base"][1] + P["motor_bell"][1]
    r = P["prop_d"] / 2
    hub = cq.Workplane("XY").circle(2.6).extrude(4.0)
    p = hub
    pitch = -14 if cw else 14
    for k in range(3):
        blade = (cq.Workplane("XY").ellipse(r * 0.43, 3.0).extrude(0.6).translate((r * 0.53, 0, -0.3)))
        blade = blade.rotate((0, 0, 0), (1, 0, 0), pitch).translate((0, 0, 2.0))
        p = p.union(blade.rotate((0, 0, 0), (0, 0, 1), 120 * k))
    return p.translate((x, y, z))


def battery():
    L, W, H = P["battery"]
    z0 = P["fc_z"] + P["fc"][2] + 0.4 + P["canopy_h"] + 1.0
    b = cq.Workplane("XY").box(L, W, H, centered=(True, True, False)).edges().fillet(1.5)
    return b.translate((-4, 0, z0))


def strap():
    L, W, H = P["battery"]
    z0 = P["fc_z"] + P["fc"][2] + 0.4 + P["canopy_h"] + 1.0
    s = (cq.Workplane("YZ").rect(W + 2.4, H + 2.4).extrude(8).cut(cq.Workplane("YZ").rect(W + 0.4, H + 0.4).extrude(8))
         .translate((-8, 0, z0 + H / 2)))
    return s


def box(dx, dy, dz, at):
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, False)).translate(at)


def build():
    OUT.mkdir(exist_ok=True)
    fr = frame()
    esc = notched_board(P["esc"][0], P["esc"][1], P["esc"][2], P["esc_z"], R_OUT + 0.6)
    fc = notched_board(P["fc"][0], P["fc"][1], P["fc"][2], P["fc_z"], R_IN + P["lip"] + 0.6)
    can = canopy()
    fz = P["fc_z"] + P["fc"][2]
    parts = {
        "frame_pa11": (fr, (0.16, 0.17, 0.19, 1.0)),
        "canopy_tpu": (can, (0.92, 0.41, 0.20, 1.0)),
        "esc_board": (esc, (0.10, 0.25, 0.18, 1.0)),
        "fc_board": (fc, (0.10, 0.25, 0.18, 1.0)),
        "esp32_module": (box(25.5, 18.0, 3.1, (-3.0, 0, fz)), (0.75, 0.76, 0.78, 1.0)),
        "camera": (box(6, 8.5, 8.5, (17.5, 0, fz + 0.3)).union(
            cq.Workplane("YZ").circle(3.6).extrude(4.5).translate((20.5, 0, fz + 4.5))), (0.12, 0.12, 0.14, 1.0)),
        "tof_front_8x8": (box(3.0, 6.4, 1.5, (19.3, 0, fz - 1.5 - 1.0)), (0.05, 0.05, 0.06, 1.0)),
        "sensor_pod_down": (box(12, 10, 2.2, (0, 0, P["tray_z"] - 0.4)), (0.10, 0.25, 0.18, 1.0)),
        "battery_2s_550": (battery(), (0.22, 0.24, 0.30, 1.0)),
        "battery_strap": (strap(), (0.92, 0.41, 0.20, 1.0)),
    }
    for i, (x, y) in enumerate(MOTORS):
        parts[f"motor_{i+1}"] = (motor(x, y), (0.80, 0.62, 0.28, 1.0))
        parts[f"prop_{i+1}"] = (prop(x, y, SPIN_CW[(x, y)]), (0.55, 0.78, 0.95, 0.80))
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts[f"led_{i+1}"] = (box(2.2, 2.2, 1.0, (sx * 15.5, sy * 15.5, fz)), (0.98, 0.98, 1.0, 1.0))
    for i, (name, at, rot) in enumerate((("left", (0, 16.5, fz - 4.5), 90), ("right", (0, -16.5, fz - 4.5), -90), ("rear", (-19.5, 0, fz - 4.5), 180))):
        parts[f"tof_{name}"] = (box(1.2, 7.0, 5.0, (0, 0, 0)).rotate((0, 0, 0), (0, 0, 1), rot - 90 if name != "rear" else 0).translate(at), (0.10, 0.25, 0.18, 1.0))

    assy = cq.Assembly(name="microscout_concept_revB")
    for name, (shape, rgba) in parts.items():
        assy.add(shape, name=name, color=cq.Color(*rgba))
        cq.exporters.export(shape, str(OUT / f"{name}.step"))
    for name in ("frame_pa11", "canopy_tpu", "battery_strap"):
        cq.exporters.export(parts[name][0], str(OUT / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
        try:
            cq.exporters.export(parts[name][0], str(OUT / f"{name}.3mf"), tolerance=0.02, angularTolerance=0.1)
        except Exception as e:      # older CadQuery without 3MF support
            print("3MF export skipped:", e)
    exportAssembly(assy, str(OUT / "microscout_concept_assembly.step"))
    exportGLTF(assy, str(OUT / "microscout_concept.glb"), binary=True, tolerance=0.05, angularTolerance=0.15)
    web = REPO / "docs" / "models"
    web.mkdir(parents=True, exist_ok=True)
    (web / "microscout_concept.glb").write_bytes((OUT / "microscout_concept.glb").read_bytes())

    # mass + clearance report
    dens = {"frame_pa11": B.PA11_DENSITY, "canopy_tpu": B.TPU_DENSITY, "battery_strap": B.TPU_DENSITY}
    rep = dict(units="mm, g", note="CONCEPT - envelopes are APPROXIMATE; masses only for the printed parts", parts={})
    for name, d in dens.items():
        vol = parts[name][0].val().Volume()
        rep["parts"][name] = dict(volume_mm3=round(vol, 1), density=d, mass_g=round(vol / 1000 * d, 2))
    est = B.duct_frame_mass()[1]
    rep["frame_cad_vs_hand_estimate"] = dict(cad_mass_g=rep["parts"]["frame_pa11"]["mass_g"], hand_estimate_g=round(est, 2),
                                             note="budgets.py uses the CAD mass once this report exists")
    bb = parts["frame_pa11"][0].val().BoundingBox()
    rep["frame_bbox_mm"] = [round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)]
    clash = {}
    for a_name in ("esc_board", "fc_board"):
        for b_name in [n for n in parts if n.startswith("prop_")] + ["frame_pa11"]:
            v = parts[a_name][0].intersect(parts[b_name][0]).val().Volume() if True else 0
            if v > 1e-3:
                clash[f"{a_name} x {b_name}"] = round(v, 3)
    for i in range(1, 5):
        v = parts[f"prop_{i}"][0].intersect(parts["frame_pa11"][0]).val().Volume()
        if v > 1e-3:
            clash[f"prop_{i} x frame_pa11"] = round(v, 3)
    rep["interference_mm3"] = clash or "none found between boards, props and frame"
    rep["prop_tip_clearance_mm"] = round(R_IN - P["prop_d"] / 2, 2)
    (OUT / "concept_report.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    return parts


if __name__ == "__main__":
    build()
