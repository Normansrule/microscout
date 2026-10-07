> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2

# Power, charger and interface circuits compared with their datasheet reference designs

Each row compares the schematic with what the manufacturer's datasheet or evaluation-module guide (EVM) recommends. The datasheets were read on 2026-10-07; links and limits are in `sources.md`.

- **Match** means the same value or topology.
- **Deviation** means the agent chose differently and says why.
- **UNCONFIRMED** means the reference value could not be read; it may have been in a figure or a section that didn't extract.

Refs are flight-controller (FC) designators unless marked ESC (electronic speed controller) or satellite. Rows changed after the independent G2 review say "(review)".

## BQ25887 2S boost charger with cell balancing (U2)

Sources: datasheet SLUSD89 (pin table §6, §7, §8.3), EVM guide SLUUC12.

| Item | Reference | Schematic | Status |
|---|---|---|---|
| VBUS input capacitor | ≥ 1 µF at the pin (§6 pin 23) | C4 1 µF 25 V | Match |
| PMID capacitor | 10 µF typ.; VBUS + PMID ≥ 10 µF after derating (§6) | C5 10 µF 25 V 0805 (plus C4) | Match. X5R at 5 V keeps ~70 % of nominal; check derating at G3. |
| Inductor | 1 µH (§7.7 note; EVM fits a 1 µH, 11 A part) | L1 1 µH, saturation current (Isat) 5.6 A, DCR 35 mΩ (FTC252012S1R0) | Match on value. Peak inductor current at 0.5 A input is about 1 A, so there is margin. |
| BTST capacitor | 47 nF (§6 pin 12; EVM C9) | C6 47 nF 25 V | Match |
| REGN capacitor | 4.7 µF (§6 pin 11) | C7 4.7 µF 16 V | Match |
| BAT capacitor | ≥ 10 µF after derating | C10 10 µF 25 V | Match. At 8.4 V, X5R derating may leave about 6 µF, so a second capacitor may be needed (G3 check). |
| SNS capacitor | 44 µF ceramic (§6 pins 15/16) | C8 + C9, 2 × 22 µF 25 V | Match on nominal value. The same derating concern applies. |
| MID | 300 Ω series to the cell midpoint (§6 pin 9) | R8 300 Ω to BAL_MID | Match |
| CBSET | R_CBSET ≈ 9.5 Ω gives 400 mA balance current (§8.3.4.3) | R9 150 Ω 1206 | **Deviation.** 9.5 Ω would dissipate about 1.7 W. 150 Ω gives about 29 mA and 0.13 W: slow balancing but safe on a small board. |
| TS | NTC (negative temperature coefficient) thermistor divider (§8.3.4.5) | R5 5.23 k REGN→TS, R6 30.1 k TS→GND, R7 10 k TS→GND (no thermistor) | **Deviation**, copying the EVM's no-thermistor jumper (JP7) setting. TS sits at 58.9 % of REGN, inside the normal band. The pack has no thermistor, so the charger can't sense pack temperature (residual risk, `protection.md`). |
| ILIM | I = 1110 A·Ω / R (§8.3.7) | R4 2.2 k → 0.50 A | Match. Sized for any USB port. |
| PSEL | High = 500 mA, low = 3 A | R3 10 k to REGN (high) | Match, chosen for any-port safety. |
| CD | Low = charge enabled; internal 900 k pull-down | Tied to GND | Match. Firmware can still stop charging over I²C. |
| /PG, STAT, /INT, SDA, SCL | 10 k pull-ups (§6) | /PG → R11 10 k to 3V3; STAT → red LED + 1 k from REGN; /INT → R12 10 k to 3V3; I²C 2.2 k to 3V3 | Match, except STAT, which drives an LED so charging shows while the drone is off. |
| Exposed pad | Not stated in the extracted text | EP (pad 25) → GND, via a project symbol that includes the pad | Assumed GND as on other TI charger QFNs; confirm against the layout section (UNCONFIRMED). |

## TPS62162 3.3 V buck (U3 on the FC, U1 on the ESC)

