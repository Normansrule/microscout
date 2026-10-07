> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (owner action; D-002, OQ-7)

# Making the repository public and turning on the design explorer

The agent's session can push commits but cannot change repository settings, so these two steps are for the owner. Run them from any terminal where `gh auth status` shows you logged in as `Normansrule`.

```bash
# 1. Make the repository public (and set its description and homepage)
gh repo edit Normansrule/microscout \
  --visibility public --accept-visibility-change-consequences \
  --description "Open-source palm-sized ESP32-S3 brushless camera drone - DRAFT, unbuilt and untested" \
  --homepage "https://normansrule.github.io/microscout/"

# 2. Serve docs/ with GitHub Pages (the interactive design explorer)
gh api -X POST repos/Normansrule/microscout/pages \
  -f "source[branch]=main" -f "source[path]=/docs"
```

After a minute or two the explorer is at https://normansrule.github.io/microscout/. If step 2 says Pages already exists, it is already on. Check with `gh repo view Normansrule/microscout --json visibility` and `gh api repos/Normansrule/microscout/pages`.

Things that become public with the repo: every file and the full git history, including commit author names and email addresses.

## Rev A tag

The G1 review files refer to the superseded rev A design at git tag `g1-rev-a`. The agent's session could not push tags, so create it once from a clone:

```bash
git fetch origin && git tag g1-rev-a 01358cd && git push origin g1-rev-a
```
