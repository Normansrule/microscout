> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# Gate G1 review package - Architecture and parts (rev B)

Rev B answers the owner's 2026-10-07 direction: **fast, agile enough to flip, durable in crashes, and easy to program and fly.** It replaces the brushed 1S rev A (kept at git tag `g1-rev-a`; changes in `REVISIONS.md`). The agent has **stopped at G1 again**: the schematic (M2) waits for `APPROVED G1` or corrections. Nothing here is built or tested; every number is a datasheet value, vendor claim, estimate or assumption, and is labelled.

## Contents

| File | What it is | Review time |
|---|---|---|
| `REVISIONS.md` | What changed from rev A and why | 3 min |
| `requirements.md` | Requirements incl. new R-20 agility, R-21 speed, R-22 durability, R-23/24 ease of use | 5 min |
| `block-diagram.svg` (source `.dot`) | Rev B architecture: 2S power, FC board, separate AM32 ESC board | 5 min |
| `parts-selection.md` + `../../bom/drone-bom-g1.csv` | Parts, LCSC numbers, prices/stock seen 2026-10-04..07 | 15 min |
| `budgets.md` (from `calc/budgets.py`) | Weight (uses CAD frame mass), T/W, agility, power, hover time, peak current, crash energy, cost | 15 min |
| `pin-allocation.md` / `.csv` / `pin-check-report.txt` | Pin table (DShot outputs, ICM-42688-P); check: 0 errors, 8 warnings | 10 min |
| `../../mechanical/concept/` + `../../docs/figures/renders/` | Concept CAD (frame, canopy, envelopes), STEP/STL/GLB, renders, report | 10 min |
| `../../software/microscout_sdk/` | SDK + simulator, reference flight controller, 23 tests, 5 examples | 10 min |
| `../../docs/guide/fly.md`, `../../docs/guide/program.md` | How to fly it and how to program it | 5 min |
| `../../docs/decisions.md` | D-028 to D-043 (rev B); superseded rev A rows are marked | 10 min |
| [Design explorer](https://normansrule.github.io/microscout/) | Interactive charts, 3D viewer, simulated flights (once Pages is on) | 5 min |

Regenerate: `python3 review/G1/calc/budgets.py && python3 review/G1/calc/check_pins.py > review/G1/pin-check-report.txt`; CAD: `python3 mechanical/concept/microscout_concept.py`; visuals: `tools/viz/README.md`; SDK tests: `cd software/microscout_sdk && pip install -e .[dev] && pytest`.

## Headline numbers (rev B, all estimates)

| | Rev A | Rev B |
|---|---|---|
| Takeoff weight | 71.6 g | **82.4 g** (72-98 g) |
| Thrust-to-weight | 1.6-2.0 | **4.1-5.9** |
| Max angular acceleration (pitch) | - | **980-1,410 rad/s²** |
| Hover time | 5.1-6.2 min | **5.0-6.8 min** |
| Peak battery current | 8-11 A | **~38 A** (firmware-limited to 30 A) |
| Priced parts per drone | $69 | **$137** |
| Simulated back flip | - | ~0.8 s, no height lost (estimated parameters) |

## Open questions for the owner

| # | Question | Agent recommendation |
|---|---|---|
| OQ-1 | Toolchain: KiCad 9 PPA blocked here (KiCad 7.0.11 available); ESP-IDF/Freerouting need repo access. | Same as rev A. |
| OQ-2 | **Battery and connector:** 2S 550 mAh (29 g) vs 450 mAh (26 g); XT30 is rated 30 A peak vs ~38 A full-throttle estimate. | 550 mAh + XT30 with the 30 A firmware limit; revisit after measuring real current at G6. |
| OQ-3 | **Frame fabrication:** MJF PA11 (service, e.g. JLC3DP) vs FDM nylon/TPU at home vs injection-moulded PP later. | MJF PA11 for the first frames; print the drop-test coupons at G5. |
| OQ-4 | Optical flow: bare PMW3901 needs an LN03-ZSZ lens with no confirmed source. | Unchanged from rev A (Bitcraze Flow deck fallback). |
| OQ-5 | **Cost:** priced parts ~$137 vs ~$75 target (motors alone $60). | Accept a higher target for the performance version, or source motors in bulk. |
| OQ-6 | Barometer stock (BMP390/DPS310/SPL06 out of stock 2026-10-04). | Unchanged. |
| OQ-7 | Repo visibility: still **private** - the agent's session cannot change repo settings or enable Pages. | Run the two commands in [`docs/publishing.md`](../../docs/publishing.md). |
| OQ-8 | **Firmware base:** esp-drone vs esp-fc vs own firmware following the SDK's reference controller (D-037). | Prototype the rate loop + DShot on esp-fc's approach, keep esp-drone's autonomy ideas; decide at M7 start. |
| OQ-9 | **ESC:** design our own AM32 4-in-1 board vs buy a commercial whoop 4-in-1/AIO. | Own board (open, repairable) with a commercial ESC as the bring-up fallback; gate-driver stock decides. |
| OQ-10 | **Reverse polarity:** the ground-return FETs in the first rev B draft do not work (the balance lead bypasses them). Keyed XT30 + JST-XH only, or add a high-side ideal-diode controller with back-to-back N-FETs (~2-3 W at 30 A, extra area and cost). | Keyed connectors only, as commercial whoops do; buy packs with factory-fitted XT30. Residual risk stated in R-13: no fuse, so unplug after every flight. |
| OQ-11 | **Weight:** 82.4 g vs < 80 g. | Try the 450 mAh pack and thinner duct walls before cutting sensors. |
| OQ-12 | **Brief changes:** rev B changes R-03 (PCB-as-frame), R-05 (1S JST-PH), R-14 (brushed) and the firmware base. R-12 (3.3 V regulator ≥ 90 % efficient) is likely **not met** by the TPS62162 from 8 V at these loads (estimate 85 %). | Approve the changes or say which to keep; accept ~85 % for R-12 or ask for a different regulator at G2. |

## Section 1 items the agent cannot confirm (relevant to G1)

Prices and stock move daily; ESP32-S3 pin conflicts must be checked against the purchased module; power and analog values are first-pass until G2; weights, thrust and currents are vendor data or estimates; the simulator uses estimated parameters (it shows the control design works in principle, not that the drone will fly); whether the chosen firmware runs acro + streaming on ESP32-S3 is UNCONFIRMED; regulatory and licence notes are draft guidance.

The G1 checklist is in `VERIFY.md`.
