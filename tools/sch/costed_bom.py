# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Write bom/drone-bom-g2.csv: one drone's parts from the G2 schematics plus off-board items.

Board multiplicity: 1x flight controller, 1x ESC, 3x ToF side satellite, 1x ToF front satellite.
Prices: LCSC/JLCPCB pages seen 2026-10-04..07 (G1 BOM + G2 checks, review/G2/sources.md).
Same columns as bom/drone-bom-g1.csv so budgets.py and tools/viz read either. Licence: MIT.
"""
import csv
import importlib.util
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
G1 = REPO / "bom" / "drone-bom-g1.csv"
OUT = REPO / "bom" / "drone-bom-g2.csv"
BOARDS = [("FC", REPO / "hardware/drone-pcb/design/fc.py", 0, 1), ("ESC", REPO / "hardware/esc-pcb/design/esc.py", 0, 1),
          ("TOF-SIDE", REPO / "hardware/tof-satellites/design/tof.py", 0, 3), ("TOF-FRONT", REPO / "hardware/tof-satellites/design/tof.py", 1, 1)]

# LCSC -> (unit USD, price break, stock seen, date) added or changed at G2
G2_PRICES = {
    "C683782": (6.67, "1+", "2538", "2026-10-07"), "C2868382": (0.95, "1+", "1611", "2026-10-07"),
    "C205990": (0.52, "1+", "14503", "2026-10-07"), "C779278": (5.8269, "1+", "~5000", "2026-10-07"),
    "C328453": (2.373, "1+", "0 (out of stock)", "2026-10-07"), "C191023": (0.0133, "50+", "4023500", "2026-10-07"),
    "C2286": (0.0076, "100+", "2586400", "2026-10-07"), "C5832370": (0.0806, "20+", "286920", "2026-10-07"),
    "C5832372": (0.0806, "20+", "284840", "2026-10-07"), "C2939798": (0.1819, "5+", "16645", "2026-10-07"),
    "C1525": (0.0046, "100+", "16.4M (JLCPCB)", "2026-10-07"), "C52923": (0.0108, "50+", "4462050", "2026-10-07"),
    "C15195": (0.005, "100+", "248100", "2026-10-07"), "C23630": (0.0182, "50+", "615000", "2026-10-07"),
    "C23733": (0.0167, "50+", "1299850", "2026-10-07"), "C19666": (0.0298, "10+", "24080", "2026-10-07"),
    "C19702": (0.0322, "20+", "1595420", "2026-10-07"), "C15850": (0.0657, "20+", "12.67M (JLCPCB)", "2026-10-07"),
    "C45783": (0.2222, "20+", "839940", "2026-10-07"), "C285062": (0.0043, "100+", "271400", "2026-10-07"),
    "C26404": (0.0068, "20+", "149060", "2026-10-07"), "C106862": (0.0048, "100+", "697700", "2026-10-07"),
    "C25102": (0.0021, "100+", "716300", "2026-10-07"), "C22276": (0.0026, "100+", "49800", "2026-10-07"),
    "C2933105": (0.0004, "1 (jlcsearch)", "94045 (JLCPCB)", "2026-10-07"), "C29402": (0.0015, "100+", "176069 (JLCPCB)", "2026-10-07"),
    "C17917": (0.0047, "100+", "194200", "2026-10-07"),
    "C157928": (0.0741, "10+", "134440", "2026-10-07"), "C160407": (0.3343, "5+", "116705", "2026-10-07"),
    "C318884": (0.0207, "20+", "211640", "2026-10-07"),
}
G2_PRICES.update({"C8678": (0.0351, "20+", "3631780", "2026-10-07"), "C84817": (0.0958, "1+", "154499", "2026-10-07"),
                  "C48888313": (0.0587, "1+", "2270", "2026-10-07"), "C25745": (0.0005, "1 (jlcsearch)", "198299 (JLCPCB)", "2026-10-07"),
                  "C25755": (0.0005, "1 (jlcsearch)", "720091 (JLCPCB)", "2026-10-07")})
for c in ("C25744", "C25741", "C25900", "C25905", "C11702", "C25879", "C25792", "C25092", "C25077", "C17168", "C25076"):
    G2_PRICES[c] = (0.0011, "1 (jlcsearch)", "JLCPCB Basic", "2026-10-07")
OFFBOARD = ["M1-M4", "P1-P4", "B1", "RX1", "CAM1", "FRAME"]
COLS = ["ref", "status", "qty", "function", "mpn", "manufacturer", "package", "lcsc", "lcsc_check", "unit_usd",
        "price_break", "stock_seen", "fetched_utc", "datasheet_url", "notes"]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem + "_cb", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def g1_rows():
    lines = [l for l in G1.read_text().splitlines() if not l.startswith("#")]
    return list(csv.DictReader(lines))


def refkey(r):
    m = re.match(r"([A-Z#]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)


def main():
    g1 = g1_rows()
    prices = {r["lcsc"]: (r["unit_usd"], r["price_break"], r["stock_seen"], r["fetched_utc"]) for r in g1 if r["lcsc"].startswith("C")}
    prices.update({k: (str(v[0]), v[1], v[2], v[3]) for k, v in G2_PRICES.items()})
    rows = []
    for board, path, idx, mult in BOARDS:
        projects = load(path).build()
        proj = projects[idx] if isinstance(projects, list) else projects
        groups = {}
        for p in proj.parts.values():
            if p.ref.startswith("#"):
                continue
            key = (p.value, p.footprint, p.fields.get("LCSC", ""), p.dnp)
            groups.setdefault(key, []).append(p)
        for (value, fp, lcsc, dnp), parts in groups.items():
            refs = sorted((p.ref for p in parts), key=refkey)
            p0 = parts[0]
            pr = prices.get(lcsc, ("", "", "", ""))
            short = refs[0] if len(refs) == 1 else f"{refs[0]}..{refs[-1]}" if len(refs) > 2 else " ".join(refs)
            pcb_only = not lcsc and any(k in fp for k in ("TestPoint", "SolderWirePad", "PinHeader_1.27mm"))
            status = "DNP" if dnp else ("PCB" if pcb_only else "SELECTED")
            rows.append(dict(ref=f"{board}:{short}", status=status, qty=0 if dnp else len(refs) * mult,
                             function=f"{value} ({p0.lib_id.split(':')[-1]})", mpn=p0.fields.get("MPN", value),
                             manufacturer=p0.fields.get("Manufacturer", ""), package=fp.split(":")[-1], lcsc=lcsc,
                             lcsc_check="page" if lcsc else "", unit_usd=pr[0], price_break=pr[1], stock_seen=pr[2],
                             fetched_utc=pr[3], datasheet_url=p0.fields.get("Datasheet", ""),
                             notes=(f"x{mult} boards; " if mult > 1 else "") + " ".join(refs) +
                             (f"; {p0.fields['Note']}" if "Note" in p0.fields else "") +
                             (f"; alt {p0.fields['Alternate']}" if "Alternate" in p0.fields else "")))
    for r in g1:
        if r["ref"] in OFFBOARD:
            rows.append({k: r.get(k, "") for k in COLS})
    rows.append(dict(ref="FLOW1", status="SELECTED", qty=1, function="Optical flow + down ToF module (D-047)", mpn="Flow deck v2",
                     manufacturer="Bitcraze", package="21x28x4 mm 1.6 g", lcsc="", lcsc_check="n/a", unit_usd="55.00",
                     price_break="1", stock_seen="'Add to Cart' shown", fetched_utc="2026-10-07",
                     datasheet_url="https://www.bitcraze.io/products/flow-deck-v2/", notes="Bought from Bitcraze; wired to FC J10"))
    with open(OUT, "w", newline="") as f:
        f.write("# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2\n")
        f.write("# One drone's parts generated from the G2 schematics (tools/sch/costed_bom.py) plus off-board items from bom/drone-bom-g1.csv.\n")
        f.write("# Prices seen 2026-10-04..07; EMPTY unit_usd = not priced (UNCONFIRMED). Board multiplicity: FC 1, ESC 1, ToF side 3, ToF front 1.\n")
        f.write("# status PCB = copper pads/test points (no purchased part); DNP = footprint left empty.\n")
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    total = sum(float(r["unit_usd"]) * int(r["qty"]) for r in rows if r["status"] == "SELECTED" and r["unit_usd"])
    unpriced = [r["ref"] for r in rows if r["status"] == "SELECTED" and not r["unit_usd"]]
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} lines, priced total ${total:.2f}, unpriced: {', '.join(unpriced)}")


if __name__ == "__main__":
    main()
