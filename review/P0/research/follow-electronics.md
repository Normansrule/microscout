> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate. Research notes compiled on 2026-10-26 from the sources listed at the end; items not checked against a primary source are marked UNCONFIRMED.

# Wisp Follow: Electronics Selection (ArduPilot, sub-250 g ducted 3-3.5 in quad)

Research date: 2026-10-26. Web research only.

**Legend**
- Figures come from the maker's page unless marked otherwise. A retailer figure carries the retailer's name.
- **ESTIMATE**: my figure, not from the maker or a retailer.
- **UNCONFIRMED**: I could not verify it today, either because the page was unreachable from this session or because sources conflict.
- "AP wiki" is the ArduPilot documentation. I read its source files on GitHub (ArduPilot/ardupilot_wiki, master) because ardupilot.org itself was blocked for this session.
- "hwdef" means `libraries/AP_HAL_ChibiOS/hwdef/<name>/hwdef.dat` in ArduPilot master.

**Access limits.** The proxy blocked these sites for direct fetches today: ardupilot.org, firmware.ardupilot.org, micoair store, holybro.com (partly), expresslrs.org, benewake.com, mateksys.com, pololu, Raspberry Pi resellers (except Adafruit and SparkFun), Radxa, Luckfox, Milk-V, OpenMV, Amazon and AliExpress. The web-search quota also ran out partway through. For that reason the companion-computer alternatives and the Remote ID modules are mostly UNCONFIRMED. Firmware-server target folders were checked by hwdef name only; I did not open the server's folder listings.

---

## 1. Flight controller (FC) / all-in-one board (AIO, FC plus 4-in-1 Electronic Speed Controller (ESC))

| # | Model | Mass | Size / mount | Price / retailer / stock (2026-10-26) | ArduPilot status | Notes |
|---|---|---|---|---|---|---|
| 1 | **MicoAir H743 v2 AIO 35A** (MicoAir743v2-AIO-35A): STM32H743, BMI088 + BMI270 IMUs, SPL06 barometer, Bluejay 35A 4-in-1 ESC | **10 g** (maker; does not say whether cables are included) | 36 x 36 x 8 mm, **25.5 x 25.5 mm whoop mount, 3 mm holes** | **$87.99, Pyrodrone, In stock** | The maker page has ArduPilot sections (UART map, RC, OSD). **Target `MicoAir743v2`** per retailer Unmanned Tech UK; the maker page gives only PX4 build names (`micoair_h743-v2_default`), so the target is **UNCONFIRMED by the maker**. hwdef `MicoAir743v2` exists in master and is listed in the AP wiki "Choosing an Autopilot" page. | 7 UARTs (UART1-6, UART8), 1 external I2C bus, no compass, 2-6S. Bidirectional DShot on channels 1-8. ESC rated **35A continuous per channel**; Pyrodrone says it "requires good cooling". Bluejay 0.19.2 firmware, DShot300/600 and bidirectional DShot (Pyrodrone). |
| 2 | **Flywoo GOKU GN745 V3 AIO 45A** (F745, ICM42688 since Fall 2025, AM32 ESC) | **9.4 g** (AP wiki and GetFPV) | 33.5 x 33.5 mm, 25.5 x 25.5 mm mount | Price not readable on GetFPV; **In stock, GetFPV** (limited quantity) | Listed in the AP wiki as "Flywoo F745 AIO BL_32/ Nano". hwdef `FlywooF745` exists. Whether the V3 is covered by the same wiki page/target is **UNCONFIRMED**. | 7 UARTs, I2C, **45A continuous**, 2-6S. F7 class with 1 MB flash. |
| 3 | **SpeedyBee F405 AIO 40A Bluejay** (V1) | **13.6 g** including CNC parts (Pyrodrone; also AP wiki) | 33 x 33 mm, 25.5 x 25.5 mm mount, 3 mm holes | $71.99, Pyrodrone, **Sold out**. A "V2" is $92.49 at RaceDayQuads, stock not shown, and its ArduPilot compatibility is **UNCONFIRMED**. | AP wiki page; target **`SpeedyBeeF405AIO`**; hwdef exists | 6 UARTs, but UART1 is tied to the Bluetooth module and unusable, so 5 are usable. F405 with 1 MB flash, so some features are cut. **40A continuous / 45A burst for 10 s**, 3-6S. |
| ref | **MicoAir743-AIO 35A** (v1, AM32) | 10 g | 36 x 36 x 8 mm, 25.5 x 25.5 mm | Maker page says **"Discontinued"** | target `MicoAir743-AIO`, AP wiki page, hwdef exists | 7 UARTs, 1 I2C, BMI088 + BMI270, DPS310 barometer, AM32 35A ESC (35A continuous per Rotor Village). ArduPilot since 4.6 (Rotor Village). |
| ref | **MicoAir NxtPX4v2** (FC only, H743, dual BMI088) | **6.5 g** (AP wiki) | 27 x 32 x 8 mm, **20 x 20 mm, 3 mm holes** | **$71.99, Pyrodrone, In stock** | target `NxtPX4v2`, AP wiki page, hwdef exists | 7 UARTs, I2C, 8 PWM outputs with bidirectional DShot. Needs a **separate 20x20 4-in-1 ESC** (not researched; mass and price UNCONFIRMED). |
| ref | **Holybro Kakute H7 Mini v1.5** | 5.5 g (Flying Tech / OpenELAB) | 20 x 20 mm | Sold out at OpenELAB and Flying Tech | target `KakuteH7Mini` / `KakuteH7Mini-Nand`. The AP wiki **moved it to "Discontinued Boards"**: "v1.5 has been unavailable since mid 2025". | Do not plan around it. |

