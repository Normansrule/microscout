# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Writes the project footprint library hardware/libraries/microscout.pretty.

Two footprints here are ESTIMATES because the land-pattern drawings could not be read from this
workspace (figures only, no numbers in the text): the VL53L5CX (ST DS13754 Fig. 28) and the
MLT-5020 buzzer. Both carry an on-board fab note and are listed as blockers for Gate G4.
The rest are simple solder pads for wires and pigtails (D-061).

Run with any Python 3: python3 tools/pcb/footprints.py
"""
import pathlib
import uuid

OUT = pathlib.Path(__file__).resolve().parents[2] / "hardware/libraries/microscout.pretty"
HDR = "STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3"


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "microscout-fp/" + "/".join(map(str, parts))))


def fp(name, descr, pads, body, courtyard, notes=(), attr="smd", silk=()):
    """pads: (num, x, y, w, h, shape, layers?) ; body/courtyard: (w, h) rectangles centred."""
    L = [f'(footprint "{name}" (version 20221018) (generator microscout_footprints) (layer "F.Cu")',
         f'  (descr "{descr} | {HDR}")',
         f'  (attr {attr})',
         f'  (fp_text reference "REF**" (at 0 {-courtyard[1] / 2 - 0.8:.3f}) (layer "F.SilkS") (effects (font (size 0.6 0.6) (thickness 0.1))) (tstamp {uid(name, "ref")}))',
         f'  (fp_text value "{name}" (at 0 {courtyard[1] / 2 + 0.8:.3f}) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))) (tstamp {uid(name, "val")}))']
    for i, n in enumerate(notes):
        L.append(f'  (fp_text user "{n}" (at 0 {courtyard[1] / 2 + 1.5 + 0.7 * i:.3f}) (layer "Cmts.User") (effects (font (size 0.5 0.5) (thickness 0.08))) (tstamp {uid(name, "note", i)}))')
    bw, bh = body
    L.append(f'  (fp_rect (start {-bw / 2:.3f} {-bh / 2:.3f}) (end {bw / 2:.3f} {bh / 2:.3f}) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab") (tstamp {uid(name, "fab")}))')
    cw, ch = courtyard
    L.append(f'  (fp_rect (start {-cw / 2:.3f} {-ch / 2:.3f}) (end {cw / 2:.3f} {ch / 2:.3f}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd") (tstamp {uid(name, "crt")}))')
    for k, (x1, y1, x2, y2) in enumerate(silk):
        L.append(f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width 0.12) (type solid)) (layer "F.SilkS") (tstamp {uid(name, "silk", k)}))')
    for p in pads:
        num, x, y, w, h, shape = p[:6]
        extra = p[6] if len(p) > 6 else ""
        rr = " (roundrect_rratio 0.25)" if shape == "roundrect" else ""
        L.append(f'  (pad "{num}" smd {shape} (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask"){rr}{extra} (tstamp {uid(name, "pad", num, x, y)}))')
    L.append(")")
    (OUT / f"{name}.kicad_mod").write_text("\n".join(L) + "\n")
    return name


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []

    # VL53L5CX optical LGA16, 6.4 x 3.0 mm. Pin grid A/B/C x 1..7 from DS13754 Table 3.
    # ESTIMATE: 0.8 mm column pitch and 1.0 mm row pitch fill the 6.4 x 3.0 body; pad 0.5 x 0.5;
    # thermal pad B4 1.6 x 0.6. Replace from DS13754 Fig. 28 before G4.
    pads = []
    for col in range(1, 8):
        x = (col - 4) * 0.8
        pads.append((f"A{col}", x, -1.0, 0.5, 0.5, "roundrect"))
        pads.append((f"C{col}", x, 1.0, 0.5, 0.5, "roundrect"))
    pads += [("B1", -2.4, 0.0, 0.5, 0.5, "roundrect"), ("B7", 2.4, 0.0, 0.5, 0.5, "roundrect"),
             ("B4", 0.0, 0.0, 1.6, 0.6, "roundrect")]
    made.append(fp("ST_VL53L5CX_LGA16_TBD", "ST VL53L5CX optical LGA16 6.4x3.0 mm - PAD GEOMETRY ESTIMATED (DS13754 Fig. 28 not read)",
                   pads, (6.4, 3.0), (7.0, 3.6),
                   notes=("ESTIMATED LAND PATTERN - CHECK ST DS13754 FIG 28 BEFORE G4",),
                   silk=((-3.3, -1.6, -2.6, -1.6), (-3.3, -1.6, -3.3, -0.9))))

    # MLT-5020 magnetic buzzer, 5.2 x 5.2 x 2.5 mm (LCSC C94598 listing). ESTIMATE: four corner pads,
    # 1 = +, 2 = -, 3/4 mechanical. Replace from the LCSC datasheet before G4.
    pads = [("1", -2.1, -2.1, 1.2, 1.2, "roundrect"), ("2", 2.1, -2.1, 1.2, 1.2, "roundrect"),
            ("3", -2.1, 2.1, 1.2, 1.2, "roundrect"), ("4", 2.1, 2.1, 1.2, 1.2, "roundrect")]
    made.append(fp("Buzzer_MLT-5020_TBD", "Magnetic buzzer MLT-5020 5.2x5.2 mm - PAD GEOMETRY ESTIMATED (datasheet drawing not read)",
                   pads, (5.2, 5.2), (6.0, 6.0), notes=("ESTIMATED LAND PATTERN - CHECK MLT-5020 DATASHEET BEFORE G4",),
                   silk=((-2.9, -0.8, -2.9, 0.8),)))

    # Solder pads for wires (D-061).
    for n in (4, 5, 6, 8):
        p = 1.5
        pads = [(str(i + 1), (i - (n - 1) / 2) * p, 0.0, 1.0, 1.8, "roundrect") for i in range(n)]
        w = (n - 1) * p + 1.0
        made.append(fp(f"PadRow_1x{n:02d}_P1.50mm_SMD", f"{n} SMD solder pads 1.0x1.8 mm at 1.5 mm pitch for 28-32 AWG wires or a flex",
                       pads, (w, 1.8), (w + 0.5, 2.3),
                       silk=((-w / 2 - 0.3, -0.8, -w / 2 - 0.3, 0.8),)))
    made.append(fp("Pad_SMD_3x6mm", "Single SMD solder pad 3x6 mm for a 20 AWG power wire",
                   [("1", 0, 0, 3.0, 6.0, "roundrect")], (3.0, 6.0), (3.5, 6.5)))
    made.append(fp("Pigtail_2x_SMD_3x6mm_P4.5mm", "Battery pigtail pads (XT30 lead, 18 AWG): pad 1 = pack +, pad 2 = pack -",
                   [("1", -2.25, 0, 3.0, 6.0, "roundrect"), ("2", 2.25, 0, 3.0, 6.0, "roundrect")], (7.5, 6.0), (8.0, 6.5),
                   silk=((-2.25, -3.6, -2.25, -3.6),)))
    made.append(fp("Pigtail_3x_SMD_1.5x3mm_P2.5mm", "Balance-lead pigtail pads (JST-XH lead, 26-28 AWG): 1 = pack -, 2 = mid, 3 = pack + (unused)",
                   [(str(i + 1), (i - 1) * 2.5, 0, 1.5, 3.0, "roundrect") for i in range(3)], (6.5, 3.0), (7.0, 3.5)))
    # M2 soft-mount grommet hole (D-060): 3.0 mm NPTH, copper keep-out to r = 2.1 mm
    hole = [f'(footprint "MountingHole_3.0mm_NPTH" (version 20221018) (generator microscout_footprints) (layer "F.Cu")',
            f'  (descr "3.0 mm unplated hole for an M2 soft-mount grommet (D-060) | {HDR}")',
            '  (attr exclude_from_pos_files exclude_from_bom)',
            f'  (fp_text reference "REF**" (at 0 -2.8) (layer "F.Fab") hide (effects (font (size 0.6 0.6) (thickness 0.1))) (tstamp {uid("mh", "ref")}))',
            f'  (fp_text value "MountingHole_3.0mm_NPTH" (at 0 2.8) (layer "F.Fab") hide (effects (font (size 0.5 0.5) (thickness 0.08))) (tstamp {uid("mh", "val")}))',
            f'  (fp_circle (center 0 0) (end 2.1 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd") (tstamp {uid("mh", "crt")}))',
            f'  (fp_circle (center 0 0) (end 2.1 0) (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd") (tstamp {uid("mh", "crtb")}))',
            f'  (pad "" np_thru_hole circle (at 0 0) (size 3.0 3.0) (drill 3.0) (layers "*.Cu" "*.Mask") (tstamp {uid("mh", "pad")}))',
            ")"]
    (OUT / "MountingHole_3.0mm_NPTH.kicad_mod").write_text("\n".join(hole) + "\n")
    made.append("MountingHole_3.0mm_NPTH")
    (OUT.parent / "microscout.pretty.README.md").write_text(
        f"> {HDR}\n\n# microscout.pretty\n\nGenerated by `tools/pcb/footprints.py`. "
        "`ST_VL53L5CX_LGA16_TBD` and `Buzzer_MLT-5020_TBD` are **estimated land patterns** and block Gate G4 until checked "
        "against the manufacturer drawings. The others are plain solder pads.\n\n" + "\n".join(f"- `{m}`" for m in made) + "\n")
    print("wrote", len(made), "footprints to", OUT)


if __name__ == "__main__":
    main()
