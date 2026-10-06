> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1

# tools/viz - figures, animations and the design explorer

Everything visual in this repo is generated from the G1 data, so the pictures change when the numbers change (decision D-027). Nothing here is a measurement, a CAD render or a simulation of real hardware.

| Script | Reads | Writes |
|---|---|---|
| `figures.py` | `review/G1/calc/budgets.py`, `bom/drone-bom-g1.csv`, `review/G1/pin-allocation.csv` | `docs/figures/<name>-light.svg` and `-dark.svg` (7 charts) |
| `animations.py` | `budgets.py` | `docs/figures/anim/*.gif` (concept top view, ToF re-addressing, power-on sequence) |
| `build_site.py` | the same data + `site_template.html` + the open questions in `review/G1/README.md` | `docs/index.html`, served by GitHub Pages at <https://normansrule.github.io/microscout/> |

## Rebuild

```bash
cd microscout
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/viz/requirements.txt
python3 review/G1/calc/budgets.py          # refresh the numbers first
cd tools/viz
python3 figures.py && python3 animations.py && python3 build_site.py
```

## Conventions

- Colours: a fixed categorical order, checked for colour-vision deficiency with a palette validator; slots 3-5 are low-contrast on white, so those charts always carry direct labels.
- Every chart has a light and a dark SVG; the README uses `<picture>` so GitHub shows the one matching your theme.
- SVG text is converted to outlines so it renders the same everywhere.
- GIF frames cannot hold a file header, so each frame carries a DRAFT - UNVERIFIED footer and says which values are sourced, calculated or illustrative.
- The explorer page embeds its data, so it also works when opened straight from disk.