Source: TI datasheet (§6, Fig. 35, §9.2.2).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| Output | Fixed 3.3 V version: FB to AGND, VOS to the output capacitor | FB → GND, VOS → +3V3 | Match |
| Inductor | 2.2 µH | L2 (ESC L1) 2.2 µH, Isat 3.8 A | Match |
| C_IN / C_OUT | 10 µF / 22 µF | 10 µF 25 V / 22 µF 25 V | Match |
| PG | Open drain, pull-up to < 7 V | 100 k to 3V3, test point (FC); left open on the ESC | Match |
| EN | High = on; internal pull-down; maximum VIN + 0.3 V | FC: PWR_EN (pull-up to VLOGIC = this regulator's VIN). ESC: tied to VIN. | Match |
| Load | 1 A rated | FC 3V3 peak ≈ 0.84 A once the ESC MCUs moved off (D-048, budgets 3a) | Margin 1.19×. Efficiency at 8 V not read (UNCONFIRMED; R-12 accepted at ~85 %). |

## TPS62133 5 V buck (U4)

Source: TI datasheet (Table 6-1, Table 9-1).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| Output | Fixed 5.0 V: FB to AGND; DEF low = nominal | FB → GND, DEF → GND | Match |
| Inductor | 2.2 µH (XFL4020-222) | L3 2.2 µH, Isat 3.8 A, 2.5 × 2 mm | Match on value. Smaller part; load ≈ 0.5 A peak. |
| C_IN | 10 µF 25 V + 0.1 µF at AVIN | C17 10 µF 25 V + C18 100 nF | Match |
| C_OUT | 22 µF | C19 22 µF | Match |
| SS/TR | 3.3 nF | C20 3.3 nF | Match |
| FSW | Low = 2.5 MHz, high = 1.25 MHz | Low | Agent choice. 1.25 MHz may be more efficient; G6 can test with a 0 Ω option at G3. |
| PG | Pull-up to < 7 V | R19 100 k to +5V | Match |

## LTC2954-1 pushbutton on/off controller (U8)

Source: ADI datasheet 2954fb (p. 2-6, Fig. 5, Fig. 6, Fig. 9).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| VIN | 2.7-26.4 V, 33 V abs. max. | VLOGIC (up to ~8.4 V) + C11 100 nF | Match |
| C_ONT | 0.033 µF (Fig. 5) → t = C / 1.56 × 10⁻⁴ µF/ms + 1 ms ≈ 213 ms | C12 33 nF | Match |
| C_PDT | 1 µF (Fig. 5) → 6.4 s | C13 1 µF | Match |
| EN (open drain, -1 = active high) | Needs a pull-up (plots use 100 k to VIN) | R13 100 k to VLOGIC | Match |
| /INT | Open drain, 10 V max | R15 10 k to 3V3 → expander U11 P3 | Match |
| KILL | 0.6 V threshold; 7 V max; 512 ms blanking after turn-on | R14 100 k to 3V3; wired-OR of GPIO48 and U23 OUTA | Match. 3V3 comes up within the blanking time. |
| PB | Internal 100 k pull-up; add 10 k to VIN if board leakage > 2 µA (Fig. 9) | Switch to GND, no external pull-up | Optional external pull-up omitted. Revisit at G6 if the button misfires. |

## TLV6700 undervoltage cut-off (U23, D-053, D-055)

Source: TI datasheet (§6, §7.5, §8.1, §8.4.3).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| Threshold | V_IT− = 394.5 mV typ., V_IT+ = 400 mV | R16 1.5 M / R17 110 k → 5.77 V trip, 5.85 V release | Calculated (review: was 6.31 V, which load sag would trip) |
| Filter | – | C24 4.7 µF on UV_SENSE: τ = (1.5 M ‖ 110 k) × 4.7 µF = 0.48 s | Agent addition (review) so throttle punches do not cut power |
| Output below UVLO | OUTA is held low from V_POR (≤ 0.8 V) up to UVLO (1.3-1.7 V) (§8.4.3) | Q5 AO3400A between OUTA and KILL, gate = VBUS_DET: cut-off disabled while USB is present | Review fix: without it the board could not power on from USB alone |
| VDD | 1.8-18 V | VBAT + C14 100 nF | Match |
| Unused channel B | Tie INB− low → OUTB stays high-impedance | INB− → GND, OUTB open | Match |
| Divider current | – | 8.4 V / 1.61 M = 5.2 µA, always on | A permanent battery drain, together with about 5 µA of quiescent current (UNCONFIRMED). |

## TPS22810 ESC gate-driver supply switch (U24, D-036)

Source: TI datasheet (§9.3.3 and agent summary).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| VIN | 2.7-18 V | VBAT + C21 1 µF | Match (minimum 1 µF) |
| EN/UVLO | 1.23 V rising; may be driven from a 3.3 V GPIO; must not float | PWR_EN (open drain + 100 k to VLOGIC) | Match. EN above VIN when running on USB only (VIN = 0): UNCONFIRMED whether that is allowed. |
| CT | 2.2 nF → 464 µs at 12 V | C23 3.3 nF (≈ 0.7 ms) | Agent choice |
| QOD | Tie to VOUT for output discharge | QOD → VDRV_SW | Match |
| C_IN : C_L | 10 : 1 recommended | VIN is the whole VBAT bank (FC capacitors + ESC 100 µF + 8 × 10 µF) against 22 µF on VDRV_SW | Match (review corrected the first draft's reading) |

## MT3608 9.6 V boost for the ESC gate drivers (U25, D-054)

Source: MT3608 datasheet (pin description, setting the output voltage, inductor/capacitor/diode selection).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| Pins | 1 SW, 2 GND, 3 FB, 4 EN, 5 IN, 6 NC | As listed | Match |
| Output | VOUT = 0.6 V × (1 + R1/R2) | R25 150 k / R26 10 k → 9.6 V | Calculated. Which resistor is on top was read from text only (figure not extracted). |
| Inductor | 4.7-22 µH, check saturation current | L4 10 µH; Isat 1.6 A assumed from the sister part | Peak ≈ 0.25 A. Isat of the fitted variant is UNCONFIRMED. |
| Capacitors | 22 µF ceramic in and out | C25, C26 22 µF 25 V | Match |
| Diode | Schottky, rated for the peak current and above VOUT | D6 1N5819WS (40 V, 1 A) | Match |
| EN | High = on; tie to IN if unused | Tied to VDRV_SW (on whenever the switch is on) | Match |

## INA226 current and voltage monitor (U9)

Source: TI datasheet (Table 6-2, §6.4.2, Fig. 8-1).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| Address | A0 = A1 = GND → 0x40 | Both to GND | Match |
| Input filter | ≤ 10 Ω per input + 0.1-1 µF differential | R1, R2 10 Ω; C1 100 nF | Match |
| VS bypass | 0.1 µF | C2 100 nF | Match |
| VBUS pin | 0-36 V | VBAT (load side of the shunt) | Match |
| ALERT | Open drain | Wired-OR on EXP_INT_N (R32 10 k) | Match |

## ME6211 camera LDOs (U6 2.8 V, U7 1.2 V)

Sources: Microne datasheet V14; Espressif ESP32-S3-EYE schematic.

| Item | Reference | Schematic | Status |
|---|---|---|---|
| VIN | 2-6 V | +3V3 | Match |
| Capacitors | 1 µF in / 1 µF out (test conditions); S3-EYE uses 10 µF + 0.1 µF on each side | 1 µF in; 10 µF + 100 nF out | Match (output as S3-EYE) |
| CE | High = on | Tied to +3V3 (always on, D-049) | Match (S3-EYE also ties CE to VIN) |
| DVDD voltage | OV2640 core 1.14-1.26 V; S3-EYE feeds 1.5 V | 1.2 V | Follows the sensor datasheet; OQ-15. |

## USB-C input and ESD (J1, U22)

Sources: ST USBLC6-2 datasheet DS4260; USB Type-C sink termination; Espressif ESP32-S3 checklist.

| Item | Reference | Schematic | Status |
|---|---|---|---|
| CC | Rd 5.1 k to GND on each CC pin (sink) | R38, R39 5.1 k | Match |
| ESD | USBLC6-2SC6: I/O1 = 1/6, I/O2 = 3/4, VBUS = 5, GND = 2 | As listed | Match |
| Series resistors | 22-33 Ω near the chip | R40, R41 22 Ω | Match |
| VBUS | – | Charger VBUS + D2 (SS34) into VLOGIC (D-046); R20 100 k bleed | Design choice |

## ESP32-S3-WROOM-1 module (U1)

Source: module datasheet §9 (peripheral schematic) and the Espressif checklist.

| Item | Reference | Schematic | Status |
|---|---|---|---|
| 3V3 decoupling | 22 µF + 0.1 µF (+ 0.1 µF) | C30 22 µF, C31/C32 100 nF | Match |
| EN RC | 10 k + 1 µF | R30 10 k, C33 1 µF; RESET button | Match |
| GPIO0 | Pull-up recommended; no large capacitor | R31 10 k; BOOT button | Match |
| Strapping | See `pullups-straps.md` | – | – |

## FD6288Q gate driver and bridge (ESC, per motor)

Source: Fortior FD6288 datasheet V1.6 (§1.5, Tables 3-1 to 3-4).

| Item | Reference | Schematic | Status |
|---|---|---|---|
| VCC | 5-20 V; 10 µF "optional"; UVLO 4.6 V typ / 5.0 V max rising | VDRV 9.6 V boosted (D-054) + 1 µF + 100 nF per driver, plus the 10 µF on the ESC regulator input | **Deviation:** 1 µF instead of 10 µF per driver to save area. Review: the boost replaced raw 2S, which sat too close to UVLO under sag. |
| Bootstrap diode | External Schottky (the application circuit shows one) | 1N5819WS per phase, anode VDRV | Match |
| Bootstrap capacitor | Not stated | 1 µF per phase (calculation in the schematic note) | Agent calculation |
| Gate resistors | Not stated | 10 Ω series per gate (OpenESC uses 15 Ω with a different driver) | Agent choice; tune at G6 |
| Gate-source resistors | Application circuit shows "R2: MOS gate and source resistor" (§1.5) | 47 k on every FET | Match (review: missing in the first draft; needed because VBAT stays on the bridge when off) |
| Logic level | VIH 2.7 V min | AT32 at 3.3 V: VOH ≈ VDD − 0.4 V at low load | Margin only 0.2-0.5 V; check on the bench (G6) |
| Logic inputs | 3.3 V compatible, 200 k pull-down; outputs follow inputs | AT32 timer outputs, active high (AM32 default polarity) | Match |
| Back-EMF divider | OpenESC-20x20: 10 k / 1 k + 10 k to neutral (6S) | 10 k / 2.2 k + 10 k to neutral | Scaled for 2S: 1.59 V maximum at the comparator |

## Sensors (decoupling and pins)

| Part | Reference | Schematic | Status |
|---|---|---|---|
| ICM-42688-P | VDD 0.1 µF + 2.2 µF; VDDIO 10 nF; RESV → GND; FSYNC → GND if unused (Tables 10-11) | C50, C51, C52; all RESV and INT2 → GND | Match |
| BMP388 | 100 nF on VDD and VDDIO; CSB to VDDIO and SDO to GND for I²C 0x76 | C53, C54; CSB → 3V3; SDO → GND | Match |
| QMC5883P | C1 pin 4.7 µF, ESR < 200 mΩ | C55 4.7 µF X5R | Match. C56 100 nF VDD capacitor added by the agent. |
| TCA6408A | RESET pull-up if not driven; INT open drain; bypass capacitor at VCCP (value not given) | R53 10 k; C57/C58 100 nF | Match. 100 nF is the agent's value. |
| VL53L1X (satellite) | 4.7 µF + 100 nF at AVDDVCSEL; XSHUT pull-up 10 k | C1, C2; XSHUT **pull-down** 10 k | **Deviation:** pull-down holds the sensor in reset for re-addressing (D-052) |
| VL53L5CX (satellite) | 4.7 µF + 100 nF (Fig. 5); INT, LPn, C2 47 k up; I2C_RST 47 k down; RSVD → GND | 2 × (4.7 µF + 100 nF); INT, C2 up; I2C_RST down; LPn **down** | **Deviation** on LPn (D-052). Which capacitor goes on which pin is UNCONFIRMED. |
