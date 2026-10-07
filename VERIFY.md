> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 rev B (and at every later gate)

# MicroScout verification checklist

Only the human owner ticks boxes and changes any file's status to VERIFIED. The agent stops at each gate, posts the package in `review/Gx/`, and waits for `APPROVED Gx` or corrections.

## What the agent cannot produce or confirm (brief section 1)

The human must verify each item. The agent restates the relevant items at every gate.

- [ ] Physical testing of any kind: power-up, sensor readings, motor spin, flight, battery charging, thermal behavior, camera streaming, radio range.
- [ ] Real-time part availability and pricing, unless live LCSC/JLCPCB access works in this session. Otherwise all stock and prices are UNCONFIRMED. *(G1 note: LCSC product pages were readable on 2026-10-04 and the values seen are recorded with timestamps; they still change daily.)*
- [ ] Footprint-to-part correctness: the agent can pick library footprints but cannot guarantee they match the exact purchased part's datasheet land pattern, pin 1 orientation, or package variant.
- [ ] Pin assignment conflicts on the ESP32-S3: strapping pins, pins used by octal PSRAM and flash (for example GPIO 33-37 on R8 modules), USB pins, and input-only or boot-sensitive pins. The agent drafts a pin table; the human confirms it against the exact module datasheet.
- [ ] Quality PCB layout: autorouted traces pass DRC but may be electrically poor. The agent cannot verify RF performance, antenna keep-out effectiveness, USB differential pair quality, ground return paths, EMI, IMU vibration and noise, or motor-current heating.
- [ ] Analog and power design correctness: charger, buck/boost, and protection component values must be checked against each IC's datasheet reference design.
- [ ] Fabrication file correctness: Gerber appearance, drill alignment, and especially JLCPCB CPL component rotations, which commonly come out wrong and must be checked in JLCPCB's assembly preview.
- [ ] Availability of manufacturer STEP models: the agent may only link files it has confirmed exist; otherwise it provides datasheet dimensions for a simplified model.
- [ ] Mechanical fit and print quality: tolerances depend on the human's printer and material; weights are estimates until weighed.
- [ ] Firmware behavior on real hardware: it can confirm code compiles, not that drivers, timing, control loops, or failsafes behave correctly. All PID gains are placeholders until tuned.
- [ ] Whether esp-drone supports this exact sensor set and simultaneous camera streaming on ESP32-S3 without modification. Treat as UNCONFIRMED until bench-tested.
- [ ] Regulatory compliance (FAA or local aviation rules, radio rules), battery safety certification, and license compatibility across reused code and CAD files. The agent drafts guidance only.

## G1 rev B - Architecture and parts (package: `review/G1/`) - APPROVED BY THE OWNER 2026-10-07 (D-044)

The owner approved the package and the agent's recommendation for every open question. The boxes below are left for the owner to tick as items are actually checked.

Rev A (brushed, 1S) is superseded; its checklist is in git tag `g1-rev-a`. Only the owner ticks boxes.

Direction and architecture
- [ ] Rev B direction accepted: 2S brushless, separate AM32 ESC board, ducted one-piece frame, soft-mounted boards (D-028 to D-031), including the brief changes listed in OQ-12.
- [ ] Block diagram matches intent: charger and power stage separate, soft switch on logic rails only, DShot to the ESC board (`review/G1/block-diagram.svg`).
- [ ] Requirements R-20 (agility), R-21 (speed), R-22 (durability), R-23/24 (ease of use) and DR-06/07 accepted (`review/G1/requirements.md`).

Parts (`bom/drone-bom-g1.csv`, `review/G1/parts-selection.md`)
- [ ] Datasheet links open the intended documents; LCSC numbers match (spot-check U2 BQ25887, U3, U4, U12 ICM-42688-P, ESC parts, J2 XT30).
- [ ] Prices and stock re-checked (seen 2026-10-04 to 10-07); gate-driver stock (FD6288Q) resolved (OQ-9).
- [ ] EX1103 thrust/current figures accepted as vendor data, or one motor measured.

Budgets (`review/G1/budgets.md`)
- [ ] Weight inputs reasonable; frame mass taken from the CAD concept (11.9 g); nominal 82.4 g (OQ-11).
- [ ] Thrust scenarios (85/100/122 g per motor) and inertia estimate reasonable; agility calculation checked.
- [ ] Rails (TPS62162 1 A margin is tight), hover time method, peak current vs XT30 rating, shunt and crash-energy table checked.
- [ ] No fuse and no reverse-polarity FET accepted, with keyed connectors and "unplug after flight" as the mitigation (D-035, OQ-10); ESC driver-supply switch Q4 concept accepted (D-036).

Pin table (`review/G1/pin-allocation.*`, `pin-check-report.txt`)
- [ ] Every GPIO ↔ module pin checked against the purchased module's datasheet.
- [ ] Strapping pins GPIO0/3/45/46 give the required boot levels; eFuse notes confirmed.
- [ ] DShot outputs on GPIO2/21/38/47 with pull-downs accepted; bidirectional DShot on ESP32-S3 to be proven at G6.
- [ ] GPIO1 spare (VBAT divider removed, D-021); LED data via SPI3 (D-042); U11 P1/P2 now BQ25887 INT and VBUS detect.

