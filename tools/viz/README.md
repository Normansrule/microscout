> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# tools/viz - figures, animations and the design explorer

Everything visual in this repo is generated from the G1 data, so the pictures change when the numbers change (decision D-027). Nothing here is a measurement. The 3D renders come from the concept CAD in `mechanical/concept/` (D-039), not a finished design, and the flights are simulations with estimated parameters.

| Script | Reads | Writes |
|---|---|---|
| `figures.py` | `review/G1/calc/budgets.py`, `bom/drone-bom-g1.csv`, `review/G1/pin-allocation.csv`, the SDK simulator (flip chart) | `docs/figures/<name>-light.svg` and `-dark.svg` (8 charts) |
| `animations.py` | `budgets.py` | `docs/figures/anim/*.gif` (concept top view, ToF re-addressing, power-on sequence) |
| `export_sim.py` | the SDK simulator | `docs/data/sim_flip.json`, `docs/data/sim_demo.json` (pose tracks) |
| `render3d/render.py` | `mechanical/concept/out/microscout_concept.glb`, `docs/viewer/scene.js`, `docs/data/sim_flip.json` | `docs/figures/renders/*.png`, `turntable.gif`, `sim-backflip.gif` |
| `build_site.py` | the same data + `site_template.html` + the open questions in `review/G1/README.md` | `docs/index.html` (GitHub Pages explorer with the 3D viewer) |

## Rebuild (in this order)

```bash
cd microscout
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/viz/requirements.txt cadquery playwright
python3 mechanical/concept/microscout_concept.py     # CAD + GLB (feeds frame mass to the budget)
python3 review/G1/calc/budgets.py
python3 tools/viz/export_sim.py
cd tools/viz && python3 figures.py && python3 animations.py && python3 build_site.py && cd ../..
(cd tools/viz/render3d && npm install)                # three.js for the renderer
python3 tools/viz/render3d/render.py                 # set CHROMIUM=/path/to/chrome if Playwright has no browser
```

## Conventions

- Colours: a fixed categorical order, checked for colour-vision deficiency with a palette validator; slots 3-5 are low-contrast on white, so those charts always carry direct labels.
- Every chart has a light and a dark SVG; the README uses `<picture>` so GitHub shows the one matching your theme.
- SVG text is converted to outlines so it renders the same everywhere.
- GIF frames cannot hold a file header, so each frame carries a DRAFT - UNVERIFIED footer and says which values are sourced, calculated or illustrative.
- The explorer page embeds its numbers; the 3D viewer loads three.js from jsDelivr and the model from `docs/models/`, so serve `docs/` over HTTP (GitHub Pages does) to use it.
- Renders say CONCEPT on every frame: the frame and canopy are parametric CAD, everything else is an envelope.
