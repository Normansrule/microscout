# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Generate KiCad 7 schematics (.kicad_sch) from a Python netlist description.

Style: every pin gets a short wire stub ending in a net label, a power symbol, or a
no-connect flag ("label-per-pin" schematics). Connectivity is therefore fully defined by
net names, which `check.py` compares against KiCad's own exported netlist.

Licence: MIT (software/LICENSE).
"""
import copy
import datetime
import json
import math
import pathlib
import re
import uuid

from sexpr import Sym, dump, find, find_all
from symlib import bbox, get_symbol, is_power_symbol, pins

GRID = 1.27
STUB = 2.54
FONT = 1.27
CHAR_W = 1.0          # estimated label character advance at 1.27 mm text (layout only)
NS = uuid.UUID("6f1c0e2a-6d3b-4d55-9a3e-0b9d1d6c2a11")

# Rails drawn with power symbols. Value = net name. Stock symbols where they exist.
POWER_SYMBOLS = {
    "GND": "power:GND",
    "+3V3": "power:+3V3",
    "+5V": "power:+5V",
    "VBUS": "power:VBUS",
    "+2V8": "power:+2V8",
    "+1V2": "power:+1V2",
}
CUSTOM_POWER = ("VBAT", "VLOGIC", "VDRV", "+3V3_ESC")   # created in microscout.kicad_sym


def U(*names):
    return str(uuid.uuid5(NS, "/".join(str(n) for n in names)))


def snap(v, g=2.54):
    return round(round(v / g) * g, 4)


def clean(name):
    return re.sub(r"~\{([^}]*)\}", r"\1", name)


def label_len(text, glob=False):
    return len(text) * CHAR_W + (3.0 if glob else 1.0)


class Part:
    def __init__(self, sheet, lib_id, ref, value, footprint, conn, fields, dnp=False):
        self.sheet = sheet
        self.lib_id = lib_id
        self.ref = ref
        self.value = value
        self.footprint = footprint
        self.fields = fields
        self.dnp = dnp
        self.sym = sheet.project.symbol(lib_id)
        self.pins = pins(self.sym)
        self.netmap = {}          # pin number -> net name or None (no-connect)
        self._assign(conn)

    def _assign(self, conn):
        by_num = {p["number"]: p for p in self.pins}
        by_name = {}
        for p in self.pins:
            by_name.setdefault(clean(p["name"]), []).append(p)
        for key, net in conn.items():
            key = str(key)
            if key in by_num:
                targets = [by_num[key]]
            elif clean(key) in by_name:
                targets = by_name[clean(key)]
            else:
                raise KeyError(f"{self.ref} ({self.lib_id}): no pin '{key}'. Pins: "
                               + ", ".join(f"{p['number']}={clean(p['name'])}" for p in self.pins))
            for p in targets:
                if p["number"] in self.netmap and self.netmap[p["number"]] != net:
                    raise ValueError(f"{self.ref} pin {p['number']} assigned twice")
                self.netmap[p["number"]] = net
        missing = [p for p in self.pins if p["number"] not in self.netmap]
        if missing:
            raise ValueError(f"{self.ref}: unassigned pins " + ", ".join(f"{p['number']}={clean(p['name'])}" for p in missing))


class Block:
    def __init__(self, title, notes):
        self.title = title
        self.notes = notes
        self.parts = []


class Sheet:
    def __init__(self, project, name, filename, title):
        self.project = project
        self.name = name
        self.filename = filename
        self.title = title
        self.blocks = []
        self.block("", [])

    def block(self, title, notes=()):
        self.blocks.append(Block(title, list(notes)))
        return self

    def add(self, lib_id, ref, value, footprint, conn, dnp=False, **fields):
        p = Part(self, lib_id, ref, value, footprint, conn, fields, dnp)
        self.blocks[-1].parts.append(p)
        self.project.register(p)
        return p

    # two-terminal helpers -------------------------------------------------------------
    def R(self, ref, value, a, b, pkg="0402", **f):
        fp = {"0402": "Resistor_SMD:R_0402_1005Metric", "0603": "Resistor_SMD:R_0603_1608Metric",
              "0805": "Resistor_SMD:R_0805_2012Metric", "1206": "Resistor_SMD:R_1206_3216Metric",
              "2512": "Resistor_SMD:R_2512_6332Metric"}[pkg]
        f.setdefault("Package", pkg)
        _fill("R", value, pkg, f)
        return self.add("Device:R", ref, value, fp, {"1": a, "2": b}, **f)

    def C(self, ref, value, a, b, pkg="0402", **f):
        fp = {"0402": "Capacitor_SMD:C_0402_1005Metric", "0603": "Capacitor_SMD:C_0603_1608Metric",
              "0805": "Capacitor_SMD:C_0805_2012Metric", "1206": "Capacitor_SMD:C_1206_3216Metric"}.get(pkg, pkg)
        f.setdefault("Package", pkg)
        _fill("C", value, pkg, f)
        return self.add("Device:C", ref, value, fp, {"1": a, "2": b}, **f)

    def CP(self, ref, value, plus, minus, fp, **f):
        return self.add("Device:C_Polarized", ref, value, fp, {"1": plus, "2": minus}, **f)

    def L(self, ref, value, a, b, fp, **f):
        return self.add("Device:L", ref, value, fp, {"1": a, "2": b}, **f)

    def D(self, ref, value, anode, cathode, fp="Diode_SMD:D_SOD-323", lib="Device:D_Schottky", **f):
        return self.add(lib, ref, value, fp, {"A": anode, "K": cathode}, **f)

    def TP(self, ref, net, fp="TestPoint:TestPoint_Pad_D1.0mm", **f):
        f.setdefault("Note", f"test point on {net}")
        return self.add("Connector:TestPoint", ref, "TP", fp, {"1": net}, **f)


def _fill(kind, value, pkg, f):
    from parts import lookup
    hit = lookup(kind, value, pkg)
    if hit and "LCSC" not in f:
        f["LCSC"], f["MPN"], f["Rating"] = hit


class Project:
    def __init__(self, name, outdir, title, rev, extra_libs, company="MicroScout (open hardware, CERN-OHL-S-2.0)",
                 status="STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2"):
        self.name = name
        self.outdir = pathlib.Path(outdir)
        self.title = title
        self.rev = rev
        self.extra_libs = extra_libs
        self.company = company
        self.status = status
        self.sheets = []
        self.parts = {}
        self._syms = {}
        self.root_uuid = U(name, "root")

    def symbol(self, lib_id):
        if lib_id not in self._syms:
            self._syms[lib_id] = get_symbol(lib_id, self.extra_libs)
        return self._syms[lib_id]

    def sheet(self, name, title):
        s = Sheet(self, name, f"{name}.kicad_sch", title)
        self.sheets.append(s)
        return s

    def register(self, part):
        if part.ref in self.parts:
            raise ValueError(f"duplicate reference {part.ref}")
        self.parts[part.ref] = part

    # netlist view ----------------------------------------------------------------------
    def nets(self):
        nets = {}
        for p in self.parts.values():
            for num, net in p.netmap.items():
                if net is not None:
                    nets.setdefault(net, []).append((p.ref, num))
        return nets

    def net_sheets(self):
        res = {}
        for s in self.sheets:
            for b in s.blocks:
                for p in b.parts:
                    for net in p.netmap.values():
                        if net is not None:
                            res.setdefault(net, set()).add(s.name)
        return res

    # writing ---------------------------------------------------------------------------
    def write(self):
        self.outdir.mkdir(parents=True, exist_ok=True)
        multi = self.net_sheets()
        for i, s in enumerate(self.sheets):
            SheetWriter(self, s, page=i + 2, global_nets={n for n, ss in multi.items() if len(ss) > 1}).write()
        self._write_root()
        self._write_project_files()

    def _write_root(self):
        items = []
        x, y = 30.48, 50.8
        for i, s in enumerate(self.sheets):
            su = U(self.name, "sheet", s.name)
            items.append([Sym("sheet"), [Sym("at"), x, y], [Sym("size"), 60.96, 20.32], [Sym("fields_autoplaced")],
                          [Sym("stroke"), [Sym("width"), 0.1524], [Sym("type"), Sym("solid")]],
                          [Sym("fill"), [Sym("color"), 0, 0, 0, 0.0]],
                          [Sym("uuid"), su],
                          prop("Sheetname", s.title, x, y - 0.7, justify="left bottom"),
                          prop("Sheetfile", s.filename, x, y + 20.32 + 0.6, justify="left top"),
                          [Sym("instances"), [Sym("project"), self.name,
                                              [Sym("path"), "/" + self.root_uuid, [Sym("page"), str(i + 2)]]]]])
            x += 76.2
            if x > 330:
                x = 30.48
                y += 38.1
        notes = [self.status, f"{self.title} - root sheet. Sub-sheets: " + ", ".join(s.title for s in self.sheets) + ".",
                 "Generated by tools/sch from hardware/*/design/*.py - edit the Python, not this file, until G3 hand-off.",
                 "Connectivity: net labels and power symbols; check report in review/G2/."]
        yy = 25.4
        for n in notes:
            items.append(text(n, 30.48, yy, size=2.0 if n is notes[0] else 1.5))
            yy += 5.08
        doc = [Sym("kicad_sch"), [Sym("version"), Sym("20230121")], [Sym("generator"), Sym("eeschema")],
               [Sym("uuid"), self.root_uuid], [Sym("paper"), "A4"],
               title_block(self.title + " - root", self.rev, self.company, self.status, "1"),
               [Sym("lib_symbols")]] + items + [
               [Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]]]
        (self.outdir / f"{self.name}.kicad_sch").write_text(header() + dump(doc) + "\n")

    def _write_project_files(self):
        tpl = pathlib.Path("/usr/share/kicad/template/kicad.kicad_pro")
        pro = json.loads(tpl.read_text()) if tpl.exists() else {}
        pro.setdefault("meta", {})["filename"] = f"{self.name}.kicad_pro"
        sheets = [[self.root_uuid, ""]] + [[U(self.name, "sheet", s.name), s.title] for s in self.sheets]
        pro["sheets"] = sheets
        (self.outdir / f"{self.name}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
        rel = {k: pathlib.Path(v) for k, v in self.extra_libs.items()}
        lines = ["(sym_lib_table"]
        for k, v in rel.items():
            lines.append(f'  (lib (name "{k}")(type "KiCad")(uri "${{KIPRJMOD}}/{relpath(v, self.outdir)}")(options "")(descr "MicroScout project symbols"))')
        lines.append(")")
        (self.outdir / "sym-lib-table").write_text("\n".join(lines) + "\n")


def relpath(target, start):
    import os
    return os.path.relpath(pathlib.Path(target).resolve(), pathlib.Path(start).resolve())


def header():
    return ""


def prop(name, value, x, y, angle=0, hide=False, justify=None, size=FONT):
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), size, size]]]
    if justify:
        eff.append([Sym("justify")] + [Sym(j) for j in justify.split()])
    if hide:
        eff.append(Sym("hide"))
    return [Sym("property"), name, str(value), [Sym("at"), round(x, 4), round(y, 4), angle], eff]


def text(s, x, y, size=1.27):
    return [Sym("text"), s, [Sym("at"), round(x, 4), round(y, 4), 0],
            [Sym("effects"), [Sym("font"), [Sym("size"), size, size]], [Sym("justify"), Sym("left"), Sym("bottom")]],
            [Sym("uuid"), U("text", s, x, y)]]


def title_block(title, rev, company, status, page):
    return [Sym("title_block"), [Sym("title"), title], [Sym("date"), datetime.date.today().isoformat()],
            [Sym("rev"), rev], [Sym("company"), company], [Sym("comment"), 1, status],
            [Sym("comment"), 2, "Generated schematic - not reviewed. Values are first-pass G2 choices."]]


def fields_right(part):
    return all(p["angle"] in (90, 270) for p in part.pins) and len(part.pins) <= 3


def fields(part, X, Y, bx0, by0, bx1, by1):
    if fields_right(part):
        return [prop("Reference", part.ref, X + bx1 + 1.0, Y - 0.6, justify="left bottom"),
                prop("Value", part.value, X + bx1 + 1.0, Y + 1.9, justify="left bottom")]
    return [prop("Reference", part.ref, X + bx0, Y - by1 - 1.0, justify="left bottom"),
            prop("Value", part.value, X + bx0, Y - by0 + 2.6, justify="left bottom")]


DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # outward direction in schematic coords


class SheetWriter:
    def __init__(self, project, sheet, page, global_nets):
        self.p = project
        self.s = sheet
        self.page = page
        self.global_nets = global_nets
        self.items = []
        self.used_libs = {}
        self.pwr_count = 0
        self.sheet_uuid = U(project.name, "sheet", sheet.name)

    # geometry of one part relative to its anchor ------------------------------------------
    def part_geometry(self, part):
        bx0, by0, bx1, by1 = bbox(part.sym)
        xs = [bx0, bx1]
        ys = [-by1, -by0]
        ends = []
        seen = {}
        for pin in part.pins:
            px, py = pin["x"], -pin["y"]
            key = (round(px, 3), round(py, 3))
            net = part.netmap[pin["number"]]
            if key in seen:
                if seen[key] != net:
                    raise ValueError(f"{part.ref}: stacked pins at {key} on different nets ({seen[key]}, {net})")
                continue
            seen[key] = net
            dx, dy = DIRS[pin["angle"] % 360]
            if net is None:
                ends.append((pin, px, py, None, dx, dy))
                continue
            ex, ey = px + dx * STUB, py + dy * STUB
            if net in POWER_SYMBOLS or net in CUSTOM_POWER:
                ln = 3.0 if (net == "GND" and dy == 0) else 5.6 + len(net) * CHAR_W
            else:
                ln = label_len(net, net in self.global_nets)
            xs += [ex, ex + dx * ln]
            ys += [ey, ey + dy * ln]
            if dx == 0:   # vertical label text also has width
                xs += [ex - 1.5, ex + 1.5]
            else:
                ys += [ey - 1.5, ey + 1.5]
            ends.append((pin, px, py, (ex, ey), dx, dy))
        if fields_right(part):
            xs += [bx1 + 1.5 + max(len(part.ref), len(part.value)) * CHAR_W]
        else:
            ys += [-by1 - 3.5, -by0 + 3.5]      # reference above, value below
        return (min(xs), min(ys), max(xs), max(ys)), ends

    def layout(self):
        """Shelf-pack parts inside blocks, blocks on the page. Returns placements and paper."""
        geos = {id(pt): self.part_geometry(pt) for b in self.s.blocks for pt in b.parts}
        for paper, (W, H) in (("A3", (420, 297)), ("A2", (594, 420)), ("A1", (841, 594)), ("A0", (1189, 841))):
            for maxw in (120.0, 160.0, 200.0, 260.0, 340.0):
                blocks = self._blocks(geos, maxw)
                ok, plac = self._pack(blocks, W, H)
                if ok:
                    return paper, plac
        raise RuntimeError(f"sheet {self.s.name} does not fit on A0")

    def _blocks(self, geos, maxw):
        margin = 2.54
        blocks = []
        for b in self.s.blocks:
            if not b.parts:
                continue
            geo = [(pt, *geos[id(pt)]) for pt in b.parts]
            x = y = 0.0
            rowh = 0.0
            places = []
            for pt, (x0, y0, x1, y1), ends in geo:
                w, h = x1 - x0 + margin, y1 - y0 + margin
                if x > 0 and x + w > maxw:
                    x = 0.0
                    y += rowh
                    rowh = 0.0
                places.append((pt, x - x0, y - y0, ends))
                x += w
                rowh = max(rowh, h)
            import textwrap
            bw = max(maxw if y > 0 else x, min(maxw, max((len(n) * 1.0 for n in b.notes + [b.title]), default=0)))
            tlines = textwrap.wrap(b.title, max(30, int(bw / 1.35))) or [""]
            wrapped = [w for n in b.notes for w in textwrap.wrap(n, max(40, int(bw / 1.0)))]
            head = 1.9 + 3.2 * len(tlines) + 3.2 * len(wrapped) if (b.title or b.notes) else 0
            wrapped = (tlines, wrapped)
            bh = y + rowh + head
            blocks.append((b, places, bw, bh, head, wrapped))
        return blocks

    def _pack(self, blocks, W, H):
        left, top, right, bottom = 15.24, 30.48, W - 15.24, H - 40.0
        x, y, rowh = left, top, 0.0
        out = []
        for b, places, bw, bh, head, wrapped in blocks:
            if x > left and x + bw > right:
                x = left
                y += rowh + 7.62
                rowh = 0.0
            if y + bh > bottom or x + bw > right + 1:
                return False, None
            out.append((b, places, x, y, head, wrapped))
            x += bw + 10.16
            rowh = max(rowh, bh)
        return True, out

    def write(self):
        paper, placed = self.layout()
        self.items.append(text(self.p.status, 15.24, 17.78, size=2.0))
        self.items.append(text(f"{self.p.title} - {self.s.title}", 15.24, 22.86, size=1.8))
        for b, places, bx, by, head, wrapped in placed:
            if b.title or b.notes:
                tlines, notes = wrapped
                for i, t in enumerate(tlines):
                    self.items.append(text(t, bx, by + 3.0 + 3.2 * i, size=1.6))
                for i, n in enumerate(notes):
                    self.items.append(text(n, bx, by + 3.0 + 3.2 * len(tlines) + 3.2 * i, size=1.15))
            for pt, ox, oy, ends in places:
                X = snap(bx + ox)
                Y = snap(by + head + oy)
                self.place(pt, X, Y, ends)
        lib_syms = [copy.deepcopy(self.used_libs[k]) for k in sorted(self.used_libs)]
        doc = [Sym("kicad_sch"), [Sym("version"), Sym("20230121")], [Sym("generator"), Sym("eeschema")],
               [Sym("uuid"), self.sheet_uuid], [Sym("paper"), paper],
               title_block(f"{self.p.title} - {self.s.title}", self.p.rev, self.p.company, self.p.status, str(self.page)),
               [Sym("lib_symbols")] + lib_syms] + self.items + [
               [Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]]]
        (self.p.outdir / self.s.filename).write_text(dump(doc) + "\n")

    def _use(self, lib_id):
        if lib_id not in self.used_libs:
            self.used_libs[lib_id] = self.p.symbol(lib_id)

    def _instances(self, ref):
        return [Sym("instances"), [Sym("project"), self.p.name,
                                   [Sym("path"), f"/{self.p.root_uuid}/{self.sheet_uuid}",
                                    [Sym("reference"), ref], [Sym("unit"), 1]]]]

    def place(self, part, X, Y, ends):
        self._use(part.lib_id)
        bx0, by0, bx1, by1 = bbox(part.sym)
        su = U(self.p.name, "part", part.ref)
        node = [Sym("symbol"), [Sym("lib_id"), part.lib_id], [Sym("at"), X, Y, 0], [Sym("unit"), 1],
                [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("yes" if part.dnp else "no")],
                [Sym("uuid"), su],
                *(fields(part, X, Y, bx0, by0, bx1, by1)),
                prop("Footprint", part.footprint, X, Y, hide=True),
                prop("Datasheet", part.fields.get("Datasheet", "~"), X, Y, hide=True)]
        for k, v in part.fields.items():
            if k == "Datasheet":
                continue
            node.append(prop(k, v, X, Y, hide=True))
        for pin in part.pins:
            node.append([Sym("pin"), pin["number"], [Sym("uuid"), U(self.p.name, part.ref, "pin", pin["number"])]])
        node.append(self._instances(part.ref))
        self.items.append(node)
        for pin, px, py, end, dx, dy in ends:
            sx, sy = round(X + px, 4), round(Y + py, 4)
            net = part.netmap[pin["number"]]
            if net is None:
                self.items.append([Sym("no_connect"), [Sym("at"), sx, sy], [Sym("uuid"), U(self.p.name, part.ref, "nc", pin["number"])]])
                continue
            ex, ey = round(X + end[0], 4), round(Y + end[1], 4)
            self.items.append([Sym("wire"), [Sym("pts"), [Sym("xy"), sx, sy], [Sym("xy"), ex, ey]],
                               [Sym("stroke"), [Sym("width"), 0], [Sym("type"), Sym("default")]],
                               [Sym("uuid"), U(self.p.name, part.ref, "w", pin["number"])]])
            if net in POWER_SYMBOLS or net in CUSTOM_POWER:
                self.power(net, ex, ey, dx, dy, (part.ref, pin["number"]))
            else:
                self.label(net, ex, ey, dx, dy, (part.ref, pin["number"]))

    def label(self, net, x, y, dx, dy, key):
        angle = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}[(dx, dy)]
        just = "right" if angle in (180, 270) else "left"
        if net in self.global_nets:
            self.items.append([Sym("global_label"), net, [Sym("shape"), Sym("passive")], [Sym("at"), x, y, angle],
                               [Sym("fields_autoplaced")],
                               [Sym("effects"), [Sym("font"), [Sym("size"), FONT, FONT]], [Sym("justify"), Sym(just)]],
                               [Sym("uuid"), U(self.p.name, "gl", *key)],
                               prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, hide=True)])
        else:
            self.items.append([Sym("label"), net, [Sym("at"), x, y, angle], [Sym("fields_autoplaced")],
                               [Sym("effects"), [Sym("font"), [Sym("size"), FONT, FONT]], [Sym("justify"), Sym(just), Sym("bottom")]],
                               [Sym("uuid"), U(self.p.name, "lb", *key)]])

    def _pvalue(self, net, x, y, dx, dy, rot):
        if dy == 0 and net == "GND":   # the ground symbol is self-explanatory; avoid text pile-ups
            return prop("Value", net, x, y, hide=True)
        if dy == 0:     # horizontal: keep text horizontal, beyond the symbol
            return prop("Value", net, x + dx * 4.6, y + 0.5, angle=90 if rot in (90, 270) else 0,
                        justify="left")
        return prop("Value", net, x, y + dy * 4.8 + (1.0 if dy > 0 else 0), angle=0)

    def power(self, net, x, y, dx, dy, key):
        lib_id = POWER_SYMBOLS.get(net) or f"microscout:{net}"
        self._use(lib_id)
        self.pwr_count += 1
        ref = f"#PWR{self.page:02d}{self.pwr_count:03d}"
        # stock ground symbols point down at 0 deg, supply symbols point up
        is_gnd = net == "GND"
        if is_gnd:
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[(dx, dy)]
        else:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[(dx, dy)]
        su = U(self.p.name, "pwr", *key)
        node = [Sym("symbol"), [Sym("lib_id"), lib_id], [Sym("at"), x, y, rot], [Sym("unit"), 1],
                [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("no")],
                [Sym("uuid"), su],
                prop("Reference", ref, x, y, hide=True),
                self._pvalue(net, x, y, dx, dy, rot),
                prop("Footprint", "", x, y, hide=True), prop("Datasheet", "", x, y, hide=True)]
        for pin in pins(self.p.symbol(lib_id)):
            node.append([Sym("pin"), pin["number"], [Sym("uuid"), U(su, pin["number"])]])
        node.append(self._instances(ref))
        self.items.append(node)
