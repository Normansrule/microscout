# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Review exports for a routed board: per-layer SVG + PDF plots and coloured top/bottom PNG views.

    python3 tools/pcb/export.py hardware/drone-pcb/microscout-fc.kicad_pcb review/G3/fc
Needs kicad-cli (KiCad 7) and cairosvg (pip) for the PNGs.
"""
import pathlib
import re
import subprocess
import sys

VIEWS = {
    "top": ["Edge.Cuts", "F.Cu", "F.Mask", "F.SilkS", "F.Fab"],
    "bottom": ["Edge.Cuts", "B.Cu", "B.Mask", "B.SilkS", "B.Fab"],
}
COPPER = {2: ["F.Cu", "B.Cu"], 4: ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"],
          6: ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]}


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(" ".join(a) + "\n" + r.stdout + r.stderr)


def copper_layers(pcb):
    txt = pathlib.Path(pcb).read_text()
    layers = txt[txt.index("(layers"):txt.index("(setup")]
    return 2 + sum(1 for k in range(1, 5) if f'"In{k}.Cu"' in layers)


def export(pcb, out, png=True):
    pcb, out = pathlib.Path(pcb), pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = copper_layers(pcb)
    files = []
    for lay in COPPER[n] + ["F.SilkS", "B.SilkS", "F.Mask", "B.Mask", "F.Fab", "B.Fab", "Edge.Cuts"]:
        f = out / f"{pcb.stem}-{lay.replace('.', '_')}.svg"
        mirror = ["--mirror"] if lay.startswith("B.") else []
        run("kicad-cli", "pcb", "export", "svg", "--layers", f"{lay},Edge.Cuts", "--exclude-drawing-sheet", "--page-size-mode", "2",
            "--black-and-white", *mirror, "-o", str(f), str(pcb))
        files.append(f)
    pdf = out / f"{pcb.stem}-layers.pdf"
    run("kicad-cli", "pcb", "export", "pdf", "--layers", ",".join(COPPER[n] + ["F.SilkS", "B.SilkS", "Edge.Cuts"]),
        "--exclude-refdes", "-o", str(pdf), str(pcb))
    if png:
        import cairosvg
        for view, layers in VIEWS.items():
            svg = out / f"{pcb.stem}-{view}.svg"
            mirror = ["--mirror"] if view == "bottom" else []
            run("kicad-cli", "pcb", "export", "svg", "--layers", ",".join(layers), "--exclude-drawing-sheet",
                "--page-size-mode", "2", *mirror, "-o", str(svg), str(pcb))
            cairosvg.svg2png(url=str(svg), write_to=str(out / f"{pcb.stem}-{view}.png"), output_width=1400, background_color="#0f1418")
    return files


if __name__ == "__main__":
    export(sys.argv[1], sys.argv[2])
    print("exported", sys.argv[1])
