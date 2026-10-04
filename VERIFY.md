> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (and at every later gate)

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

## G1 - Architecture and parts (package: `review/G1/`) - AWAITING REVIEW

Architecture
- [ ] Block diagram matches intent: motors on battery via Q1/Q2, electronics on BQ24074 OUT, 3.3 V buck-boost, 5 V boost, 1.8 V and camera LDOs (`review/G1/block-diagram.svg`).
- [ ] Requirements table and derived requirements DR-01…DR-05 accepted (`review/G1/requirements.md`).
- [ ] Remote G1 deferral to M5 accepted (D-024).

Parts (`bom/drone-bom-g1.csv`, `review/G1/parts-selection.md`)
- [ ] Each datasheet link opens the intended manufacturer document.
- [ ] Each LCSC number matches the intended part and package (spot-check at least U1, U2, U3, U12, U19, Q1).
- [ ] Stock and prices re-checked (they were recorded 2026-10-04).
- [ ] Module choice ESP32-S3-WROOM-1-N8R2 (quad PSRAM) accepted (D-003).
- [ ] IMU BMI270 instead of ICM-42688-P accepted (D-006).
- [ ] TPS63802 efficiency (~88-92% graph reading) accepted vs the 90% target, or switch to TPS63020 (D-014).

Budgets (`review/G1/budgets.md`, regenerate with `calc/budgets.py`)
- [ ] Weight inputs and ranges are reasonable; nominal 71.6 g, range 58-94 g.
- [ ] Thrust-to-weight scenarios reviewed; thrust source quality understood (secondhand, 60 mm props).
- [ ] 3.3 V and 5 V rail tables checked; ESTIMATE rows (ESP32 average, ELRS current, LED average) accepted as placeholders for G6 measurement.
- [ ] Hover current / flight time method accepted (4-5 g/W from a generic 8520 test).
- [ ] Charger R_ISET 1.78 kOhm, shunt 5 mOhm, MOSFET dissipation and series-drop calculations checked.
- [ ] Prop clearance calculation and the 55 mm / 95 mm choice accepted.

Pin table (`review/G1/pin-allocation.md`, `.csv`, `pin-check-report.txt`)
- [ ] Every GPIO ↔ module pin number checked against the purchased module's datasheet revision.
- [ ] Strapping pins GPIO0/3/45/46: connected circuits give the required boot levels.
- [ ] GPIO3 eFuse (JTAG strap) and module pins 28-30 "decided by eFuse" note confirmed harmless.
- [ ] Motor gates on GPIO2/21/38/47 with pull-downs accepted.
- [ ] Expander maps and the I2C address plan (ToF reassignment avoiding 0x30) accepted.

Licences (`review/G1/license-plan.md`)
- [ ] Licence per directory accepted; third-party items to audit noted.

Open questions (`review/G1/README.md`) - reply with a decision for each
- [ ] OQ-1 toolchain  - [ ] OQ-2 battery connector  - [ ] OQ-3 thrust margin  - [ ] OQ-4 optical flow  - [ ] OQ-5 cost
- [ ] OQ-6 barometer stock  - [ ] OQ-7 GitHub repo  - [ ] OQ-8 ESP-IDF version  - [ ] OQ-9 5 V rail

## G2 - Schematic (package: `review/G2/`) - NOT STARTED
- [ ] PDF of all sheets (`kicad-cli sch export pdf`) reviewed
- [ ] ERC report clean, every waiver justified
- [ ] Net list reviewed
- [ ] Each power and charger circuit matches its datasheet reference design (comparison table)
- [ ] Pull-up and strapping summary checked
- [ ] ESD and protection summary checked

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