Concept CAD and renders (`mechanical/concept/`, `docs/figures/renders/`; D-039)
- [ ] Concept accepted as a direction for G5 (it is not the G5 design); envelopes understood as APPROXIMATE.
- [ ] No board/prop/frame interference in `concept_report.json`; 1 mm prop tip clearance acceptable for a first print.
- [ ] CAD frame mass (11.9 g, used in the weight budget) compared with the hand estimate in `concept_report.json`; motor numbering in the CAD matches D-040.

SDK and simulator (`software/microscout_sdk/`; D-038)
- [ ] `pip install -e ".[dev]" && pytest` passes on the owner's machine; `microscout demo` runs.
- [ ] Reference controller behaviour (modes, flips, safety rules) is what the firmware should implement.
- [ ] Simulator parameters understood as estimates (test checks they match `budgets.py`).

Visuals (`docs/figures/`, explorer, D-027)
- [ ] Charts match `budgets.md`, the BOM and the pin table; renders and animations do not overstate what is known.

Licences (`review/G1/license-plan.md`)
- [ ] Licence per directory accepted; AM32 (GPL-3.0) and three.js (MIT) noted.

Open questions (`review/G1/README.md`) - reply with a decision for each
- [ ] OQ-1 toolchain  - [ ] OQ-2 battery/connector  - [ ] OQ-3 frame fabrication  - [ ] OQ-4 optical flow  - [ ] OQ-5 cost  - [ ] OQ-6 barometer
- [ ] OQ-7 repo public + Pages (commands given)  - [ ] OQ-8 firmware base  - [ ] OQ-9 ESC board  - [ ] OQ-10 reverse polarity  - [ ] OQ-11 weight  - [ ] OQ-12 brief changes

## G2 - Schematic (package: `review/G2/`) - AWAITING REVIEW
- [ ] PDF of all sheets (`kicad-cli sch export pdf`) reviewed: `review/G2/schematics/` (FC, ESC, ToF side, ToF front)
- [ ] ERC: `review/G2/check-*.md` (agent checks: 0 errors, netlists identical) **and KiCad's own ERC run in KiCad 8/9** - every waiver justified
- [ ] Net lists reviewed (`review/G2/netlists/`)
- [ ] Each power and charger circuit matches its datasheet reference design (`review/G2/reference-designs.md`), including every listed deviation
- [ ] Pull-up and strapping summary checked (`review/G2/pullups-straps.md`)
- [ ] ESD and protection summary checked (`review/G2/protection.md`), including the residual risks (no fuse, no reverse protection, no pack thermistor)
- [ ] Power-on matrix understood: battery only, USB only, both (D-046, D-053, D-055)
- [ ] AM32 pin map (`OPENESC_20_F421`) and FD6288Q wiring checked against the AT32F421 datasheet you hold
- [ ] Open questions OQ-13 to OQ-18 answered (`review/G2/README.md`)
- [ ] Costed BOM `bom/drone-bom-g2.csv` reviewed (prices and stock change daily)

## G3 - PCB layout (package: `review/G3/`) - NOT STARTED
- [ ] Layer-by-layer exports and 3D renders (top, bottom, angled) reviewed
- [ ] DRC report clean
- [ ] Stackup accepted
- [ ] IPC-2152 trace-width calculations for motor and battery nets checked
- [ ] Antenna keep-out checked
- [ ] USB differential pair notes checked
- [ ] IMU placement rationale accepted
- [ ] Every autorouted net listed and reviewed

## G4 - Fabrication outputs (package: `review/G4/`) - NOT STARTED
- [ ] Gerbers and drill files inspected in JLCPCB's Gerber viewer
- [ ] JLCPCB BOM and CPL checked
- [ ] Every polarized/asymmetric part rotation checked in JLCPCB's assembly preview (rotation-check list)

## G5 - Mechanical (package: `review/G5/`) - NOT STARTED
- [ ] STEP, STL, 3MF and renders reviewed
- [ ] Clearance report against the PCB STEP checked
- [ ] Sensor field-of-view clearance checked
- [ ] Estimated weights reviewed
- [ ] Fit coupons printed and checked on the owner's printer

## G6 - Firmware build and bench bring-up (package: `review/G6/`) - NOT STARTED
- [ ] Firmware compiles in CI
- [ ] Bench procedure run with PROPS OFF: power rails, each sensor, motor direction, radio links, failsafes, charging - results reported back

## G7 - First-flight plan (package: `review/G7/`) - NOT STARTED
- [ ] Tethered or netted first-flight checklist reviewed
- [ ] PID tuning procedure and logging plan reviewed
- [ ] Gains revised only from owner-provided logs

## G8 - Release (package: `review/G8/`) - NOT STARTED
- [ ] Documentation review
- [ ] BOM totals
- [ ] Licence audit
- [ ] Known-limitations list