**ESC current for 1404-1505 motors on 4S.** I did not verify any motor datasheet current today (UNCONFIRMED). The ESC ratings above are 35A continuous (MicoAir v2), 45A continuous (Flywoo V3) and 40A continuous / 45A burst (SpeedyBee). Each is per channel. Check the chosen motor's peak current on 4S against these ratings.

**No ArduPilot-documented H7 AIO in 20 x 20 was found.** The H7 AIO options are MicoAir's 25.5 mm boards. The only 20 x 20 H7 with an ArduPilot target that is still in stock is the NxtPX4v2, and it needs a separate ESC.

---

## 2. Global Positioning System (GPS) receiver with compass (u-blox M10 class)

| Model | Mass | Size | Compass | Price / retailer / stock | Notes |
|---|---|---|---|---|---|
| **Flywoo GOKU GM10 Nano V3 GPS w/ compass** | **2.6 g** (Flywoo); RaceDayQuads says 2.8 g | 12 x 17 x 5 mm | Yes, QMC5883L (Flywoo 2026 buyer's guide) | **$20.99, Flywoo**. Stock is contradictory: "Only 750 left" next to a "Sold Out" button. $25.49 at RaceDayQuads, stock not shown. | M10050 chip, 4800-921600 baud (default 115200), 100 mm cable included. The pad count is contradictory (6-pin vs 4-pin). The patch antenna is small. |
| Flywoo GOKU GM10 Mini V3 GPS w/ compass | 4.1 g (Flywoo guide and GetFPV) | 18 x 18 x 4.8 mm | Yes, QMC5883L | GetFPV: price not shown, stock contradictory | Flywoo lists the compass version as lighter than the non-compass one (4.7 g), which looks inconsistent. Weight is UNCONFIRMED. |
| HGLRC M100-5883 (10th gen) | 7.73 g (WREKD) | 21 x 21 x 8.02 mm | Yes (chip not named) | $16.99 WREKD, "Coming soon / backorder"; $20.49 RaceDayQuads, stock not shown | M10 chip |
| Matek M10Q-5883 | 8 g (GetFPV) | 20 x 20 x 12.4 mm | QMC5883L | $51.99 GetFPV, **Out of stock**; $47.99 RaceDayQuads, stock not shown | u-blox SAM-M10Q, the largest antenna of the group |
| Holybro Micro M10 | 14 g without case / 16 g with case (Holybro) | 32 x 26 x 9 / 34 x 28 x 11 mm | IST8310 or IST8308 | $27.99 Holybro: without case **In stock**, with case Sold out. With case $36.49 at GetFPV, In stock. | Includes a JST-GH 6-pin cable. Too heavy for this build. |

On ArduPilot, every module above appears as a u-blox GPS on a UART plus an I2C compass on the FC's single I2C bus.

---

## 3. Downward optical flow plus Time-of-Flight (ToF) rangefinder

| Model | Mass | Size | Range (ToF) | Price / retailer / stock | ArduPilot parameters |
|---|---|---|---|---|---|
| **MicoAir MTF-01** | **4.5 g** (Pyrodrone listing) | 29.3 x 17 x 14.5 mm, 24.3 x 12 mm mount | **8 m** (90% reflectance, 600 lux); **5 m** at 60k lux; 2 cm dead zone; flow works above 8 cm and needs more than 60 lux; up to 7 m/s at 1 m | **$32.99, Pyrodrone, In stock** | AP wiki page `common-mtf-01`: UART, `SERIALx_PROTOCOL=1` (MAVLink1), 115200 baud, **`FLOW_TYPE=5` (MAVLink)**, **`RNGFND1_TYPE=10` (MAVLink)**, `RNGFND1_MAX=8`, `RNGFND1_ORIENT=25`. Disable MAVLink forwarding on that port (`MAVx_OPTIONS=2` on 4.7+, `SERIALx_OPTIONS=1024` before 4.7). Set the sensor's mav_id to a value other than 1 (for example 200) with MicoAssistant. Check `FLOW_ORIENT_YAW` (18000 if mounted in the INAV orientation). |
| MicoAir MTF-02P | **1.8 g** (Rotor Village) | 21.6 x 16 x 6.5 mm | 6 m (1k lux) / 4 m (70k lux), 50 Hz | $21.99 Pyrodrone, **Sold out**; Rotor Village sold out | MAVLink, MSP or Micolink, chosen by jumper. Same `FLOW_TYPE=5` / `RNGFND1_TYPE=10` setup (inferred from the MTF-01 page; AP wiki has no MTF-02P page). The plain MTF-02 is 4.5 g on the maker page; no range was listed there. |
| MicoAir MTF-01P | 8 g (Rotorama) | 33.2 x 20.8 x 16.8 mm | 12 m (600 lux) / 8 m (60k lux) | $41.99 Pyrodrone, In stock | Same as MTF-01 |
| Matek 3901-L0X | 2 g (GetFPV) | 36 x 12 mm | VL53L0X, 8-200 cm | $38.99 GetFPV, **Out of stock** | AP wiki: `FLOW_TYPE=7` (MSP), `SERIALx_PROTOCOL=32`, `RNGFND1_TYPE=32`, `RNGFND1_MAX=1.2`. AP wiki **warns that the lidar is very short-range outdoors**. |

Not researched today: ThoneFlow-3901U with a separate VL53L1X. The ArduPilot flow-type list is 0 None, 1 PX4Flow, 2 Pixart, 3 Bebop, 4 CXOF, 5 MAVLink, 6 DroneCAN, 7 MSP, 8 UPFLOW, 10 SITL (AP_OpticalFlow source).

---

## 4. Forward and side obstacle sensors

**How ArduPilot builds a proximity map from single-beam rangefinders** (AP wiki `common-rangefinder-setup`, `common-simple-object-avoidance`):
- ArduPilot supports **up to 10 rangefinders** (RNGFND1 through RNGFNDA).
- Object avoidance can use **up to 9 single-direction rangefinders**: 8 around the vehicle covering 45-degree segments, plus one facing up. A downward rangefinder is used for height above ground.
- Set `RNGFNDx_ORIENT` for each sensor. ArduPilot's rotation enum is 0 Forward, 2 Right, 4 Back, 6 Left, 24 Up, 25 Down; the enum values are from my knowledge, not checked against source today.
- Set **`PRX1_TYPE = 4` (RangeFinder)** and `AVOID_ENABLE = 7`. `AVOID_MARGIN` and `AVOID_BEHAVE` (stop or slide) apply in Loiter.
- Simple avoidance works in AltHold and Loiter. AUTO and GUIDED use BendyRuler or Dijkstra.
- ArduPilot supports up to 4 proximity sensors, and only one forward rangefinder is required.
- The PRX log records the 8 quadrants.

| Model | Mass | Range | Interface / ArduPilot type | Price / retailer / stock | Notes |
|---|---|---|---|---|---|
| **Benewake TFS20-L** | **2 g** (AP wiki table); 1.35 g (RobotShop) | 0.20-15 m (AP wiki); "20 m, 15 m at 100 klux", 2 degree field of view, up to 250 Hz (Probots) | 3.3 V supply, UART or I2C. **`RNGFNDx_TYPE=46` (BenewakeTFS20L-I2C)**, default address 0x10 (driver source); `RNGFNDx_ADDR` overrides it. | $53.84 RobotShop (stock not shown); Probots out of stock | The best mass-to-range ratio found. Whether the I2C address can be changed and stored on the sensor (needed for several on one bus) is **UNCONFIRMED**. Release version: the driver is in master; which stable release includes it is UNCONFIRMED. |
| Benewake TF-Luna | 5 g (AP wiki) | 0.20-8 m | UART (`TYPE=27`) or I2C (`TYPE=25`, address 0x10) | not checked | 3.7-5.2 V |
| Benewake TF-Nova | 5 g (AP wiki) | 0.14-7 m, 14 degree field of view | UART (`TYPE=27`) or I2C (`TYPE=25`) | not checked | The wider beam suits obstacle sensing |
| Benewake TFmini-S | 5 g (AP wiki) | 12 m indoor / 7 m outdoor | UART (`TYPE=20`) or I2C (`TYPE=25`) | not checked | |
| ST VL53L1X breakout | **UNCONFIRMED** (Pololu and Holybro pages unreachable) | 4 m; AP wiki recommends `RNGFNDx_MAX=3.6` | I2C, **`TYPE=16`** (VL53L0X or VL53L1X) or `28` (VL53L1X short range), address 0x29 | not checked | AP wiki: **range is significantly reduced in bright sunlight, so not recommended outdoors**. The ArduPilot driver skips its reset step on a non-default address but does not assign addresses itself. All VL53L1X power up at 0x29, so several on one bus need external address handling. |
| Nooploop TOFSense-F (I2C) | not checked | up to 15 m (F) / 25 m (FP) | `TYPE=40`; address = 0x08 + ID, with the ID set in NAssistant | not checked | Per-sensor IDs are documented, so several sensors can share one bus. |
| VL53L4CD / VL53L5CX / VL53L7CX | n/a | n/a | **No ArduPilot RNGFND_TYPE exists** (checked the AP_RangeFinder_Params source). Would need Lua scripting or a companion computer. | | |

---

## 5. ExpressLRS (ELRS) receiver with MAVLink telemetry, plus handset

**MAVLink mode:**
- ELRS 3.5.0 added native "MAVLink-RC". It carries MAVLink telemetry (Mission Planner, parameter changes, missions) and RC over one link, and the backpack can forward MAVLink over WiFi. Flash both the TX and RX (IntoFPV release notes).
- AP wiki (`common-crsf-telemetry`, `common-rc-systems`): ELRS can output CRSF, SBUS or MAVLink with RC embedded. Telemetry needs a full UART.
- A worked ArduPilot setup (Unmanned Tech blog) uses: receiver link mode MAVLink, flight-controller UART set to MAVLink2 at 460800, `RSSI_TYPE=5`, backpack WiFi, Mission Planner on UDP 14550.
- The expresslrs.org MAVLink page could not be fetched, so ELRS-side parameter names are **UNCONFIRMED** beyond the above.

| Model | Mass | Size | Chip | Price / retailer / stock |
|---|---|---|---|---|
| **RadioMaster RP1 V2** | **2.2 g including antenna** (maker) | 13 x 11 x 3 mm | ESP8285 + SX1281, temperature-compensated crystal oscillator (TCXO), 10 mW telemetry | **$18.99, RadioMaster, listed available** |
| RadioMaster XR1 Nano (2.4 GHz antenna version) | 1 g **without antenna** (Motion RC) | 20 x 13 x 3 mm | ESP32-C3 + LR1121 (2.4 GHz and sub-GHz) | $15.99 RaceDayQuads (stock not shown) |
| BetaFPV ELRS Lite (flat antenna V1.2) | 0.46 g (BetaFPV); 0.53 g for V1.1 (GetFPV) | 11 x 10 x 3 mm | ESP8285, 17 mW telemetry | $8.99 BetaFPV (stock count invalid); V1.1 back-ordered at GetFPV |

Whether each receiver's MCU supports ELRS MAVLink mode is **UNCONFIRMED** for every receiver above.

**Handset / backpack** (ground side, not part of the airframe mass):
- **RadioMaster Ranger Nano**: $39.99 RadioMaster, listed available. Built-in ELRS backpack on ESP32 + ESP8285 with WiFi and Bluetooth. 39 g. Fits a Nano module bay.
- **RadioMaster Boxer**: "built-in ExpressLRS Backpack". $159.99, **Sold out** at RadioMaster.
- **RadioMaster Pocket**: has a Nano bay and an internal ELRS module up to 250 mW. Backpack not stated. €78.49 at Rotorama, "on the way". US price UNCONFIRMED.

---

## 6. Companion computer

| Board | Mass | Price / stock | Compute | Camera | Status |
|---|---|---|---|---|---|
| **Raspberry Pi Zero 2 W** | **10.0 g** (Adafruit) | **$19.05 Adafruit, Out of stock**; $19.00 SparkFun, **Out of stock**, limit 1 per customer. PiShop and CanaKit were unreachable (UNCONFIRMED). | BCM2710A1, 4x Cortex-A53 at 1 GHz, 512 MB (Core Electronics). No neural processing unit (NPU). | CSI-2 | 65 x 30 x 5.3 mm |
| Radxa ZERO 3W | UNCONFIRMED | UNCONFIRMED | RK3566, 4x Cortex-A55 at 1.6 GHz, 1-8 GB (Radxa docs). NPU not stated in Radxa's spec table (UNCONFIRMED). | 1x 4-lane MIPI CSI | Same 65 x 30 mm footprint as the Pi Zero |
| Luckfox Pico Ultra / Ultra W | UNCONFIRMED | UNCONFIRMED | RV1106 (Luckfox SDK board list); NPU TOPS UNCONFIRMED | UNCONFIRMED | |
| OpenMV AE3 / N6 | UNCONFIRMED | UNCONFIRMED | AE3: Alif E3 with dual Ethos-U55 NPUs, "YOLO at 30 FPS at 0.25 W", built-in 8x8 distance sensor. N6: STM32N6 with 600 GOPS NPU (OpenMV README). | AE3: 1 MP global shutter, built in | Microcontroller camera; ArduPilot documents OpenMV as a MAVLink flow source (`FLOW_TYPE=5`). |
| OpenMV RT1062, Milk-V Duo S, ESP32-S3 boards | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | Not verified today |

**Connection to ArduPilot** (AP dev wiki `raspberry-pi-via-mavlink`): wire TX, RX and GND to a free flight-controller UART. Set `SERIALx_PROTOCOL=2` (MAVLink2) and `SERIALx_BAUD=921` (921600). Run MAVProxy or mavlink-router on `/dev/serial0`.

**For the follow behaviour** (AP wiki `follow-mode`): set `FOLL_ENABLE=1` and `FOLL_SYSID` to the lead device's MAVLink system id. Use `FOLL_OFS_X/Y/Z` with `FOLL_OFS_TYPE` for the offset and `FOLL_YAW_BEHAVE` to face the subject. Follow mode uses `GLOBAL_POSITION_INT` or, preferably, `FOLLOW_TARGET` from the lead device.

---

## 7. Remote ID (reference only; not needed for recreational flight under 250 g)

- The AP wiki lists ArduPilot-compatible modules, including Holybro Remote ID, BlueMark DroneBeacon MAVLink and FPV, Dronetag, Cube ID and Aerobits idME.
- **ArduRemoteID** firmware runs on ESP32-S3 and ESP32-C3 dev boards. It connects by serial MAVLink or DroneCAN (ArduRemoteID README).
- **Masses and prices for all Remote ID modules are UNCONFIRMED.** The Holybro and BlueMark pages were unreachable today.

---

## Recommended set

Design choice: one 25.5 mm H7 AIO with 7 UARTs, 1 I2C bus and an ArduPilot hwdef in master, plus the lightest verified sensors that are in stock or nearly so.

**Port plan.** It assumes the AIO v2 uses the `MicoAir743v2` UART mapping, which is UNCONFIRMED for the AIO:

| Port | Use |
|---|---|
| UART6 | ELRS receiver (MAVLink mode) |
| UART3 | GPS |
| UART1 | Raspberry Pi Zero 2 W, MAVLink2 at 921600 |
| UART4 | MTF-01, MAVLink1 at 115200, forwarding off |
| UART2, UART5 | Spare (DisplayPort / video transmitter) |
| I2C | GPS compass + TFS20-L forward sensor |

| Part | Mass g | Price USD | Supplier | Stock (2026-10-26) | Source |
|---|---|---|---|---|---|
| MicoAir H743 v2 AIO 35A (FC + 4-in-1 ESC), ArduPilot target `MicoAir743v2` (retailer-stated, UNCONFIRMED by maker) | 10 | 87.99 | Pyrodrone | In stock | https://pyrodrone.com/products/micoair-h743-v2-aio-flight-controller-35a-2-6s-4in1-esc-25-25mm |
| Flywoo GOKU GM10 Nano V3 GPS w/ compass | 2.6 | 20.99 | Flywoo | UNCONFIRMED (page shows "Sold Out" and "Only 750 left") | https://www.flywoo.net/products/goku-gm10-nano-v3-gps-w-compass |
| MicoAir MTF-01 optical flow + 8 m ToF | 4.5 | 32.99 | Pyrodrone | In stock | https://pyrodrone.com/collections/micro-drones-accessories/products/micoair-mtf-01-optical-flow-8m-range-2in1-sensor |
| Benewake TFS20-L (forward), I2C, `RNGFND2_TYPE=46`, `ORIENT=0`, `PRX1_TYPE=4` | 2 (AP wiki; RobotShop says 1.35) | 53.84 | RobotShop | UNCONFIRMED | https://www.robotshop.com/es/products/benewake-tfs20-l-mini-single-point-lidar-module |
| RadioMaster RP1 V2 ELRS receiver (MAVLink mode) | 2.2 (with antenna) | 18.99 | RadioMaster | Listed available | https://radiomasterrc.com/collections/receivers/products/rp1-expresslrs-2-4ghz-nano-receiver |
| Raspberry Pi Zero 2 W | 10.0 | 19.05 | Adafruit | **Out of stock** (SparkFun also out) | https://www.adafruit.com/product/5291 |
| **Airborne total (listed parts only)** | **31.3** | **233.85** | | | |
| Optional: 2 more TFS20-L for left/right (`ORIENT=6/2`), only if I2C addresses can be changed (UNCONFIRMED) | +4 | +107.68 | RobotShop | UNCONFIRMED | as above |
| Ground side: RadioMaster Ranger Nano (ELRS TX with ESP32 WiFi backpack), needs a Nano-bay radio | (ground) | 39.99 | RadioMaster | Listed available | https://www.radiomasterrc.com/products/ranger-nano-2-4ghz-elrs-module |

**Not included in the 31.3 g:**
- wiring, connectors and solder (ESTIMATE: a few grams; no number checked)
- the vlog/companion camera and its ribbon cable
- battery, motors, frame and ducts
- a 5 V supply for the Pi (the AIO's own BEC ratings were not confirmed today)

**Fallbacks:**
- If the MicoAir v2 AIO's ArduPilot target turns out wrong: **NxtPX4v2** (20x20, 6.5 g, $71.99, in stock, documented target) plus a separate 20x20 ESC, or the Flywoo GN745 V3 AIO (9.4 g, in stock at GetFPV, F7).
- If the GM10 Nano's small antenna gives poor fixes: GM10 Mini V3 (4.1 g) or HGLRC M100-5883 (7.73 g).

---

## Open items / unknowns
1. **ArduPilot target for the MicoAir H743 v2 AIO.** Only the retailer (Unmanned Tech UK) names `MicoAir743v2`. The ArduPilot wiki page for MicoAir743v2 describes the 30x30 board (8 UARTs with Bluetooth on UART8), while the AIO page says UART1-6 and UART8. Confirm the pad mapping before wiring.
2. Whether the TFS20-L I2C address can be changed and stored on the sensor. This decides whether 3 can share one bus. Also which ArduPilot stable release includes `RNGFND_TYPE=46`.
3. Whether each receiver's MCU (ESP8285 vs ESP32-C3) supports ELRS MAVLink mode. Exact ELRS-side settings (expresslrs.org was unreachable).
4. Raspberry Pi Zero 2 W US stock: out at Adafruit and SparkFun; PiShop, CanaKit and Amazon not checked.
5. Mass, price and NPU figures for Radxa ZERO 3W, Luckfox Pico Ultra/Max, Milk-V Duo S, OpenMV RT1062 and ESP32-S3 boards.
6. Remote ID module masses (Holybro, BlueMark, ArduRemoteID on ESP32-C3).
7. Peak motor current for 1404-1505 motors on 4S against the 35A ESC.
8. Firmware feature inclusion for the chosen target. `features.txt` on firmware.ardupilot.org was not reachable. This matters most on F405 boards (1 MB flash).

---

## Sources (all seen 2026-10-26)

| URL | Supports |
|---|---|
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-autopilots.rst | ArduPilot autopilot list; Kakute H7 Mini under "Discontinued Boards"; MicoAir, Flywoo, SpeedyBee, NxtPX4v2 entries |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-MicoAir743-AIO.rst | MicoAir743-AIO specs, UARTs, bidirectional DShot, target name |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-MicoAir743v2.rst | MicoAir743v2 UART map, 8 UARTs, Bluetooth, target name |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-NxtPX4v2.rst | NxtPX4v2 20x20 mount, 6.5 g, 7 UARTs |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-holybro-kakuteh7mini.rst | "v1.5 has been unavailable since mid 2025" |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-speedybeef405aio.rst | SpeedyBee F405 AIO specs, 13.6 g, target `SpeedyBeeF405AIO` |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-speedybeef405-mini.rst | SpeedyBee F405 Mini (stack, 9.6 g, flash-limited) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-flywoo-f745.rst | Flywoo GN745 AIO V3: 45A, 9.4 g, 7 UARTs |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-betafpvf405.rst | BetaFPV F405 AIOs (20A, limited to ACRO/STABILIZE/ALTHOLD) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743v2/hwdef.dat | hwdef exists; IMUs, SPL06 barometer, serial order |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743-AIO/hwdef.dat | hwdef exists; DPS310 barometer, serial order |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_HAL_ChibiOS/hwdef/MicoAir743-Lite/README.md | MicoAir743-Lite is 30.5 mm, 10 g (not whoop size) |
| https://micoair.com/flightcontroller_micoair743_aio_35a/ | MicoAir743-AIO-35A specs; "Discontinued" |
| https://micoair.com/flightcontroller_micoair743v2_aio_35a/ | v2 AIO specs (10 g, 25.5 mm, 2-6S, Bluejay 35A, 7 UARTs); ArduPilot sections; PX4 build names |
| https://www.unmannedtechshop.co.uk/products/micoair743v2-aio-h743-flight-controller-45a-blheli_s-esc-3-6s | Retailer states ArduPilot target `MicoAir743v2`; £67.99, sold out |
| https://pyrodrone.com/products/micoair-h743-v2-aio-flight-controller-35a-2-6s-4in1-esc-25-25mm | $87.99, in stock, 10 g, 35A continuous, Bluejay 0.19.2 |
| https://pyrodrone.com/products/micoair-h743-v2-aio-45a-am32-2-6s-flight-controller-esc-25-25mm | 45A version $104.99, sold out |
| https://pyrodrone.com/collections/micoair-products/brand_micoair | Prices and stock for MicoAir parts (NxtPX4v2 $71.99, MTF-01 $32.99, MTF-01P $41.99, MTF-02P $21.99 sold out) |
| https://rotorvillage.ca/micoair-h743-aio-35a-am32/ | MicoAir743-AIO: 35A continuous, AM32 2.12, ArduPilot from 4.6 |
| https://pyrodrone.com/collections/whoop-style-aio-flight-controllers/products/speedybee-f405-40a-bluejay-3-6s-aio-flight-controller-esc-25-5x25-5mm | SpeedyBee F405 AIO: $71.99, sold out, 40A/45A |
| https://www.racedayquads.com/products/speedybee-f405-v2-aio-f405-fc-40a-3-6s-bluejay-esc-25-5x25-5 | SpeedyBee F405 V2 AIO $92.49 |
| https://www.getfpv.com/flywoo-goku-gn745-v3-aio-f7-fc-45a-2-6s-am32-4-in-1-esc-mpu6000-25x25.html | GN745 V3: in stock, 9.4 g, 45A, 7 UARTs, ICM42688 change |
| https://openelab.io/products/holybro-kakute-h7-mini-v15 | Kakute H7 Mini: 5.5 g, 20x20, sold out |
| https://www.flyingtech.co.uk/product/holybro-kakute-h7-mini-20x20-flight-controller/ | Kakute H7 Mini sold out |
| https://flywoo.net/blogs/blog/flywoo-goku-gm10-gps-buyer's-guide-2026 | GM10 variant sizes, masses, QMC5883L |
| https://www.flywoo.net/products/goku-gm10-nano-v3-gps-w-compass | GM10 Nano V3: $20.99, 2.6 g, contradictory stock |
| https://www.racedayquads.com/products/flywoo-goku-gm10-nano-v3-micro-gps-w-compass-10th-gen | $25.49, 2.8 g |
| https://www.getfpv.com/flywoo-goku-gm10-mini-v3-gps-w-compass.html | GM10 Mini V3: 4.1 g |
| https://wrekd.com/products/hglrc-m100-5883-micro-gps-w-compass-10th-gen | HGLRC M100-5883: 7.73 g, 21x21x8.02 mm, $16.99 backorder |
| https://racedayquads.com/products/hglrc-m100-5883-gps-module-10th-gen | HGLRC M100-5883 $20.49 |
| https://www.getfpv.com/mateksys-m10q-5883-gnss-compass.html | Matek M10Q-5883: 8 g, 20x20x12.4 mm, $51.99, out of stock |
| https://www.racedayquads.com/products/matek-m10q-5883-gnss-compass | $47.99 |
| https://holybro.com/products/micro-m10-gps/ | Holybro Micro M10: 14/16 g, $27.99, stock |
| https://www.getfpv.com/holybro-micro-m10-gps-w-case.html | $36.49, in stock |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-mtf-01.rst | MTF-01 ArduPilot setup (FLOW_TYPE 5, RNGFND1_TYPE 10, options) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-mateksys-optflow-3901L0X.rst | 3901-L0X setup (FLOW_TYPE 7, RNGFND 32), outdoor warning |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-optical-flow-sensors-landingpage.rst | Supported flow sensors list |
| https://pyrodrone.com/collections/micro-drones-accessories/products/micoair-mtf-01-optical-flow-8m-range-2in1-sensor | MTF-01 specs, $32.99, in stock |
| https://micoair.com/optical_range_sensor_mtf-02/ | MTF-02: 4.5 g, 25x10x4.5 mm |
| https://rotorvillage.ca/micoair-mtf-02p-optical-flow-6m-range-lidar/ | MTF-02P: 1.8 g, 6 m/4 m |
| https://www.rotorama.com/product/micoair-mtf-01p-optical-flow-a-range-sensor | MTF-01P: 8 g, 12 m |
| https://www.getfpv.com/mateksys-optical-flow-lidar-sensor-3901-l0x.html | 3901-L0X: 2 g, $38.99, out of stock |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-rangefinder-setup.rst | Up to 10 rangefinders; 8 + 1 for avoidance; PRXx_TYPE = 4 |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-simple-object-avoidance.rst | AVOID_ENABLE = 7, PRX1_TYPE = 4, modes |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-proximity-landingpage.rst | Up to 4 proximity sensors; PRX logging |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-benewake-tf02-lidar.rst | TFS20-L, TF-Luna, TF-Nova masses, ranges, types 27/25/46 |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-benewake-tfmini-lidar.rst | TFmini-S/Plus range and mass, types 20/25 |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-vl53l0x-lidar.rst | VL53L0X/L1X type 16, ranges, sunlight warning |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-rangefinder-nooploop-tofsense-f.rst | TOFSense-F type 40, ID-based I2C addressing |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_RangeFinder/AP_RangeFinder_Params.cpp | Full RNGFND_TYPE list (no VL53L4/L5/L7) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_RangeFinder/AP_RangeFinder_Benewake_TFS20L.h | TFS20-L default I2C address 0x10 |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_RangeFinder/AP_RangeFinder_VL53L1X.cpp | VL53L1X non-default address handling |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_Proximity/AP_Proximity_Params.cpp | PRX_TYPE values (4 = RangeFinder) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot/master/libraries/AP_OpticalFlow/AP_OpticalFlow.cpp | FLOW_TYPE values |
| https://www.robotshop.com/es/products/benewake-tfs20-l-mini-single-point-lidar-module | TFS20-L: $53.84, 1.35 g, 20 m / 15 m at 100 klux |
| https://probots.co.in/benewake-tfs20-l-miniaturized-lidar-distance-sensor-20m-uart-i2c.html | TFS20-L: 2 degree field of view, 0-250 Hz, 3.3 V |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-crsf-telemetry.rst | ELRS MAVLink mode note |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-rc-systems.rst | ELRS can output MAVLink; needs full UART |
| https://intofpv.com/t-expresslrs-3-5-0-final-release-now-available | ELRS 3.5.0 MAVLink-RC, backpack MAVLink via WiFi |
| https://blog.unmanned.tech/elrs-mavlink-tx-as-rx-one-radio/ | ArduPilot ELRS MAVLink setup example (MAVLink2 at 460800, RSSI_TYPE = 5, UDP 14550) |
| https://radiomasterrc.com/collections/receivers/products/rp1-expresslrs-2-4ghz-nano-receiver | RP1 V2: 2.2 g, $18.99, ESP8285 |
| https://www.unmannedtechshop.co.uk/products/radiomaster-rp1-v2-elrs-receiver | RP1 V2: 2.2 g, 13x11x3 mm |
| https://motionrc.com/products/radiomaster-xr1-nano-multi-frequency-2-4ghz-antenna-elrs-receiver-hp0157-xr1-2400 | XR1: 1 g without antenna, ESP32-C3, LR1121 |
| https://racedayquads.com/products/radiomaster-xr1-nano-multi-frequency-receiver-elrs-2-4ghz | XR1: $15.99 |
| https://betafpv.com/collections/expresslrs-series-accessories/products/elrs-lite-receiver | ELRS Lite: 0.46 g, $8.99 |
| https://www.getfpv.com/betafpv-elrs-lite-v1-1-2-4ghz-receiver-w-flat-antenna.html | ELRS Lite V1.1: 0.53 g, back-ordered |
| https://www.radiomasterrc.com/products/ranger-nano-2-4ghz-elrs-module | Ranger Nano: $39.99, ESP32 backpack WiFi/Bluetooth |
| https://www.radiomasterrc.com/products/boxer-radio-transparent-version | Boxer: $159.99, sold out, built-in backpack |
| https://www.rotorama.com/product/radiomaster-pocket-elrs | Pocket: 250 mW, Nano bay, €78.49 |
| https://www.adafruit.com/product/5291 | Pi Zero 2 W: $19.05, out of stock, 10.0 g, 65x30x5.3 mm |
| https://www.sparkfun.com/raspberry-pi-zero-2-w.html | $19.00, out of stock, limit 1 |
| https://core-electronics.com.au/raspberry-pi-zero-2-w-wireless.html.md | BCM2710A1, 512 MB, CSI-2 |
| https://raw.githubusercontent.com/radxa-docs/docs/main/i18n/en/docusaurus-plugin-content-docs/current/zero/zero3/README.md | Radxa ZERO 3W: RK3566, MIPI CSI, 65x30 mm |
| https://raw.githubusercontent.com/LuckfoxTECH/luckfox-pico/main/README.md | Luckfox Pico Ultra/Ultra W use RV1106 |
| https://raw.githubusercontent.com/openmv/openmv/master/README.md | OpenMV N6 / AE3 NPU claims |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/dev/source/docs/raspberry-pi-via-mavlink.rst | Pi to flight controller UART MAVLink2 at 921600 |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-openmv-optflow.rst | OpenMV as MAVLink flow sensor |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/copter/source/docs/follow-mode.rst | Follow mode parameters (FOLL_*) |
| https://raw.githubusercontent.com/ArduPilot/ardupilot_wiki/master/common/source/docs/common-remoteid.rst | ArduPilot-compatible Remote ID modules list |
| https://raw.githubusercontent.com/ArduPilot/ArduRemoteID/master/README.md | ArduRemoteID on ESP32-S3/C3 |
