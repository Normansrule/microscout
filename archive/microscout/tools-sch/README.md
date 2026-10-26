> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2

# tools/sch - schematics from Python (D-051)

This folder turns the board descriptions in `hardware/*/design/*.py` into KiCad 7 schematics, then checks them. In the generated sheets every pin has a short wire ending in a net label, a power symbol or a no-connect flag, so net names define all the connectivity.

| File | What it does |
|---|---|
| `sexpr.py` | Reads and writes KiCad S-expressions |
| `symlib.py` | Loads KiCad symbol libraries, flattens derived symbols, lists pins |
| `customsyms.py` | Builds `hardware/libraries/microscout.kicad_sym`: parts missing from KiCad 7 (pin tables from the datasheets) and the custom power symbols |
| `schgen.py` | `Project` / `Sheet` / `Part` classes, the layout (blocks with notes, shelf packing) and the `.kicad_sch` / `.kicad_pro` writer |
| `parts.py` | LCSC numbers for the passives (checked 2026-10-07), plus capacitor voltage ratings |
| `check.py` | ERC on the source netlist, comparison with KiCad's exported netlist, footprint and capacitor-rating checks |
| `build_all.py` | Regenerates every board and writes PDFs, netlists, check reports and per-board BOMs to `review/G2/` |
| `costed_bom.py` | Writes `bom/drone-bom-g2.csv` for one drone (board counts, prices, off-board items) |
| `summaries.py` | Writes `review/G2/pullups-straps.md` |

## Running it

Run these from the repository root. They need `kicad-cli` (KiCad 7 or later) and Python 3; no other packages are required.

```bash
python3 tools/sch/build_all.py      # exits non-zero on any check failure
python3 tools/sch/costed_bom.py
python3 tools/sch/summaries.py
```

## Editing a board

Edit its Python file, not the `.kicad_sch` output. Moving to hand-edited KiCad files is a G3 decision.

`Sheet.add(lib_id, ref, value, footprint, {pin: net})` places a part. Each key in the mapping is a pin number or a pin name, and a name covers every pin that carries it. A value of `None` marks the pin as a no-connect.

The two-terminal helpers are `R`, `C`, `CP`, `L`, `D` and `TP`.
