> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# MicroScout requirements (drone) - rev B

Rev B adds the owner's 2026-10-07 direction: **high performance (speed, controls, flips) and robust enough not to break on impact**, plus **easy to program and to fly**. Requirements changed by that direction are marked **(rev B)**. Rev A is preserved at git tag `g1-rev-a`. "Verify at" is the gate where evidence is reviewed; physical requirements can only be confirmed by the human on real hardware.

| ID | Requirement | Source | Status at G1 rev B | Verify at |
|---|---|---|---|---|
| R-01 | Quadcopter, ~90-100 mm motor-to-motor | brief 3 | 95 mm, ducted (overall ~126 mm across the ducts) | G3, G5 |
| R-02 | Takeoff weight < 80 g (well under 250 g) | brief 3, 13 | Estimate **82.4 g** nominal, 72-98 g range - **over target** (budgets 1, OQ-11) | G5 estimate, human weighs |
| R-03 (rev B) | ~~Main PCB doubles as the frame~~ → one-piece ducted frame carries all crash loads; boards are soft-mounted inside it | brief 3 + owner (durability) | Concept CAD in `mechanical/concept/` (D-030) | G5 |
| R-04 | Printed canopy with integrated prop guards | brief 3, 6 | Ducts are the prop guards; TPU canopy (D-031) | G5 |
| R-05 (rev B) | ~~1S, JST-PH 2.0~~ → 2S LiHV 450-550 mAh, XT30, with balance lead | brief 3 + owner (performance) | GNB 2S 550 selected; XT30 peak rating exceeded at full throttle (OQ-2) | G1 decision |
| R-06 (rev B) | USB-C charging on the drone | brief 3, 4 | 2S boost charger with balancing, BQ25887 (D-033) | G2, G6 bench |
| R-07 | Camera with Wi-Fi video streaming (MJPEG) | brief 3, 7 | Unchanged; simultaneous streaming + 2-8 kHz control loop **UNCONFIRMED** | G6 bench |
| R-08 | Control by RC (ELRS/CRSF), Wi-Fi UDP, BLE, Python SDK | brief 3, 7, 8 | SDK drafted with a simulator back end (`software/microscout_sdk`) | G6, M8 |
| R-09 | External control at 50-100 Hz (attitude/rate/velocity), runtime parameters, full telemetry | brief 7 | Implemented in the simulator; firmware at M7 | G6/G7 |
| R-10 | Sensors: IMU, baro, mag, down ToF, flow, forward multizone ToF, side + rear ToF, battery V/I | brief 4 | All kept; IMU → ICM-42688-P (D-032) | G2 |
| R-11 | Parts cost < ~$75/drone at 5 units | brief 3 | **Exceeded** - priced lines ~$137 (budgets 6, OQ-5) | G1 decision, G8 |
| R-12 | 3.3 V regulator ≥ 90 % efficient | brief 4 | TPS62162 buck from 2S; efficiency curve not read yet (ESTIMATE 85 %) - **likely not met** (D-034, OQ-12) | G2 |
| R-13 | UVLO, over-current, reverse polarity, soft power switch, USB ESD | brief 4 | **Partly changed:** soft switch controls the logic rails and ESC driver supply (D-036); firmware/ESC current limit replaces the fuse; reverse polarity by keyed connectors only (D-035). **Residual risk:** no fuse and no reverse FET - a hard short or reversed pigtail is stopped only by unplugging; unplug after every flight (OQ-10) | G2, G6 |
| R-14 (rev B) | ~~Brushed 8520~~ → brushless 1103-class motors, 2-inch props, onboard 4-in-1 ESC | owner (performance) | EX1103 11000KV + AM32 ESC board (D-028, D-029) | G2, G3 |
| R-15 | 4x WS2812-2020, buzzer, boot/reset, test pads, debug (USB-JTAG + UART0; ESP32-S3 has no SWD) | brief 4 | Unchanged | G2, G3 |
| R-16 | Pre-certified radio module | brief 4, 13 | ESP32-S3-WROOM-1 | G8 |
| R-17 | Safety: arming checks, kill, link-loss (hover then land), low-battery land, altitude ceiling, obstacle stop - each bench-tested props off | brief 7 | All emulated and unit-tested in the simulator; firmware at M7 | G6 |
| R-18 | Thrust-to-weight adequate | brief 3 | **4.1-5.9** at nominal weight (rev A was 1.6-2.0) | G7 |
| R-19 | Licences: hardware CERN-OHL-S-2.0, firmware GPL-3.0, software MIT, docs CC-BY-SA-4.0 | brief 9 | In place; AM32 (GPL-3.0) flagged for the ESC firmware | G8 |
| **R-20 (rev B)** | **Agility: 360° flips on all four axes; body rates ≥ 1000 °/s; T/W ≥ 4 at takeoff weight** | owner | Budgets 2: 980-1410 rad/s² available; simulator flips in ~0.8 s with no height loss (estimated parameters) | G7 (flight test) |
| **R-21 (rev B)** | **Speed: ≥ 10 m/s level flight (target, measured)** | owner | Simple model upper bound 19-21 m/s (heavy assumptions); real value from G7 logs | G7 |
| **R-22 (rev B)** | **Durability: survive 26 drops from 1.0 m onto a hard floor (faces, edges, corners) and frontal impacts at 3 m/s with no damage beyond replaceable props; boards never in the load path; frame, canopy and props replaceable without soldering** | owner; drop method after IEC 60068-2-31 / MIL-STD-810 (budgets 5) | Design response D-030/D-031; acceptance test written at G5, run by the owner | G5 plan, owner test |
| **R-23 (rev B)** | **Easy to fly: beginner mode (speed control, height hold, obstacle stop), sport (angle) and acro (rates) modes; one-button flips** | owner | Modes and flips work in the simulator | G6/G7 |
| **R-24 (rev B)** | **Easy to program: `pip install` SDK with the same API for simulator and drone; blocking beginner calls (`takeoff/move/flip/land`) and low-level setpoints for control experiments; examples and tests** | owner | Drafted: 19 passing simulator tests, 5 examples | M8, G6 |

Derived requirements:

| ID | Requirement | Reason |
|---|---|---|
| DR-01 | Motors are never powered through the charger | Charger and power stage are separate paths (D-033) |
| DR-02 | Firmware must not arm while USB power is present | Bench safety |
| DR-03 | ESC lines stay idle (no DShot frames) during reset/boot | Props-on safety |
| DR-04 | All ToF sensors held in reset by hardware until addressed | Five devices share 0x29 |
| DR-05 | 5 V rail for the ELRS receiver and LEDs | Both need ≥ 3.7 V / 5 V |
| DR-06 (rev B) | Firmware limits battery current to ≤ 30 A | XT30 peak rating vs 37.7 A full-throttle estimate (budgets 3d) |
| DR-07 (rev B) | Flips only above 1.0 m, and only in a mode the pilot selected | Recovery needs height |
