> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1

# Part selection and findings (drone)

The machine-readable part list with LCSC numbers, prices, stock and datasheet links is **`bom/drone-bom-g1.csv`**. This page explains the choices and lists what each check found. All values were read from pages fetched on 2026-10-03/04 (mostly via a web-fetch tool that returns a summary of the page, not the raw PDF); every LCSC number marked `page` in the CSV was seen on its LCSC product page with the part name matching. **Prices and stock change daily and must be re-checked before ordering.**

## Selected parts by block

| Block | Selected | LCSC | Key datasheet values read (not independently verified) | Main finding / risk |
|---|---|---|---|---|
| MCU + radio | ESP32-S3-WROOM-1-N8R2 | C2913204 | 8 MB flash, 2 MB quad PSRAM, -40..85 C; 3.0-3.6 V, supply ≥ 0.5 A; Wi-Fi TX peak 355 mA (802.11b, 20.5 dBm); antenna should overhang the board edge or have board cut away beneath it | Uses every GPIO (D-021) |
| Charger | BQ24074RGTR | C54313 | 4.35-10.2 V input, OVP ~10.5 V; up to 1.5 A charge, I = 890/R_ISET; OUT recommended max 4.5 A | Motors must not use OUT (D-012) |
| 3.3 V | TPS63802DLAR | C2845237 | 2 A for V_IN ≥ 2.3 V; 11 uA I_Q; ~88-92% at 3.6 V/300-500 mA (graph) | Borderline vs 90% (D-014) |
| 5 V | TPS61023DRLR | C919459 | 0.5-5.5 V in; 3.7 A valley switch limit; true load disconnect | Max output at 3.0 V in not stated - calculate at G2 |
| 1.8 V (IMU) | TLV70018DDCR | C79924 | 200 mA, 2-5.5 V in, 31 uA I_Q | Optical-flow core gets a separate 1.9-2.0 V LDO (U5B, chosen at G2) because 1.8 V nominal sits on the PMW3901 1.8-2.1 V lower limit |
| Camera rails | ME6211C28M5G-N / ME6211C12M5G-N | C53099 / C236672 | CE active high; 450 mA / 300 mA (LCSC listing) | MOQ 10 each |
| Soft power | LTC2954CTS8-1 | C580652 | 2.7-26.4 V, 6 uA; KILL active low, ignored 400-650 ms after turn-on | **11 in stock, $6.22** |
| Battery monitor | INA226AIDGSR | C49851 | Bus 0-36 V, shunt ±81.92 mV, 16 addresses | Needs calibration register written before current reads |
| Expanders (x2) | TCA6408ARGTR | C181499 | Power-up = inputs, high-Z; 0x20/0x21 | Needs external pulls (D-010) |
| IMU | BMI270 | C2836813 | VDD 1.71-3.6 V, VDDIO 1.2-3.6 V; 970 uA performance mode | 8 kB config upload each boot; chosen over ICM-42688-P on cost |
| Barometer | BMP390 | C5124834 | 570 uA drone use case; 0x76/0x77; light-sensitive | **Out of stock** (also DPS310, SPL06-001) |
| Magnetometer | QMC5883P | C2847467 | 2.5-3.6 V; 400 kHz; 0x2C fixed; no copper under/near | Placement constraint (D-008) |
| ToF x4 | VL53L1CXV0FY/1 | C190004 | 0x29 default; XSHUT each; 16 mA avg / 40 mA peak; min range 4 cm | 4 x $4.39 is a large cost line |
| Multizone ToF | VL53L5CXV0GC/1 | C3178303 | 0x29 default; LPn; ~84 kB firmware upload; 313 mW at 3.3 V | 1.9 s boot upload at 400 kHz |
| Optical flow | PMW3901MB-TXQT (conditional) | C43496881 | VDD 1.8-2.1 V, VDDIO 1.8-3.6 V (≥ VDD); 9 mA; 80 mm to infinity; needs LN03-ZSZ lens | **Lens has no confirmed source** (OQ-4); X-ray at JLCPCB |
| LED data buffer | SN74AHCT1G125DBVR | C7484 | VIH 2.0 V at VCC 4.5-5.5 V; 3.8 ns typ | - |
| USB ESD | USBLC6-2SC6 | C7519 | 6 V min breakdown, 3.5 pF max, IEC 61000-4-2 8 kV contact | - |
| Reverse FET, motor switch | DMP2008UFG-7 (x2) | C461052 | -20 V, -14 A, 9.8 mOhm max at -2.5 V ("Advance Information" datasheet) | 600 in stock; alt CSD25402Q3A |
| N-FETs (x6) | AO3400A | C20917 | 48 mOhm max at 2.5 V; 5.7 A; Vgs(th) ≤ 1.45 V; JLCPCB Basic | - |
| Flyback (x5) | B5819W SL | C8598 | 1 A, 40 V, 0.6 V; JLCPCB Basic | Re-check average current at G2 |
| Fuse | Littelfuse 0451015.MRL | C44480 | 15 A, 65 V DC, 2410; melting I2t 97.82 A2s (LCSC listing) | 10 A part rejected (below full-throttle estimate after derating); check I2t vs 4-motor start-up at G2 |
| USB-C | TYPE-C-31-M-12 | C165948 | 16-pin, 5 A/20 V rating | - |
| Camera FPC | XUNPU FPC-05F-24PH20 | C2856805 | 24-pin, 0.5 mm, bottom contact, flip lock | Contact side vs module - confirm |
| Buzzer | MLT-5020 | C94598 | 3 V (2-4 V), 100 mA, 4 kHz; JLCPCB Basic | Needs FET drive |
| LEDs (x4) | WS2812B-2020 | C965555 | VDD 3.7-5.3 V; VIH 0.7 VDD; 16 mA per colour (test) | Needs 5 V rail (D-015) |

