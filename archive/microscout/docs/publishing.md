> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2 (owner action; D-002, OQ-7)

# Making the repository public and turning on the design explorer

The full step-by-step guide for a fresh Ubuntu terminal is in **[setup-ubuntu.md](setup-ubuntu.md)**: installing the tools, logging in, pulling the latest commits, publishing, adding tags, running the SDK, KiCad ERC and sending changes back.

The agent can push commits but cannot change repository settings or push tags. These are the owner's commands, assuming `gh auth status` shows `Normansrule`:

```bash
gh repo edit Normansrule/microscout \
  --visibility public --accept-visibility-change-consequences \
  --description "Open-source palm-sized ESP32-S3 brushless camera drone - DRAFT, unbuilt and untested" \
  --homepage "https://normansrule.github.io/microscout/" \
  --add-topic drone,quadcopter,esp32-s3,open-hardware,kicad,brushless,am32,python,simulator,micro-drone

gh api -X POST repos/Normansrule/microscout/pages -f "source[branch]=main" -f "source[path]=/docs" \
  || gh api -X PUT repos/Normansrule/microscout/pages -f "source[branch]=main" -f "source[path]=/docs"

git fetch --tags origin
git tag g1-rev-a 01358cd
git tag -a g1-rev-b-approved 1ea3e59 -m "G1 rev B as approved by the owner 2026-10-07"
git tag -a g2-draft -m "G2 schematics draft for owner review" origin/main
git push origin g1-rev-a g1-rev-b-approved g2-draft
```

The explorer goes live at https://normansrule.github.io/microscout/ a minute or two later. Making the repo public also publishes every file and the full git history, including commit author names and email addresses.
