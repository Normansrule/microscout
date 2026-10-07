> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# Part selection and findings (drone) - rev B

The machine-readable list with LCSC numbers, prices, stock and datasheet links is **`bom/drone-bom-g1.csv`**. Values below were read from pages fetched 2026-10-03 to 2026-10-07, mostly through a web-fetch tool that summarises pages; they are datasheet or vendor readings, not independently verified. **Prices and stock change daily.** Rev A choices are at git tag `g1-rev-a`.

## What changed from rev A, and why

| Area | Rev A | Rev B | Reason |
|---|---|---|---|
| Propulsion | 4x brushed 8520, 55 mm props, AO3400A drivers | 4x **EX1103 11000KV brushless**, 2-inch 3-blade props in ducts, separate **4-in-1 AM32 ESC** board | Flips and speed need T/W ≥ 4; rev A reached 1.6-2.0. EX1103 vendor table: 121.9 g at 9.2 A on 7.4 V (S15). Same motor as the 85 mm 2S Mobula8 |
| Battery | 1S 660 mAh, JST-PH | **2S LiHV 550 mAh**, XT30 + JST-XH balance | Brushless 1103 motors are 2S motors; XT30 is rated 15 A cont / 30 A peak vs JST-PH 2 A |
| Charger | BQ24074 (1S) | **BQ25887** 2S boost charger with balancing | 2S from 5 V USB needs a boost charger and cell balancing |
| Regulators | TPS63802 buck-boost, TPS61023 boost | **TPS62162** 3.3 V buck, **TPS62133** 5 V buck | 2S is always above 5 V, so plain bucks work |
| IMU | BMI270 | **ICM-42688-P** | Betaflight docs: ICM-42688-P "recommended for new designs" (8 kHz); BMI270 "not recommended" (3.2 kHz). LCSC price is $3.39 - the earlier $19.64 was a stale third-party figure |
| Frame | PCB is the frame; printed canopy with guards | **One-piece ducted frame** (PA11 prototype, PP for production); boards soft-mounted inside; TPU canopy | Crash loads go through the frame, not the PCB. Bitcraze: "we want the motor mount to break instead of the PCB arms" |
| Protection | 10/15 A fuse, P-FET reverse protection, motor-rail P-FET switch | No fuse (firmware 30 A current limit); no reverse FET - keyed XT30 + JST-XH only (D-035, OQ-10); soft switch on logic rails and ESC driver supply (D-036) | A 37 A full-throttle path makes series fuses and P-FETs lossy and bulky; commercial whoops rely on keyed connectors and ESC current limiting |

## Selected parts (rev B)