Off-board: 8520 motors (4.5-5.5 g, 1.0 mm shaft, vendor specs vary widely), 55 mm props, GNB 660 mAh 1S HV (15.5 g, 58x18x7.8 mm, PH2.0 lead), BetaFPV ELRS Lite receiver (5 V, 0.46 g), OV2640 24-pin FPC camera module (vendor and pinout TBD).

## Findings that change the brief's assumptions

1. **GPIO count forces a quad-PSRAM module.** Octal modules lose GPIO35-37; the design needs all 36 GPIOs (pin-allocation.md).
2. **JST-PH 2.0 is rated 2 A per contact** (JST datasheet) against ~4.6-5.6 A hover and ~8-11 A full-throttle estimates (OQ-2).
3. **No measured 8520 thrust data for 55 mm props was found.** Using the secondhand 33-36 gf (60 mm props) figure, T/W is ~1.6-2.0 at the nominal 71.6 g and ~1.2-1.5 at the 94 g worst case (OQ-3).
4. **65 mm props do not fit with guards** on a ≤100 mm frame (tip gap 2.2 mm at 95 mm).
5. **Cost target likely exceeded**: priced lines alone ~$69/drone (OQ-5).
6. **ELRS receivers and WS2812B-2020 need ~5 V**, so a 5 V boost and a level buffer are added (D-015).
7. **All three barometer candidates were out of stock** at LCSC on 2026-10-04 (OQ-6).
8. **esp-drone**: supports ESP32-S3 per its README, targets ESP-IDF `release/v5.0`, has had limited support since Dec 2022, has MPU6050/VL53L1X/PMW3901 drivers but none for BMI270, BMP390, QMC5883P, VL53L5CX, INA226 or camera streaming (OQ-8). **Whether it can fly this sensor set while streaming video is UNCONFIRMED.**
9. **Camera modules**: OV2640 24-pin FPC modules expect the host to supply AVDD/DVDD (e.g. Espressif ESP32-S3-EYE supplies 2.8 V and 1.5 V from on-board LDOs). Pinout and rails vary by vendor - confirm on the actual module.

## Key sources

- ESP32-S3-WROOM-1 datasheet: <https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf>
- Espressif hardware design guidelines (schematic checklist, PCB layout): <https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/>
- esp32-camera driver: <https://github.com/espressif/esp32-camera>
- esp-drone: <https://github.com/espressif/esp-drone>, docs <https://docs.espressif.com/projects/espressif-esp-drone/en/latest/>
- JST PH datasheet: <https://www.jst-mfg.com/product/pdf/eng/ePH.pdf>
- ExpressLRS receiver wiring: <https://www.expresslrs.org/quick-start/receivers/wiring-up/>
- FAA recreational flyers: <https://www.faa.gov/uas/recreational_flyers>; registration: <https://www.faa.gov/uas/getting_started/register_drone>
- Per-part datasheets: `datasheet_url` column in `bom/drone-bom-g1.csv`; calculation sources S1-S27 at the end of `budgets.md`.
