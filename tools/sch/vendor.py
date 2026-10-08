# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Copy the KiCad 7 library symbols and footprints this project uses into hardware/libraries/.

  python3 tools/sch/vendor.py      (run on a machine with the KiCad 7 libraries; rerun after adding a stock part)

Why: KiCad 9 renamed some symbol pins (e.g. ESP32-S3-WROOM-1 IO19/IO20 -> USB_D-/USB_D+) and some
footprints, so a fresh KiCad 9 install broke `build_all.py` and gave hundreds of library warnings.
With these copies plus the project sym-lib-table / fp-lib-table that schgen writes, every KiCad
version sees the same symbols and footprints. KiCad library licence: CC-BY-SA-4.0 with the
KiCad libraries exception (https://www.kicad.org/libraries/license/). Script licence: MIT.
"""
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import symlib  # noqa: E402
from sexpr import Sym, dump, find, find_all, parse  # noqa: E402

symlib.USE_VENDOR = False
LIBDIR = REPO / "hardware" / "libraries"
SYMOUT = LIBDIR / "kicad7-symbols"
FPOUT = LIBDIR / "kicad7-footprints"
DESIGNS = [REPO / "hardware/drone-pcb/design/fc.py", REPO / "hardware/esc-pcb/design/esc.py",
           REPO / "hardware/tof-satellites/design/tof.py"]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem + "_vend", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    import schgen
    lib_ids, fps = set(schgen.POWER_SYMBOLS.values()) | {"power:PWR_FLAG", "power:+3V3"}, set()
    for d in DESIGNS:
        ps = load(d).build()
        for proj in (ps if isinstance(ps, list) else [ps]):
            for p in proj.parts.values():
                if not p.lib_id.startswith("microscout:"):
                    lib_ids.add(p.lib_id)
                if p.footprint and not p.footprint.startswith("microscout:"):
                    fps.add(p.footprint)
    by_lib = {}
    for lid in sorted(lib_ids):
        lib, name = lid.split(":", 1)
        by_lib.setdefault(lib, set()).add(name)
    if SYMOUT.exists():
        shutil.rmtree(SYMOUT)
    SYMOUT.mkdir(parents=True)
    for lib, names in by_lib.items():
        tree = parse((symlib.STOCK / f"{lib}.kicad_sym").read_text())[0]
        syms = {e[1]: e for e in find_all(tree, "symbol")}
        need = set(names)
        for n in list(need):                       # parents of derived symbols
            ext = find(syms[n], "extends")
            if ext:
                need.add(ext[1])
        out = [Sym("kicad_symbol_lib"), [Sym("version"), Sym("20220914")], [Sym("generator"), Sym("microscout_vendor")]]
        out += [syms[n] for n in sorted(need)]
        (SYMOUT / f"{lib}.kicad_sym").write_text(dump(out) + "\n")
    if FPOUT.exists():
        shutil.rmtree(FPOUT)
    for fp in sorted(fps):
        lib, name = fp.split(":", 1)
        src = pathlib.Path("/usr/share/kicad/footprints") / f"{lib}.pretty" / f"{name}.kicad_mod"
        dst = FPOUT / f"{lib}.pretty" / f"{name}.kicad_mod"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    tpl = pathlib.Path("/usr/share/kicad/template/kicad.kicad_pro")
    if tpl.exists():
        shutil.copy(tpl, LIBDIR / "kicad7-template.kicad_pro")
    (LIBDIR / "README.md").write_text(
        "> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2\n\n# hardware/libraries\n\n"
        "- `microscout.kicad_sym` - project symbols (parts missing from KiCad 7, custom power rails), built by `tools/sch/customsyms.py`.\n"
        "- `kicad7-symbols/`, `kicad7-footprints/` - copies of the KiCad 7.0 library symbols and footprints this project uses, made by "
        "`tools/sch/vendor.py`. The project `sym-lib-table` / `fp-lib-table` files point at them, so KiCad 7, 8 and 9 all see the same parts.\n"
        "  Licence: CC-BY-SA-4.0 with the KiCad libraries exception (https://www.kicad.org/libraries/license/).\n"
        "- `kicad7-template.kicad_pro` - the KiCad 7 default project settings used for every generated project.\n")
    print(f"vendored {sum(len(v) for v in by_lib.values())} symbols from {len(by_lib)} libraries and {len(fps)} footprints")


if __name__ == "__main__":
    main()
