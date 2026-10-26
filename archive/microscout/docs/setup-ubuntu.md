> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3 (owner actions; D-002, OQ-7)

# From a fresh Ubuntu terminal: update GitHub, publish, and run everything

These commands were written for **Ubuntu 24.04**. Run them in order; each step says when you can skip it. The agent's session can push commits to `Normansrule/microscout`, but it cannot change repository settings or push tags. So step 4 (make the repo public, turn on Pages, add tags) is yours to run.

> [!NOTE]
> Nothing in this repository has been built or tested. Publishing makes the **drafts** public, including the full git history and commit author names and emails.

## 1. Install the tools (once per machine)

```bash
sudo apt update
sudo apt install -y git gh python3 python3-venv python3-pip
git --version && gh --version && python3 --version
```

## 2. Log in to GitHub (once per machine)

```bash
gh auth login --hostname github.com --git-protocol https --web   # follow the browser prompt
gh auth setup-git                                                # lets git push with your gh login
gh auth status                                                   # should say: Logged in to github.com account Normansrule
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"   # use your GitHub no-reply address to keep your email private
```

## 3. Get the latest version of the repository

```bash
# first time on this machine
git clone https://github.com/Normansrule/microscout.git ~/microscout
cd ~/microscout

# if you already have a copy
cd ~/microscout && git fetch origin && git status    # shows whether you are behind
git pull --rebase origin main

git log --oneline -5      # the newest commit should mention G2 / schematics
```

If `git pull` complains about local changes you don't need, run `git stash` first, or `git reset --hard origin/main` to throw them away. **The second command deletes your uncommitted changes.**

## 4. Publish: make the repo public, turn on the explorer, add tags (once)

```bash
cd ~/microscout

# 4a. Public repo, description, homepage and topics
gh repo edit Normansrule/microscout \
  --visibility public --accept-visibility-change-consequences \
  --description "Open-source palm-sized ESP32-S3 brushless camera drone - DRAFT, unbuilt and untested" \
  --homepage "https://normansrule.github.io/microscout/" \
  --add-topic drone,quadcopter,esp32-s3,open-hardware,kicad,brushless,am32,python,simulator,micro-drone

# 4b. GitHub Pages from /docs on main (the interactive design explorer)
gh api -X POST repos/Normansrule/microscout/pages -f "source[branch]=main" -f "source[path]=/docs" \
  || gh api -X PUT repos/Normansrule/microscout/pages -f "source[branch]=main" -f "source[path]=/docs"

# 4c. Tags for the reviewed states
git fetch --tags origin
git tag g1-rev-a 01358cd                                                            # superseded rev A (G1)
git tag -a g1-rev-b-approved 1ea3e59 -m "G1 rev B as approved by the owner 2026-10-07"
git tag -a g2-draft -m "G2 schematics draft for owner review" origin/main
git push origin g1-rev-a g1-rev-b-approved g2-draft
```

To check that it worked:

```bash
gh repo view Normansrule/microscout --json visibility,homepageUrl --jq '.visibility + "  " + .homepageUrl'
gh api repos/Normansrule/microscout/pages --jq '.html_url + "  status: " + (.status // "building")'
gh run list --repo Normansrule/microscout --limit 3          # CI: simulator tests, budgets, schematic checks
git ls-remote --tags origin
```

The explorer goes live at https://normansrule.github.io/microscout/ a minute or two after 4b.

**Optional social preview.** On github.com go to *Settings → General → Social preview → Edit → Upload an image* and pick `docs/figures/social-preview.png` (1280 × 640). GitHub has no API for this setting.

## 5. Try the Python SDK and simulator (no hardware needed)

```bash
cd ~/microscout/software/microscout_sdk
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                          # 23 simulator tests
microscout demo --plot demo.png    # take off, square, turn, back flip, side flip, land
deactivate
```

### 5b. The Flight Lab (browser simulator)

The lab is online at <https://normansrule.github.io/microscout/lab/>. To run your own copy, for example after editing `docs/lab/js/*.js`:

```bash
cd ~/microscout/docs && python3 -m http.server 8000     # then open http://localhost:8000/lab/ ; Ctrl+C to stop
```

To run its tests, or to retrain the bundled policies (Node 18 or later):

```bash
sudo apt install -y nodejs
cd ~/microscout
node --test docs/lab/test/lab.test.mjs                  # 10 simulation regression tests (also run in CI)
node docs/lab/test/compare.mjs 20                       # every autopilot on 20 layouts -> docs/data/lab_controllers.json
node docs/lab/train.mjs '{"course":"window","trainer":"cem","arch":"linear","init":"pd","population":32,"episodes":2,"randomize":true}' 140 docs/lab/policies/window-cem-linear.json
```

## 6. Regenerate the schematics and run KiCad's own ERC (G2 checklist)

KiCad 7 from Ubuntu's archive is enough to regenerate the schematics. KiCad's command-line ERC needs **KiCad 8 or later**, so this step installs KiCad 9 from the official PPA:

