> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2 (owner actions; D-002, OQ-7)

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

## 7. Send your own changes or review notes back to GitHub

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

Then tell the agent `APPROVED G2`, or send corrections and answers to OQ-13 to OQ-18 (`review/G2/README.md`).

## 8. Optional: rebuild every figure, render and the explorer

This needs CadQuery, Playwright and Node; see `tools/viz/README.md` for the full order.

```bash
cd ~/microscout
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/viz/requirements.txt cadquery playwright && python3 -m playwright install chromium
sudo apt install -y nodejs npm graphviz poppler-utils
(cd tools/viz/render3d && npm install)
python3 mechanical/concept/microscout_concept.py && python3 review/G1/calc/budgets.py && python3 tools/viz/export_sim.py
(cd tools/viz && python3 figures.py && python3 animations.py && python3 build_site.py)
python3 tools/viz/render3d/render.py && python3 tools/viz/render3d/render.py --banner && python3 tools/viz/banner.py
```
