# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Load KiCad 7 symbol libraries, flatten derived symbols, list pins (MIT)."""
import copy
import pathlib

from sexpr import Sym, find, find_all, parse

STOCK = pathlib.Path("/usr/share/kicad/symbols")
# Copies of the KiCad 7 library symbols this project uses (tools/sch/vendor.py), so the
# schematics regenerate identically with KiCad 7, 8 or 9 installed.
VENDOR = pathlib.Path(__file__).resolve().parents[2] / "hardware" / "libraries" / "kicad7-symbols"
USE_VENDOR = True
_cache = {}


def _load_lib(path):
    if path not in _cache:
        tree = parse(pathlib.Path(path).read_text())[0]
        _cache[path] = {e[1]: e for e in find_all(tree, "symbol")}
    return _cache[path]


def lib_path(lib, extra_libs, name=None):
    if lib in extra_libs:
        return extra_libs[lib]
    v = VENDOR / f"{lib}.kicad_sym"
    if USE_VENDOR and v.exists() and (name is None or name in _load_lib(v)):
        return v
    p = STOCK / f"{lib}.kicad_sym"
    if not p.exists():
        raise FileNotFoundError(f"symbol library {lib} not found")
    return p


def get_symbol(lib_id, extra_libs=None):
    """Return a flattened copy of the symbol named 'Lib:Name' with its top name set to lib_id."""
    extra_libs = extra_libs or {}
    lib, name = lib_id.split(":", 1)
    syms = _load_lib(lib_path(lib, extra_libs, name))
    if name not in syms:
        raise KeyError(f"{lib_id} not in library")
    s = copy.deepcopy(syms[name])
    ext = find(s, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        pname = ext[1]
        # keep the child's properties, take the parent's flags and graphics
        child_props = {p[1]: p for p in find_all(s, "property")}
        out = [Sym("symbol"), name]
        for e in parent[2:]:
            if isinstance(e, list) and e and e[0] == "property":
                out.append(child_props.pop(e[1], e))
            elif isinstance(e, list) and e and e[0] == "symbol":
                sub = copy.deepcopy(e)
                sub[1] = sub[1].replace(pname + "_", name + "_", 1)
                out.append(sub)
            else:
                out.append(e)
        for p in child_props.values():
            out.append(p)
        s = out
    s[1] = lib_id
    return s


def pins(sym):
    """List of dicts: number, name, type, x, y (lib coords, connection point), angle, unit, hidden."""
    res = []
    base = sym[1].split(":", 1)[-1]
    for sub in find_all(sym, "symbol"):
        parts = sub[1].rsplit("_", 2)
        unit = int(parts[-2]) if len(parts) >= 3 and parts[-2].isdigit() else 0
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            nm = find(p, "name")
            nu = find(p, "number")
            res.append(dict(number=str(nu[1]), name=str(nm[1]), type=str(p[1]),
                            x=float(at[1]), y=float(at[2]), angle=int(float(at[3])) if len(at) > 3 else 0,
                            unit=unit, hidden=any(e == "hide" for e in p)))
    return res


def is_power_symbol(sym):
    return find(sym, "power") is not None


def bbox(sym):
    """Approximate body extents in lib coordinates (xmin, ymin, xmax, ymax), pins included."""
    xs, ys = [], []
    for sub in find_all(sym, "symbol"):
        for g in sub:
            if not isinstance(g, list):
                continue
            if g[0] in ("rectangle",):
                st, en = find(g, "start"), find(g, "end")
                xs += [float(st[1]), float(en[1])]
                ys += [float(st[2]), float(en[2])]
            elif g[0] in ("polyline",):
                for xy in find_all(find(g, "pts"), "xy"):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif g[0] == "circle":
                c, r = find(g, "center"), float(find(g, "radius")[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
    for p in pins(sym):
        xs.append(p["x"]); ys.append(p["y"])
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))
