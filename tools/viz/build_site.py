#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Build docs/index.html (the GitHub Pages design explorer) from the G1 data.

The page is self-contained: the G1 numbers are embedded as JSON so it also
works when opened straight from disk. Re-run after any change to the budgets,
BOM or pin table:  python3 tools/viz/build_site.py
"""
import json
import re

from figures import PIN_GROUPS, STRAPPING, short_load, short_weight_label
from theme import REPO, load_budgets, read_csv_rows

B = load_budgets()
TEMPLATE = REPO / "tools" / "viz" / "site_template.html"
OUT = REPO / "docs" / "index.html"


def data():
    items = B.weight_table()
    tot, lo, hi = B.weight_totals()
    weight = [dict(name=short_weight_label(n), full=n, value=round(v.value, 2), lo=round(v.rng()[0], 2),
                   hi=round(v.rng()[1], 2), kind=v.kind, basis=v.source) for n, v in items]
    rails = {}
    for key, rail, eff in (("3V3", B.RAIL33, B.EFF33), ("5V", B.RAIL5, B.EFF5)):
        rails[key] = dict(eff=eff.value, loads=[dict(name=short_load(n), full=n, peak=round(p, 2), avg=round(a, 2), tag=k, src=s)
                                                for n, p, a, k, s in rail])
    cost = []
    for r in read_csv_rows(REPO / "bom" / "drone-bom-g1.csv"):
        if r["status"] in ("SELECTED", "CONDITIONAL") and r["unit_usd"]:
            cost.append(dict(ref=r["ref"], mpn=r["mpn"], qty=int(r["qty"]), unit=float(r["unit_usd"]),
                             line=round(float(r["unit_usd"]) * int(r["qty"]), 4), fn=r["function"], lcsc=r["lcsc"],
                             brk=r["price_break"], url=r["datasheet_url"]))
    pins = []
    for r in read_csv_rows(REPO / "review" / "G1" / "pin-allocation.csv"):
        g = int(r["gpio"])
        gi = next(i for i, (_, f) in enumerate(PIN_GROUPS) if f(r["net"]))
        pins.append(dict(gpio=g, pin=int(r["module_pin"]), net=r["net"], fn=r["function"], dir=r["direction"],
                         pull=r["external_pull"], notes=r["boot_or_conflict_notes"], group=gi, strap=g in STRAPPING))
    oq = []
    for line in (REPO / "review" / "G1" / "README.md").read_text().splitlines():
        m = re.match(r"\| (OQ-\d+) \| (.+?) \| (.+?) \|$", line)
        if m:
            oq.append(dict(id=m.group(1), q=m.group(2), rec=m.group(3)))
    return dict(
        weight=weight, total=dict(nominal=round(tot, 2), lo=round(lo, 2), hi=round(hi, 2)),
        thrust=[dict(gf=t, tag=tag) for t, tag in B.THRUST_SCENARIOS], eta=list(B.ETA_GW),
        model=dict(v_nom=B.V_NOM.value, cap=B.CAP_MAH.value, derate=B.HV_DERATE.value, usable=B.USABLE_FRAC.value,
                   elec_a=round(B.electronics_battery_current_a(), 4), d_mm=B.MOTOR_TO_MOTOR_MM.value, prop_mm=B.PROP_MM.value),
        rails=rails, cost=cost, pins=pins, groups=[g for g, _ in PIN_GROUPS] + ["Power / reset"], oq=oq,
    )


def md_inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


if __name__ == "__main__":
    d = data()
    for q in d["oq"]:
        q["q"], q["rec"] = md_inline(q["q"]), md_inline(q["rec"])
    html = TEMPLATE.read_text().replace("/*__G1_DATA__*/null", json.dumps(d, ensure_ascii=False))
    OUT.write_text(html)
    print("wrote", OUT.relative_to(REPO), f"{len(html)/1024:.0f} kB")