| Block | Part | LCSC | Key values read | Risk |
|---|---|---|---|---|
| MCU + radio | ESP32-S3-WROOM-1-N8R2 | C2913204 | unchanged from rev A | 35 of 36 GPIOs used (GPIO1 spare) |
| IMU | ICM-42688-P | C1850418 | 1.71-3.6 V, SPI 24 MHz, 0.88 mA, $3.39 | - |
| Charger | BQ25887RGER | C2761614 | 3.9-6.2 V in, 2 A boost, 93.4 % at 5 V → 7.6 V / 1 A, balancing 400 mA, $5.08 | needs pack balance lead; 698 in stock |
| 3.3 V | TPS62162DSGR | C40256 | 3-17 V in, 1 A, fixed 3.3 V, $1.29 | 1 A vs ~0.95 A peak - tight |
| 5 V | TPS62133RGTR | C73973 | 3-17 V in, 3 A, fixed 5 V (per LCSC), $1.69 | confirm suffix in datasheet |
| Battery monitor | INA226 + 1 mΩ 2 W shunt | C49851, C2924520 | 81.9 A full scale, 2.5 mA LSB | - |
| Soft switch | LTC2954-1 | C580652 | unchanged | 11 in stock, $6.22 |
| ESC MCU (x4) | AT32F421G8U7 | C2765098 | AM32 supports AT32F421 (GPL-3.0), $0.76 | package not shown on LCSC page |
| Gate driver (x4) | FD6288Q (JSMSEMI second source) | C7466367 | 5-20 V supply → runs from 2S; $0.41 | Fortior original 0 in stock; JSMSEMI stock unknown (OQ-9) |
| ESC FETs (x24) | HL 60N03D | C7471100 | 30 V, 60 A, 4.7 mΩ, PDFN3333, $0.068 | 24 parts = board area; dual-N part would halve it |
| Reverse protection | **not fitted** (Q1 kept as ALTERNATE) | - | ground-return FETs are bypassed by the balance lead (budgets 4b) | OQ-10: keyed connectors vs high-side ideal-diode controller |
| ESC driver supply switch | Q4, part TBD | - | switches FD6288Q VCC from VBAT with the soft switch (D-036) | chosen at G2 |
| Battery connector | XT30PW-M (right angle) | C431092 | 15 A cont / 30 A peak (retailer) | gender must mate the pack; full throttle exceeds peak rating |
| Motors (x4) | Happymodel EX1103 11000KV | - | 3.8 g; 121.9 g / 9.2 A on 7.4 V (vendor table); $14.99 each | vendor data only |
| Props (x4) | Gemfan Hurricane 2023 3-blade | - | 2-inch, 1.5 mm T-mount; $3.99 per 4 | designed sacrificial part |
| Battery | GNB 2S 550 mAh 100C LiHV XT30 | - | 29 g, 12x18x69 mm, JST-XH balance plug; A$13.99 | LAVA alternative discontinued |
| Everything else | as rev A (sensors, camera, expanders, LEDs, buzzer, USB, ESD) | see BOM | | barometer and flow-lens sourcing still open |

## Firmware base for acro (OQ-8)

- **esp-drone** (Espressif, GPL-3.0, Crazyflie-derived): good for autonomy and position hold; no brushless/DShot support documented.
- **esp-fc** (rtlopez): Betaflight-style acro controller for ESP32 with DShot and Betaflight Configurator over MSP; release notes report "esp32-s3 bidir dshot support" but also "ESP32-S2 and ESP32-S3 are not ready yet" for web flashing; listed gyros do not include ICM-42688-P or BMI270; licence UNCONFIRMED.
- The Python reference controller in `software/microscout_sdk/src/microscout/sim/fc.py` defines the behaviour either base must reach (cascade, modes, flips, safety).

## Key sources

- EX1103 table: <https://druav.com/en-us/products/happymodel-ex1103-brushless-motor> · Mobula8: <https://www.getfpv.com/micro-quadcopters/micro-rtf-bnf/happymodel-mobula8-1-2s-85mm-analog-drone.html>
- Betaflight supported sensors: <https://betaflight.com/docs/wiki/guides/current/Supported-Sensors> · rates: <https://betaflight.com/docs/wiki/guides/current/Rate-Calculator>
- AM32: <https://github.com/am32-firmware/AM32> · OpenESC 30x30 (AM32, CERN-OHL-S-2.0): <https://hub.allspice.io/AllSpiceMirrors/incutec-OpenESC-30x30>
- BQ25887: <https://www.ti.com/product/BQ25887> · TPS62162: <https://www.ti.com/product/TPS62162> · TPS62133: <https://www.ti.com/product/TPS62133>
- esp-fc releases: <https://github.com/rtlopez/esp-fc/releases> · ESP-IDF RMT (DShot example): <https://docs.espressif.com/projects/esp-idf/en/v5.1.4/esp32s3/api-reference/peripherals/rmt.html>
- Bitcraze on arm breakage: <https://forum.bitcraze.io/viewtopic.php?p=664> · PP whoop frames: <https://www.getfpv.com/betafpv-meteor75-pro-brushless-whoop-frame-black.html>
- Materials: HP PA11 <https://3dprinting.com/wp-content/uploads/2019/02/HP-PA-11-TDS-4AA7-0715ENE.pdf>, Bambu TPU 95A <https://polyalkemi.no/wp-content/uploads/2023/06/Bambu_TPU_95A_Technical_Data_Sheet.pdf>
- Every number in the budgets: sources S1-S28 at the end of `budgets.md`.