```bash
sudo add-apt-repository -y ppa:kicad/kicad-9.0-releases
sudo apt update && sudo apt install -y kicad
kicad-cli version                                  # expect 9.x

cd ~/microscout
python3 tools/sch/build_all.py                     # regenerates every board; non-zero exit on any check failure
python3 tools/sch/costed_bom.py && python3 tools/sch/summaries.py

mkdir -p review/G2/kicad-erc
for sch in hardware/drone-pcb/microscout-fc.kicad_sch hardware/esc-pcb/microscout-esc.kicad_sch \
           hardware/tof-satellites/side/microscout-tof-side.kicad_sch hardware/tof-satellites/front/microscout-tof-front.kicad_sch; do
  kicad-cli sch erc --severity-all --output "review/G2/kicad-erc/$(basename "$sch" .kicad_sch).rpt" "$sch"
done
grep -h "ERC messages\|Errors\|Warnings" review/G2/kicad-erc/*.rpt
```

To browse a schematic in KiCad, open the project file (for example `hardware/drone-pcb/microscout-fc.kicad_pro`). KiCad 9 will ask to upgrade the files when you save. That is fine, but the source of truth is the Python in `hardware/*/design/` until G3.

## 7. Rebuild the PCB layouts, DRC reports and renders (G3 checklist)

The board scripts use **KiCad 7's Python module** (`pcbnew`), as the agent did. KiCad 9's module has a different API, so install KiCad 7 next to it or use a KiCad 7 container if `python3 -c "import pcbnew; print(pcbnew.Version())"` does not print 7.x. Autorouting uses **Freerouting 1.9.0** (Java 21) through a virtual display.

```bash
sudo apt install -y openjdk-21-jre-headless xvfb imagemagick build-essential
mkdir -p ~/tools-ext && curl -L -o ~/tools-ext/fr.jar \
  https://github.com/freerouting/freerouting/releases/download/v1.9.0/freerouting-1.9.0.jar
export FREEROUTING_JAR=~/tools-ext/fr.jar        # tools/pcb/layout.py reads this
pip install --break-system-packages shapely numpy cairosvg

cd ~/microscout
python3 tools/pcb/footprints.py                   # project footprints (hardware/libraries/microscout.pretty)
python3 -u tools/pcb/tof.py                       # both ToF satellites, a few minutes
python3 -u tools/pcb/fc.py --passes=30            # flight controller, 1-2 hours (Freerouting + finisher)
python3 -u tools/pcb/esc.py --passes=25           # ESC, 1-2 hours
python3 tools/pcb/currents.py && python3 tools/pcb/copper.py && python3 tools/pcb/g3_report.py
for b in hardware/drone-pcb/microscout-fc hardware/esc-pcb/microscout-esc \
         hardware/tof-satellites/side/microscout-tof-side hardware/tof-satellites/front/microscout-tof-front; do
  python3 tools/pcb/export.py $b.kicad_pcb review/G3/$(basename $b | sed 's/microscout-//')
done
```

Autorouting is not deterministic, so a re-run gives different copper. To check a board in **KiCad 9's own DRC**, open the `.kicad_pcb` file, let KiCad upgrade it, then run *Inspect, Design Rules Checker* with *Refill all zones* ticked, or from a terminal:

```bash
kicad-cli pcb drc --severity-all --refill-zones -o review/G3/kicad9-drc-fc.rpt hardware/drone-pcb/microscout-fc.kicad_pcb
```

The 3D renders need the step 9 tools plus KiCad's 3D models: `python tools/pcb/render3d.py <board>.kicad_pcb review/G3/<name>` (set `KICAD_3D` to your `3dmodels` folder).

## 8. Send your own changes or review notes back to GitHub

```bash
cd ~/microscout
git pull --rebase origin main            # always start from the latest version
git checkout -b review-g2                # optional: a branch for your notes
# ...edit files, e.g. tick boxes in VERIFY.md or add review/G2/kicad-erc/*.rpt...
git add -A
git commit -m "G2 review: KiCad 9 ERC reports and checklist"
git push -u origin review-g2             # or: git push origin main
gh pr create --fill                      # only if you used a branch
```

Then tell the agent `APPROVED G3`, or send corrections and answers to the open questions in `review/G3/README.md`.

## 9. Optional: rebuild every figure, render and the explorer

This needs CadQuery, Playwright and Node; see `tools/viz/README.md` for the full order.

```bash
cd ~/microscout
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/viz/requirements.txt cadquery playwright && python3 -m playwright install chromium
sudo apt install -y nodejs npm graphviz poppler-utils ffmpeg
(cd tools/viz/render3d && npm install)
python3 mechanical/concept/microscout_concept.py && python3 review/G1/calc/budgets.py && python3 tools/viz/export_sim.py
(cd tools/viz && python3 figures.py && python3 animations.py && python3 build_site.py)
python3 tools/viz/render3d/render.py && python3 tools/viz/render3d/render.py --banner && python3 tools/viz/banner.py
# Flight Lab charts and recordings
node docs/lab/test/compare.mjs 20 && node docs/lab/test/curves.mjs 80 3
(cd tools/viz && python3 lab_charts.py)
python3 tools/viz/lab_capture.py                 # several minutes: drives the lab frame by frame
```
