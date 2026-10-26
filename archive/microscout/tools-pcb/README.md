> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3

# tools/pcb: board layout scripts (G3)

Every MicroScout board is laid out by a Python script, so the layout can be rebuilt and diffed. The scripts run on **KiCad 7's `pcbnew` Python module** (system `python3`) and route with **Freerouting 1.9.0**. Licence: MIT (the boards they produce are CERN-OHL-S-2.0).

| Script | What it does |
|---|---|
| `footprints.py` | Writes the project footprints in `hardware/libraries/microscout.pretty` (SMD pad rows, pigtail pads, 3 mm holes, and two **estimated** land patterns: VL53L5CX and MLT-5020) |
| `common.py` | Netlist reader, footprint loading, courtyards, outline and holes |
| `layout.py` | `Layout`: builds a board from a G2 netlist, design rules and net classes, zones and keep-outs, Freerouting runs (DSN export, patching, SES import), stitching vias, save and DRC |
| `placer.py` | Legalising placer: puts each part at the nearest spot clear of courtyards, holes and keep-outs; optional 180-degree twin placement |
| `finisher.py` | Grid A* router for the connections Freerouting leaves open (exact clearances, vias), driven by KiCad's own DRC list |
| `fc.py`, `esc.py`, `tof.py` | One script per board: outline, hand-placed parts, placement hints, planes and pours, routing order |
| `report.py` | Common end: overlap check, late pours, zone fill, save, DRC report and JSON summary in `review/G3/drc/` |
| `copper.py` | Measures the copper actually drawn on the battery and motor-phase paths (appends to `trace-widths.md`) |
| `astar.c` | The finisher's grid search in C (compiled on first use with `cc`) |
| `currents.py` | IPC-2221 copper widths for the high-current paths (`review/G3/trace-widths.md`) |
| `export.py` | Per-layer SVG and PDF plots, coloured top and bottom PNGs |
| `render3d.py` | 3D renders (top, bottom, angled) via STEP, glTF and three.js |
| `g3_report.py` | `review/G3/summary.md` and `autorouted-nets.md` |

## How a board is made

1. Parts are created from the KiCad netlist exported at G2 (`review/G2/netlists/*.net`), so the board matches the schematic net for net.
2. Big parts are placed by hand in the script; the rest go next to the part they connect to.
3. Planes and copper islands that must exist before routing are drawn (the L2 GND plane, the battery-path islands, the ESC VBAT plane). Pours that only fill leftover space are added after routing.
4. Freerouting routes the board. On the ESC it routes motor channel 2, the script copies that copper onto channel 3 (its parts are a 180-degree copy), then routes channel 1 and copies it onto channel 4, then routes the shared nets.
5. Tracks Freerouting put on the GND plane layers or through the FC battery-path islands are removed. The finisher then tries every connection still open, with one local rip-up round. Finally, tracks KiCad flags for clearance are removed and routed once more.
6. Zones are filled, the board is saved, and KiCad's DRC writes `review/G3/drc/<board>.rpt`.

Rebuild commands are in `docs/setup-ubuntu.md`, step 7. Autorouting is not deterministic: a re-run gives different copper, so review the committed board files, not a fresh run.

## Known limits

- Freerouting cannot narrow a track at a fine-pitch pin, so power nets are routed at a width that fits the pins and the current is carried by pours. The pours' real width must be checked in the layer plots (`review/G3/trace-widths.md`).
- Pours added after routing fill only the space the router left: on the ESC this left the motor phases far too narrow (`review/G3/README.md`). Power copper must be drawn before routing.
- Freerouting has no differential-pair support; the USB pair is two ordinary 0.2 mm nets.
- KiCad 7 cannot run DRC or ERC from the command line; the scripts call `pcbnew.WriteDRCReport`. Re-run DRC in KiCad 9 (setup guide step 7).
