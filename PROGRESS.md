> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# Progress

| Milestone | Gate | State | Notes |
|---|---|---|---|
| Setup (brief sections 10-11) | - | Partly done | System packages + Python environment installed; KiCad 9, ESP-IDF, Freerouting deferred (D-001, OQ-1). Repo at github.com/Normansrule/microscout, **still private** - owner runs `docs/publishing.md` (D-002). |
| M1 Requirements, block diagram, parts, budgets, pin table | G1 | **Rev B drafted - awaiting `APPROVED G1`** | Package in `review/G1/`; rev A at tag `g1-rev-a`. 12 open questions. |
| M2 Drone schematic | G2 | Not started | Blocked on G1 approval and OQ-1. |
| M3 Drone PCB | G3 | Not started | |
| M4 Fab outputs | G4 | Not started | |
| M5 Remote PCB (G1 outline → G2-G4) | G2-G4 | Not started | Remote G1 deferred (D-024). |
| M6 Mechanical | G5 | Concept only (D-039) | `mechanical/concept/`: parametric frame + canopy, renders. Real design at M6. |
| M7 Firmware + bench bring-up plan | G6 | Not started | OQ-8. |
| M8 SDK, simulator, notebooks | - | Started early (D-038) | `software/microscout_sdk`: SDK, simulator, reference controller, 23 tests, 5 examples. Notebooks and BLE/UDP transport to come. |
| M9 CI | - | Started (CI checks, D-043) | `.github/workflows/checks.yml`: SDK tests, budget regeneration diff, pin check. |
| M10 First-flight and tuning docs | G7 | Not started | |
| M11 Docs, BOM totals, licence audit | G8 | Not started | |

## Log

- 2026-10-04 - Scaffolded repository; drafted M1 / G1 package; stopped at G1.
- 2026-10-05 - Owner pushed the repo to GitHub (Normansrule/microscout). Added generated figures, animations and a GitHub Pages design explorer for the G1 data (D-027); owner asked for the repo to be public; the agent's session cannot change repo settings, so it is still private (D-002, `docs/publishing.md`). Still stopped at G1.
- 2026-10-07 - Owner direction: high performance, flips, crash durability, easy to program and fly. G1 revised to rev B (2S brushless, AM32 ESC board, ducted PA11 frame); concept CAD + 3D renders; Python SDK + simulator with flips; explorer gains a 3D viewer and simulated flights; flying and programming guides. Still stopped at G1. Repo still private (settings change needs the owner).
