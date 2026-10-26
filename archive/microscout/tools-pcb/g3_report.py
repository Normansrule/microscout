# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Collects the per-board results (review/G3/drc/*.json) into review/G3/summary.md and
review/G3/autorouted-nets.md. Run after the board scripts: python3 tools/pcb/g3_report.py"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
G3 = REPO / "review/G3"
BOARDS = [("fc", "Flight controller"), ("esc", "4-in-1 ESC"), ("tof-side", "ToF side satellite (x3)"), ("tof-front", "ToF front satellite")]


def stats(pcb):
    import pcbnew
    b = pcbnew.LoadBoard(str(pcb))
    length = sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetClass() != "PCB_VIA")
    vias = sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA")
    bot = sum(1 for f in b.GetFootprints() if f.IsFlipped() and not f.GetReference().startswith("H"))
    top = sum(1 for f in b.GetFootprints() if not f.IsFlipped() and not f.GetReference().startswith("H"))
    layers = b.GetCopperLayerCount()
    return dict(track_m=length / 1000, vias=vias, top=top, bottom=bot, layers=layers)


def main():
    rows, nets_md = [], []
    for key, label in BOARDS:
        j = G3 / "drc" / f"{key}.json"
        if not j.exists():
            continue
        d = json.loads(j.read_text())
        st = stats(REPO / d["pcb"])
        drc = d["drc"]
        rows.append(f"| {label} | `{d['pcb']}` | {st['layers']} | {d['footprints']} ({st['top']} top, {st['bottom']} bottom) | "
                    f"{drc.get('DRC violations', '?')} | {drc.get('unconnected pads', '?')} | {st['vias']} | {st['track_m']:.2f} m | "
                    f"{len(d['autorouted_nets'])} |")
        nets_md.append(f"## {label}\n\n{len(d['autorouted_nets'])} nets carry Freerouting copper:\n\n" +
                       ", ".join(f"`{n}`" for n in d["autorouted_nets"]) + "\n")
    (G3 / "summary.md").write_text(
        "> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3\n\n"
        "| Board | File | Layers | Parts | DRC violations | Unconnected | Vias | Track length | Nets with routed copper |\n"
        "|---|---|---:|---|---:|---:|---:|---:|---:|\n" + "\n".join(rows) + "\n")
    (G3 / "autorouted-nets.md").write_text(
        "> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3\n\n# Autorouted nets (G3)\n\n"
        "Every track on these boards was placed by Freerouting 1.9.0 from the KiCad DSN export (`tools/pcb/layout.py`), "
        "except the copper islands drawn by the board scripts (planes, battery path, motor phases) and the stitching vias. "
        "Nothing was hand-routed. **Every net below needs a human look** (VERIFY G3).\n\n" + "\n".join(nets_md))
    # every connection still open, straight from KiCad's DRC reports
    out = ["> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3", "", "# Connections still open (G3)", "",
           "Taken from KiCad's DRC reports in `drc/`. Each line is one missing connection between two copper items of "
           "the same net (KiCad picks the nearest pair). They must be routed (for example with KiCad's interactive "
           "router) before G4. On the ESC, channels 3 and 4 are copies of channels 2 and 1, so most items appear twice.", ""]
    for key, label in BOARDS:
        rpt = G3 / "drc" / f"{key}.rpt"
        if not rpt.exists():
            continue
        t = rpt.read_text()
        u = t[t.index("unconnected pads"):] if "unconnected pads" in t else ""
        items = []
        for blk in u.split("[unconnected_items]")[1:]:
            pts = re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)", blk)[:2]
            if len(pts) == 2:
                (x1, y1, a), (x2, y2, b) = pts
                net = re.search(r"\[(.*?)\]", a)
                items.append((net.group(1) if net else "?", re.sub(r" \[.*?\]", "", a).strip(), re.sub(r" \[.*?\]", "", b).strip(),
                              f"({float(x1) - 150:.1f}, {float(y1) - 100:.1f})"))
        out.append(f"## {label}: {len(items)} open\n")
        if items:
            out.append("| Net | From | To | Near (x, y) mm from board centre |\n|---|---|---|---|")
            out += [f"| `{n}` | {a} | {b} | {xy} |" for n, a, b, xy in sorted(items)]
        out.append("")
    (G3 / "open-connections.md").write_text("\n".join(out) + "\n")
    print("wrote review/G3/summary.md, autorouted-nets.md and open-connections.md")


if __name__ == "__main__":
    main()
