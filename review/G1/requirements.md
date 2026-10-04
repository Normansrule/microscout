> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1

# MicroScout requirements (drone)

Derived from the project brief (sections 3, 4, 7, 13). "Verify at" = the gate where evidence for the requirement is reviewed; physical requirements can only be confirmed by the human on real hardware.

| ID | Requirement | Source | Current status at G1 | Verify at |
|---|---|---|---|---|
| R-01 | Quadcopter, ~90-100 mm motor-to-motor | brief 3 | 95 mm chosen (D-019) | G3, G5 |
| R-02 | Takeoff weight < 80 g (well under 250 g) | brief 3, 13 | Estimate 71.6 g nominal, 58-94 g range (budgets 1) - **at risk** | G5 (estimate), human weighs after build |
| R-03 | Main PCB is the frame (Crazyflie-style), 4-layer, ~1 mm | brief 3, M3 | Planned | G3 |
| R-04 | 3D-printed canopy with integrated prop guards | brief 3, 6 | Planned (CadQuery) | G5 |
| R-05 | 1S LiPo 600-800 mAh, JST-PH 2.0 | brief 3 | 660 mAh pack selected; **JST-PH current rating conflict** (OQ-2) | G1 decision |
| R-06 | USB-C charging on the drone, power-path charger (not TP4056) | brief 3, 4 | BQ24074, ~500 mA | G2, G6 bench |
| R-07 | Camera with Wi-Fi video streaming (MJPEG) | brief 3, 7 | OV2640 + ESP32-S3; simultaneous streaming + flight control **UNCONFIRMED** | G6 bench |
| R-08 | Control by RC (ELRS/CRSF), Wi-Fi UDP, BLE, Python SDK | brief 3, 7, 8 | UART1 for CRSF; Wi-Fi/BLE on module | G6, M8 |
| R-09 | External-control mode accepting attitude/rate setpoints at 50-100 Hz; runtime parameters; telemetry logging | brief 7 | Firmware milestone | G6/G7 |
| R-10 | Sensors: IMU, barometer, magnetometer, downward ToF, optical flow, forward multizone ToF, side + rear ToF, battery V/I | brief 4 | All allocated; optical-flow lens sourcing open (OQ-4); barometer stock open (OQ-6) | G2 |
| R-11 | Parts cost < ~$75/drone at 5 units, excluding remote | brief 3 | **Likely exceeded** - priced lines alone ~$69 (budgets 5, OQ-5) | G1 decision, G8 totals |
| R-12 | 3.3 V regulator ≥ 90% efficient at expected load | brief 4 | TPS63802 ~88-92% (graph reading) - **borderline** (D-014) | G2 |
| R-13 | UVLO, over-current and reverse-polarity protection, soft power switch, USB ESD | brief 4 | 15 A fuse, reverse P-FET first in the battery path, LTC2954, USBLC6; hardware UVLO supervisor (U23) chosen at G2 | G2, G6 bench |
| R-14 | Motors: 4x brushed coreless 8520, 55-65 mm props, low-side N-MOSFETs with flyback diodes and gate resistors | brief 4 | 8520 + 55 mm; AO3400A + B5819W | G2, G3 |
| R-15 | Extras: 4x WS2812-2020, buzzer, boot/reset buttons, labelled test pads on every rail and bus, SWD/UART debug header | brief 4 | Allocated; LEDs need a 5 V rail (D-015). ESP32-S3 has no SWD: debug = USB Serial/JTAG (GPIO19/20) + UART0 pads | G2, G3 |
| R-16 | Pre-certified radio module | brief 4, 13 | ESP32-S3-WROOM-1 module (certification status per region: human to confirm) | G8 |
| R-17 | Safety functions: arming checks, kill switch, link-loss failsafe (hover then land), low-battery auto-land, altitude ceiling, obstacle stop - each with a props-off bench test | brief 7 | Firmware milestone; hardware hooks: PGOOD arm-inhibit, KILL line, INA226 + VBAT ADC, ToF array | G6 |
| R-18 | Thrust-to-weight adequate for controlled flight | implied by brief 3 | **T/W ~1.6-2.0 at nominal weight** with available (secondhand) thrust data (budgets 2, OQ-3) | G1 decision, G7 |
| R-19 | Licenses: hardware CERN-OHL-S-2.0, firmware GPL-3.0, software MIT, docs CC-BY-SA-4.0 | brief 9 | License files in place (license-plan.md) | G8 |

Derived requirements added at G1 (from findings, not in the brief):

| ID | Requirement | Reason |
|---|---|---|
| DR-01 | Motors must not be powered through the charger's power-path output | BQ24074 supplement-mode short-circuit trip (D-012) |
| DR-02 | Firmware must not arm while USB power is present | Motor current during charging disturbs charge termination; bench safety |
| DR-03 | Motor gates held low by hardware during reset/boot | Props-on safety; GPIO states undefined during reset |
| DR-04 | All ToF sensors held in reset by hardware until firmware addresses them | Five devices share default address 0x29 |
| DR-05 | 5 V rail for ELRS receiver and LEDs | Both parts specify ≥ 3.7 V / 5 V supply (D-015) |
