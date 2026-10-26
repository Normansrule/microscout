# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Regenerate every MicroScout schematic and the Gate G2 outputs.

  python3 tools/sch/build_all.py            # needs KiCad 7+ (kicad-cli) on PATH

Writes: hardware/*/ *.kicad_sch, review/G2/schematics/*.pdf, review/G2/netlists/*.net,
review/G2/check-*.md, review/G2/bom-*.csv. Exits non-zero if any check fails.
Licence: MIT.
"""
import csv
import importlib.util
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import customsyms  # noqa: E402
from check import report  # noqa: E402

DESIGNS = [
    ("fc", REPO / "hardware/drone-pcb/design/fc.py", "Flight controller"),
    ("esc", REPO / "hardware/esc-pcb/design/esc.py", "4-in-1 ESC"),
    ("tof", REPO / "hardware/tof-satellites/design/tof.py", "ToF satellites"),
]
G2 = REPO / "review" / "G2"


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bom(project, path):
    rows = {}
    for p in project.parts.values():
        if p.ref.startswith("#"):
            continue
        key = (p.value, p.footprint, p.fields.get("LCSC", ""), p.dnp)
        r = rows.setdefault(key, dict(refs=[], value=p.value, footprint=p.footprint.split(":")[-1],
                                      lcsc=p.fields.get("LCSC", ""), mpn=p.fields.get("MPN", ""),
                                      manufacturer=p.fields.get("Manufacturer", ""),
                                      rating=p.fields.get("Rating", ""), note=p.fields.get("Note", ""),
                                      dnp="DNP" if p.dnp else ""))
        r["refs"].append(p.ref)

    def refkey(r):
        import re
        m = re.match(r"([A-Z#]+)(\d+)", r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)
    with open(path, "w", newline="") as f:
        f.write("# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2\n")
        f.write("# Generated from the schematic source by tools/sch/build_all.py. Prices: see bom/drone-bom-g1.csv and review/G2/sources.md.\n")
        w = csv.writer(f)
        w.writerow(["refs", "qty", "value", "footprint", "lcsc", "mpn", "manufacturer", "rating", "dnp", "note"])
        for r in sorted(rows.values(), key=lambda r: refkey(sorted(r["refs"], key=refkey)[0])):
            refs = sorted(r["refs"], key=refkey)
            w.writerow([" ".join(refs), len(refs), r["value"], r["footprint"], r["lcsc"], r["mpn"], r["manufacturer"],
                        r["rating"], r["dnp"], r["note"]])


def main():
    customsyms.main()
    (G2 / "schematics").mkdir(parents=True, exist_ok=True)
    (G2 / "netlists").mkdir(parents=True, exist_ok=True)
    failures = 0
    summary = []
    for key, path, title in DESIGNS:
        mod = load(path)
        projects = mod.build()
        projects = projects if isinstance(projects, list) else [projects]
        for proj in projects:
            proj.write()
            root = proj.outdir / f"{proj.name}.kicad_sch"
            net = G2 / "netlists" / f"{proj.name}.net"
            pdf = G2 / "schematics" / f"{proj.name}.pdf"
            subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(net), str(root)], check=True, capture_output=True)
            subprocess.run(["kicad-cli", "sch", "export", "pdf", "-o", str(pdf), str(root)], check=True, capture_output=True)
            text, nerr = report(proj, net, proj.title)
            (G2 / f"check-{proj.name}.md").write_text(text + "\n")
            bom(proj, G2 / f"bom-{proj.name}.csv")
            nparts = sum(1 for r in proj.parts if not r.startswith("#"))
            summary.append((proj.name, nparts, len(proj.sheets), nerr))
            failures += nerr
            print(f"{proj.name}: {nparts} parts, {len(proj.sheets)} sheets, {nerr} check failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
