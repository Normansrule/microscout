# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Electrical-rules and consistency checks for a generated MicroScout schematic.

KiCad 7's command line cannot run ERC (added in KiCad 8), so this script checks the
source netlist itself and then proves the .kicad_sch files say the same thing:

  1. ERC on the source netlist (pin electrical types from the KiCad symbols):
     unassigned pins, single-pin nets, undriven power inputs, undriven inputs,
     output conflicts, open-drain nets without a pull-up, connected no-connect pins.
  2. Netlist match: KiCad's own exported netlist (kicad-cli sch export netlist) must
     group exactly the same pins into nets as the source.
  3. Footprints exist in the KiCad library (or are flagged as G3 custom footprints).
  4. Capacitors on 2S nets are rated >= 16 V.

The owner should still run KiCad's ERC in KiCad 8/9 (VERIFY.md, G2).
Licence: MIT.
"""
import pathlib
import re

from parts import CAP_RATING_V, HIGH_V_NETS
from sexpr import find, find_all, parse

FP_ROOT = pathlib.Path("/usr/share/kicad/footprints")
DRIVERS = {"output", "power_out", "bidirectional", "tri_state", "passive", "open_collector", "open_emitter", "unspecified"}


def is_supply(net):
    return net.startswith("+") or net in ("VBAT", "VLOGIC", "VDRV", "VBUS", "CHG_REGN")


def erc(project):
    errors, warns = [], []
    nets = project.nets()
    types = {}
    for p in project.parts.values():
        for pin in p.pins:
            types[(p.ref, pin["number"])] = (pin["type"], p.lib_id, pin["name"])
    for p in project.parts.values():
        for pin in p.pins:
            net = p.netmap[pin["number"]]
            if net is not None and pin["type"] == "no_connect":
                errors.append(f"{p.ref} pin {pin['number']} ({pin['name']}) is no-connect type but wired to {net}")
    for net, members in sorted(nets.items()):
        real = [m for m in members if not m[0].startswith("#")]
        flags = [m for m in members if m[0].startswith("#FLG")]
        uniq = {m for m in real}
        refs = {m[0] for m in real}
        if len(uniq) < 2 and not flags:
            errors.append(f"net {net}: only one pin ({', '.join(f'{r}.{n}' for r, n in real)})")
        elif len(refs) < 2 and not flags:
            warns.append(f"net {net}: all pins on one part ({next(iter(refs))})")
        t = [types[m][0] for m in members]
        if "power_in" in t and "power_out" not in t:
            errors.append(f"net {net}: power input(s) with no power output or PWR_FLAG")
        if "input" in t and not any(x in DRIVERS for x in t):
            errors.append(f"net {net}: inputs only, nothing drives it")
        if flags and "power_out" in [types[m][0] for m in members if not m[0].startswith("#")]:
            errors.append(f"net {net}: PWR_FLAG on a net already driven by a power output (KiCad reports this)")
        outs = [m for m in members if types[m][0] in ("output", "power_out") and not m[0].startswith("#")]
        if len(outs) > 1:
            errors.append(f"net {net}: {len(outs)} outputs ({', '.join(f'{r}.{n}' for r, n in outs)})")
        if "open_collector" in t:
            pulled = False
            for (r, n) in real:
                part = project.parts[r]
                if part.lib_id == "Device:R":
                    other = part.netmap["2" if n == "1" else "1"]
                    if other and is_supply(other):
                        pulled = True
                if part.lib_id == "Device:LED":
                    pulled = True        # charger STAT drives an LED from REGN
                if part.lib_id == "Transistor_FET:AO3400A" and n in ("2", "3"):
                    other = part.netmap["3" if n == "2" else "2"]   # through a pass FET to a pulled-up net
                    for (r2, n2) in nets.get(other, []):
                        p2 = project.parts[r2]
                        if p2.lib_id == "Device:R" and is_supply(p2.netmap["2" if n2 == "1" else "1"] or ""):
                            pulled = True
            if not pulled:
                warns.append(f"net {net}: open-drain output(s) without a pull-up resistor to a supply")
    return errors, warns


def read_kicad_netlist(path):
    tree = parse(pathlib.Path(path).read_text())[0]
    nets = {}
    for net in find_all(find(tree, "nets"), "net"):
        name = find(net, "name")[1]
        nodes = {(find(nd, "ref")[1], find(nd, "pin")[1]) for nd in find_all(net, "node")}
        nets[name] = nodes
    comps = {}
    for comp in find_all(find(tree, "components"), "comp"):
        ref = find(comp, "ref")[1]
        fp = find(comp, "footprint")
        comps[ref] = fp[1] if fp else ""
    return nets, comps


def compare(project, netfile):
    errors = []
    knets, comps = read_kicad_netlist(netfile)
    src = {}
    for net, members in project.nets().items():
        m = {x for x in members if not x[0].startswith("#")}
        if m:
            src[net] = m
    kgroups = {frozenset(v): k for k, v in knets.items() if not k.startswith("unconnected-")}
    sgroups = {frozenset(v): k for k, v in src.items()}
    for g, name in sgroups.items():
        if g not in kgroups:
            errors.append(f"source net {name} not found as an identical group in the KiCad netlist")
        else:
            kname = kgroups[g].split("/")[-1]
            if kname != name:
                errors.append(f"net name differs: source {name} vs KiCad {kgroups[g]}")
    for g, name in kgroups.items():
        if g not in sgroups:
            errors.append(f"KiCad net {name} has no identical source net ({sorted(g)[:4]}...)")
    nc_src = {(p.ref, n) for p in project.parts.values() for n, net in p.netmap.items() if net is None}
    nc_k = {next(iter(v)) for k, v in knets.items() if k.startswith("unconnected-") and len(v) == 1}
    if nc_src != nc_k:
        diff = sorted(nc_src ^ nc_k)[:6]
        errors.append(f"no-connect pins differ between source and KiCad: {diff}")
    srefs = {r for r in project.parts if not r.startswith("#")}
    if set(comps) != srefs:
        errors.append(f"component sets differ: {sorted(set(comps) ^ srefs)[:8]}")
    return errors, len(knets), len(comps)


def footprints(project):
    missing, custom = [], []
    for p in project.parts.values():
        if p.ref.startswith("#"):
            continue
        fp = p.footprint
        lib, _, name = fp.partition(":")
        if lib == "microscout":
            custom.append(f"{p.ref}: {name}")
            if not (pathlib.Path(__file__).resolve().parents[2] / "hardware/libraries/microscout.pretty" / f"{name}.kicad_mod").exists():
                missing.append(f"{p.ref}: {fp}")
            continue
        vend = pathlib.Path(__file__).resolve().parents[2] / "hardware" / "libraries" / "kicad7-footprints"
        if not (vend / f"{lib}.pretty" / f"{name}.kicad_mod").exists() and not (FP_ROOT / f"{lib}.pretty" / f"{name}.kicad_mod").exists():
            missing.append(f"{p.ref}: {fp}")
    return missing, custom


def cap_ratings(project):
    errs = []
    for p in project.parts.values():
        if p.lib_id not in ("Device:C", "Device:C_Polarized"):
            continue
        nets = set(p.netmap.values())
        v = CAP_RATING_V.get(p.fields.get("LCSC"))
        if v is None:
            errs.append(f"{p.ref}: no voltage rating on record")
        elif nets & HIGH_V_NETS and v < 16:
            errs.append(f"{p.ref} ({v} V) sits on {sorted(nets & HIGH_V_NETS)} (2S, up to 8.8 V)")
    return errs


def pins_used_by(project, net):
    return sorted(f"{r}.{n}" for r, n in project.nets().get(net, []) if not r.startswith("#"))


def report(project, netfile, title):
    e1, w1 = erc(project)
    e2, nk, nc = compare(project, netfile)
    miss, custom = footprints(project)
    e4 = cap_ratings(project)
    lines = ["> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2", "",
             f"# {title} - schematic check report", "",
             "Generated by `tools/sch/check.py`. KiCad 7 has no command-line ERC, so these checks run on the source",
             "netlist and then prove the `.kicad_sch` files match it. **Run KiCad's own ERC in KiCad 8/9 as well.**", "",
             "| Check | Result |", "|---|---|",
             f"| Source ERC errors | {len(e1)} |", f"| Source ERC warnings | {len(w1)} |",
             f"| KiCad netlist vs source | {'identical' if not e2 else str(len(e2)) + ' difference(s)'} ({nk} nets, {nc} parts in KiCad export) |",
             f"| Footprints missing from the KiCad 7 library | {len(miss)} |",
             f"| Custom footprints still to draw at G3 | {len(custom)} |",
             f"| Capacitor voltage-rating problems | {len(e4)} |", ""]
    for head, items in (("ERC errors", e1), ("ERC warnings", w1), ("Netlist differences", e2),
                        ("Missing footprints", miss), ("Custom footprints for G3", custom), ("Capacitor ratings", e4)):
        if items:
            lines += [f"## {head}", ""] + [f"- {x}" for x in items] + [""]
    return "\n".join(lines), (len(e1) + len(e2) + len(miss) + len(e4))
