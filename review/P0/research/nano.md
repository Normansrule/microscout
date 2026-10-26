> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate. Research notes compiled on 2026-10-26 from the sources listed at the end; items not checked against a primary source are marked UNCONFIRMED.

# Wisp Nano: Crazyflie-class platform research

Seen: 2026-10-26. Prices are USD unless marked. "Bitcraze" means store.bitcraze.io (its product pages say "USD"; collection pages show only "$"). Stock was read from the page text on 2026-10-26. A page with only an "Add to Cart" button and no stock label is listed as "no label". The Digi-Key, Mouser, Seeed Studio direct and Amazon US listings could not be found or read: **UNCONFIRMED** (the search budget ran out before they could be retried).

Labels used below:
- **ESTIMATE**: my number, not published anywhere.
- **DERIVED**: arithmetic on published numbers.
- **UNCONFIRMED**: I could not verify it.

---

## 1. Crazyflie platforms and bundles

### 1.1 Airframes

| Model | Status | Takeoff mass | Max recommended payload | Flight time (stock battery) | Stock battery | Bitcraze price | RobotShop US price / stock | Part numbers |
|---|---|---|---|---|---|---|---|---|
| **Crazyflie 2.1+** (brushed, 7 mm coreless motors, 47-17 props) | Current | 29 g | 15 g | 7 min (charge 40 min) | 250 mAh LiPo, 7.1 g | $240.00, no label | $240.00, **"In stock, 9 units"** | Bitcraze SKU 114993491; RobotShop RB-Bcz-16 |
| Crazyflie 2.1+ (Seeed-branded listing on RobotShop) | Current | 27 g (as listed by RobotShop) | 15 g | 7 min | 250 mAh | n/a | $240.00, "On Demand item … not normally stocked" | Mfr 114993295; RB-See-1133 |
| **Crazyflie 2.1 Brushless** (08028-10000KV motors, 55-35 props, BLHeli_S/Bluejay 5 A ESCs, 100 mm frame) | Current | 34 g with legs / 37 g with guards (the intro text says 32 g) | **40 g** | 10 min (charge 60 min) | 350 mAh LiPo | $480.00, no label | $480.00, **"Re-stocking soon"** (notify-me button shown) | Bitcraze SKU 100060743; RobotShop RB-Bcz-10 |
| Crazyflie 2.1 (non-plus) | **Discontinued**. Bitcraze, Aug 2024: "we will discontinue the Crazyflie 2.1 as the Crazyflie 2.1+ replaces the 2.1" | n/a | n/a | n/a | n/a | not listed | n/a | n/a |
| Crazyflie 2.0 | **Discontinued**: "replaced with Crazyflie 2.1+" (max takeoff weight 42 g) | n/a | n/a | n/a | n/a | not listed | n/a | n/a |

Notes:
- Thrust: the Brushless motors give "up to 30 grams thrust each", so about 120 g in total. The datasheet and Bitcraze page for the 2.1+ give **no** thrust figure.
- Battery included in takeoff mass: the firmware source (`platform_defaults_cf21bl.h`, master 2026-10-22) says *"The Crazyflie 2.1 Brushless with propeller guards, 350mAh battery, and Lighthouse deck weights 39.3g."* 39.3 − 2.7 (Lighthouse deck) = 36.6 g, which is close to the published 37 g with guards. So the 37 g figure **includes the 350 mAh battery** (DERIVED). For the 2.1+, the firmware default `CF_MASS` is 0.029 kg, the same as the 29 g takeoff weight. I take that figure to include the stock battery, but Bitcraze does not say so explicitly (**UNCONFIRMED**).
- Thrust upgrade kit for the 2.1+ / 2.X: 4 × 7×20 mm motors. Bitcraze sells the motor pack for $15 and the "Thrust upgrade bundle" for $16; RobotShop sells the bundle for $19.28. RobotShop says it "Enhances thrust by 20 grams", "Reduces flight time by 15%". The firmware mass constant for this configuration is 32.5 g. No payload figure is published (**UNCONFIRMED**).
- Brushless deck compatibility (Bitcraze): "Fully compatible with the Crazyflie 2.X ecosystem (except LED-ring)".
- US import context (not drone-specific to Bitcraze):
  - On 2025-12-22 the FCC put foreign-made drones and their critical components on the Covered List. This blocks *new* equipment authorizations only; models authorized earlier can still be imported and sold.
  - A 2026-08-13 proclamation adds a 25% tariff on small drones from 2027-02-09; the rate is 15% for EU-origin hardware that qualifies.
  - The FCC authorization status of the Crazyflie models is **UNCONFIRMED**. Both are listed for sale in the US by RobotShop today.

### 1.2 Bundles (Bitcraze store, sale price shown first, struck list price in brackets)

| Bundle | Price | Stock label | Contents |
|---|---|---|---|
| Getting started – 2.1+ | $270 ($285) | none | CF 2.1+ + Crazyradio (from Generation Robots' listing of the same bundle) |
| STEM drone – 2.1+ | $320 ($338) | none | CF + Crazyradio + Flow deck v2 (Bitcraze tutorial) |
| **STEM ranging – 2.1+** | **$410** ($433) | none | The list price equals CF 2.1+ $240 + Flow $55 + Multi-ranger $95 + Crazyradio $43 = $433. Contents inferred from that sum, **UNCONFIRMED** |
| The AI bundle – 2.1+ | $610 ($648) | **Temporarily out of stock** | RobotShop EU lists CF 2.1+, Flow deck, AI deck 1.1, Crazyradio 2.0. Those items cost $578 bought separately, so the bundle may include more items: **UNCONFIRMED** |
| Getting started – Brushless | $500 ($523) | none | n/a |
| STEM – Brushless | $550 ($578) | none | n/a |
| **STEM ranging – Brushless** | **$640** ($673) | none | CF Brushless, Flow v2, Multi-ranger, Crazyradio 2.0. Confirmed by Generation Robots (EUR 822 incl. VAT, "2 Available") and by the sum $480 + 55 + 95 + 43 = $673. RobotShop US: $735.25, stock not shown |
| The AI bundle – Brushless | $830 ($888) | **Temporarily out of stock** | n/a |
| Lighthouse explorer – 2.1+ / Brushless | $810 / $1,050 | none | n/a |
| Infinite flight – Brushless (new) | $1,075 ($1,138) | none | CF Brushless, Crazyradio 2.0, charging dock, Lighthouse deck, 2 × Lighthouse V2 base stations |
| Loco explorer – 2.1+ / Brushless | $1,720 / $1,950 | none | n/a |
| Happy hacker – 2.1+ / Brushless | $315 / $540 | none | n/a |

Kit contents:
- **2.1+**: board, 250 mAh battery, 5 motors (1 spare), 6 mounts, 10 props, battery holder deck, 2 short + 2 long male deck connectors, micro-USB cable.
- **Brushless**: board, 350 mAh battery, battery holder, 5 guards, 5 legs, 4 motors, screws, 10 props, 2 short + 2 long deck connectors, USB cable, screwdriver, prop tool.

Both kits fly with the stock client, so same-day flight is realistic. The Brushless needs screw assembly.

---

## 2. Decks

Masses and pin usage come from the Bitcraze product pages and the expansion-deck compatibility page. Stock column: Bitcraze label / RobotShop US text.

| Deck | Mass | Mount | Bus / pins | Current | Bitcraze price | RobotShop US price / stock | Part no. |
|---|---|---|---|---|---|---|---|
| **Flow deck v2** (VL53L1x ToF + PMW3901 flow, 4 m range) | 1.6 g | bottom | I2C, SPI + CS (IO), VCC | ~40 mA | $55, no label | $63.39, **"In stock, 5 units"** | Mfr 114991549 (RB-See-882) |
| **Multi-ranger** (5 × VL53L1x: front, back, left, right, up; 4 m) | 2.3 g | top | I2C, VCOM | ~90 mA | $95, no label | $114.04, stock not shown | 114991485 (RB-Bcz-05) |
| **AI deck 1.1** (GAP8 8+1-core RISC-V, 512 Mbit HyperFlash, 64 Mbit HyperRAM, ESP32 NINA-W102 WiFi, Himax HM01B0 320×320 mono camera) | 4.4 g | top or bottom | UART1 (GAP8), UART2 (ESP32/CPX), I2C, BOOT (IO_1), RST (IO_4), VCOM; 3–5 V up to 300 mA | app-dependent | $240, **Temporarily out of stock** | $308.02, **"Only 2 units left"** | 114992445 (RB-Bcz-11) |
| Lighthouse positioning | 2.7 g | top | UART1, optional I2C | ~40 mA | $95, no label | not checked | n/a |
| Loco positioning (UWB) | 3.3 g | top or bottom | SPI + CS, UART1 pins (IRQ/RST), VCOM | ~160 mA | $95, no label | not checked | n/a |
| Z-ranger v2 | 1.6 g (the compatibility table says 1.3 g) | bottom | I2C, VCC | ~15 mA | **Discontinued**: "We recommend using the Flow Deck v2 instead" | n/a | n/a |
| LED-ring | 3.3 g | bottom | IO2/IO3 PWM, VCOM | 0–700 mA | $23, no label | n/a | n/a |
| Color LED deck (top or bottom, new) | 3.5 g with diffuser | top / bottom | I2C, VCOM | up to ~300 mA per channel | $23 each | n/a | n/a |

Batteries:

| Battery | Mass | Spec | Bitcraze price | RobotShop US price |
|---|---|---|---|---|
| 250 mAh LiPo | 7.1 g | 20×7×30 mm, 15C, Molex 51005 | $6.50 (or $10.50 with 500 mA charger) | n/a |
| 350 mAh LiPo | 9.1 g | 20×8×33 mm, 15C continuous / 30C burst | $12.00 (SKU 114993131) | $16.37 (RB-Bcz-18), stock not shown |

- The 350 mAh pack is thicker and needs 9 mm pin headers on brushed frames (Bitcraze blog, 2023-10).
- The Brushless ships with a 350 mAh battery. Whether that is the same 9.1 g pack: **UNCONFIRMED**.
- No separate "brushless battery" product is listed in the store.
- Positioning infrastructure: Lighthouse V2 base station $240 each. Loco positioning node $180 each; the minimum node count was not checked (**UNCONFIRMED**).

### 2.1 Compatibility (Bitcraze compatibility matrix)

- **Flow + Multi-ranger + AI deck: compatible.**
  - Multi-ranger is marked compatible with every deck.
  - The AI deck is only "conditional" with Micro SD, Loco, BigQuad, Buzzer and Lighthouse.
  - Flow is incompatible with LED-ring, Qi, BigQuad and Z-ranger, which all compete for the bottom position.
- **Lighthouse + AI deck: conditional.** Both use UART1 ("The GAP8 module is connected to UART1, so if that is enabled there will be conflicts"). It can be re-routed with solder bridges or 0 Ω resistors.
- **Loco + AI deck: conditional** (patch or workaround). Loco + Lighthouse: conditional.
- **AI deck + Buzzer/BigQuad**: UART2 conflict (CPX).
- **AI deck + Micro SD**: IO4 conflict.
- **Flow / Loco + Micro SD**: SPI sharing slows SD logging.
- **Brushless**: LED-ring not compatible. The LED-ring page says it needs a software modification.
- **Stacking rules**:
  - "There should always be one expansion board or battery holder on top to secure the battery."
  - Long pins are needed for 3 decks: "two on top and one below, or one on top and two below".
  - When the AI deck is mounted underneath, use the 15+4+6 mm long pins with the wider spacer.
  - **UNCONFIRMED**: whether the AI deck's forward-protruding 52 mm board or its camera blocks the Multi-ranger's front sensor when both are stacked on top. Test this on the bench.

### 2.2 AI deck tracking: what exists

- **Official GAP8 examples** (bitcraze.io aideck-gap8-examples):
  - Classification Demo
  - Face detection: runs on the GAP8 and streams over WiFi to `opencv-viewer.py`; max stream 324×244; "white background and dark hair work better"
  - Hello World
  - NanoCockpit
  - UART, CPX and Himax camera test
  - WiFi Video Streamer

  None of the official examples closes the flight loop. There is **no official person-following demo**.
- **Toolchain blocker (important)**:
  - The face detection docs say the GAP8 Autotiler "can no longer be downloaded" because GreenWaves went into liquidation in 2025.
  - Bitcraze GitHub discussion #1854 (opened 2025-03-20): neural-network examples that rely on the Autotiler "will not work". Bitcraze is "focusing our efforts on the DORY solution" (2026-01-19).
  - Promised NanoCockpit + DORY examples were still unreleased as of the last comment (2026-05-27).
  - So the WiFi streamer and non-NN examples are usable. Onboard NN tracking needs DORY, or an Autotiler you already have.
- **Research demo of tracking**: PULP-Frontnet (arXiv 2103.10873). It runs fully onboard the GAP8 and follows a person at about 1.3 m, at up to 134.7 fps and about 86.6 mW. The paper does not give a code URL.
- **NanoCockpit** framework paper: arXiv 2601.07476, 2026.
- **Practical Wisp Nano path** (my recommendation, not a Bitcraze claim):
  1. Stream 324×244 greyscale over WiFi.
  2. Detect and track off-board, e.g. OpenCV on the PC.
  3. Send setpoints over Crazyradio with cflib.

  Same-day AI tracking is **UNCONFIRMED / unlikely**: the GAP8 and ESP32 firmware must be flashed first.

---

## 3. Radio and host software

- **Crazyradio 2.0** (nRF52-based):
  - Bitcraze: $43.00 USD (SKU 114993492), no stock label.
  - RobotShop US: $49.44 (RB-Bcz-14), stock not shown.
  - Not compatible with custom Crazyradio PA firmware.
- **cflib 0.1.34** (PyPI, uploaded 2026-09-30): requires Python >=3.10, classifiers 3.10–3.13, Linux/macOS/Windows.
- **cfclient 2026.8.1** (PyPI, uploaded 2026-09-30): requires Python >=3.10, classifiers 3.10–3.13, PyQt6 ~6.7.1.
- **Tested here (2026-10-26) on Ubuntu 24.04.5 LTS, Python 3.12.3**:
  - `python3.12 -m venv` then `pip install cflib cfclient` installed cleanly.
  - `cflib.crtp.init_drivers()` ran.
  - The cfclient GUI module imported headless.
  - No radio hardware was attached, so a real link was **not tested**.
  - On 24.04, use a venv: system `pip3 install` is blocked by PEP 668. Bitcraze's STEM guide still says "tested on Ubuntu 22.04" with a global `pip3 install`.
- **Linux USB setup**: you need the `plugdev` group plus `/etc/udev/rules.d/99-bitcraze.rules`. The rules cover:
  - 1915:7777 (Crazyradio)
  - 1915:0101 (bootloader)
  - 0483:5740 (Crazyflie USB)

  Then run `udevadm control --reload-rules && udevadm trigger`, log out and log back in, and re-plug the radio.

---

## 4. Simulation (status as of 2026-10-26)

| Option | What it is | Real firmware? | Ubuntu 24.04 status | Activity (last commit) |
|---|---|---|---|---|
| **Bitcraze crazyflie-simulation** (Webots; Gazebo is WIP) | Webots PROTO with IMU, camera, multi-ranger, ground truth; keyboard and wall-following controllers; one controller wraps the firmware Python-binding PID | Partly (Python-binding PID) | Install Webots from Cyberbotics. Worlds are in R2023a format. The README says: "It's not actively maintained, and not very realistic in terms of dynamics." The Gazebo model "can only rotate the propellers" | 2026-03-19 |
| **Crazyswarm2 `backend:=sim`** (ROS 2) | SITL using auto-generated firmware Python bindings, with optional dynamics | Yes (bindings of controllers, estimator, planner) | **Officially supported: Ubuntu 24.04 / Python 3.12 / ROS 2 Jazzy** (also 22.04/Humble). Docs pin firmware tag 2025.02 for the bindings | 2026-09-11 |
| **Firmware Python bindings** (`cffirmware`) | Controllers (PID, Mellinger, Lee, Brescianini), Kalman core, planner, as Python bindings | Yes | **Built and imported here** on Ubuntu 24.04 + Python 3.12 from firmware master (2026-10-22) with `make cf2_defconfig && make bindings_python`. SWIG came from pip | 2026-10-22 (firmware) |
| **CrazySim** (SOARLabOSU/CrazySim, also gtfactslab; ICRA 2024) | Full firmware SITL + Gazebo Sim; cflib over `udp://0.0.0.0:19850`; works with Crazyswarm2; models `crazyflie` and `crazyflie_thrust_upgrade` | Yes (forked firmware) | README: Ubuntu ≥20.04, tested on 22.04 with Gazebo Garden (now EOL). The plugin CMake looks for gz-sim 8 or 7, so Harmonic on 24.04 should build, but this is **UNCONFIRMED** (not tested). Firmware fork is dated 2024-04-30, so it lags current firmware. No Brushless model. Flow and Multi-ranger simulation **UNCONFIRMED** | top-level 2024-05-31; sim submodule 2026-01-24 |
| sim_cf2 (CrazyflieTHI) | ROS 2 + Gazebo 11 SITL, simulated Multi-ranger | Yes | Ubuntu 22.04 / Humble / Gazebo Classic 11 only. Classic is EOL, so not a fit for 24.04 | 2024-03-23 |
| CrazyS `dev/ros2-jazzy` | Gazebo model of the Crazyflie with its controllers | No (own model) | **Ubuntu 24.04 + Jazzy + Gazebo Harmonic** branch | 2026-10-13 |
| crazyflow (utiasDSL) | JAX + MuJoCo, differentiable; good for control and RL | No | `pip install crazyflow`, Python 3.11+ | 2026-10-25 |
| gym-pybullet-drones | PyBullet Gym env of the CF 2.x | No | pip | 2026-10-16 |

Bitcraze also lists MuJoCo, Webots built-in, Isaac and an Rviz sim on its external-projects page.

**Recommendation for 24.04**:
- Control theory: firmware Python bindings plus your own dynamics, or crazyflow.
- Whole-system rehearsal: Crazyswarm2 sim on Jazzy.
- Gazebo SITL with the real cflib script path: CrazySim, but expect to patch it for Harmonic.
- Set `CF_MASS` (Kconfig `MODIFIED_CF_MASS`) to the measured Wisp Nano mass; the model-based controllers use it.

---

## 5. Recommended Wisp Nano configurations

The deck set is the same for both options:
- **Flow v2** on the bottom (hover hold).
- **AI deck 1.1** on top, first level (camera forward).
- **Multi-ranger** on top, second level (obstacle sensing).

This needs long pins, "two on top and one below". No battery holder deck is needed because a top deck retains the battery.

### Option A: brushed Crazyflie 2.1+

| Item | Mass (g) | Basis |
|---|---|---|
| Board + frame + motor mounts | 10.1 | **ESTIMATE** (remainder) |
| 4 × 7 mm coreless motors | 10.8 | **ESTIMATE** (about 2.7 g each; not published) |
| 4 × 47-17 props | 1.0 | **ESTIMATE** |
| *Subtotal: airframe without battery* | *21.9* | DERIVED (29 − 7.1) |
| 250 mAh battery | 7.1 | datasheet |
| *Stock takeoff mass* | *29.0* | Bitcraze |
| Flow deck v2 | 1.6 | Bitcraze |
| Multi-ranger | 2.3 | Bitcraze |
| AI deck 1.1 | 4.4 | Bitcraze |
| Extra long pin headers | 0.5 | **ESTIMATE** |
| Battery holder deck removed | −? | **UNCONFIRMED** (mass not published; ignored, conservative) |
| **Total takeoff mass** | **≈37.8** (37.3 without the pin estimate) | DERIVED |
| Payload used vs limit | 8.8 of 15 g (≈6 g margin) | **inside the published limit** |
| Variant with 350 mAh battery | ≈39.8 g, payload 10.8 of 15 g | inside the limit; needs 9 mm pins |

Cost (Bitcraze prices):

| Item | Price |
|---|---|
| STEM ranging bundle 2.1+ | $410 |
| AI deck 1.1 | $240 (out of stock at Bitcraze; RobotShop US $308.02, 2 left) |
| 2 × spare 250 mAh batteries | $13 |
| Long pins (15+4+6 mm) | $2 |
| **Total** | **$665** |

If the AI deck is bought from RobotShop US instead: about $733. Shipping and tax are extra and **UNCONFIRMED**. Buying everything from RobotShop US at single-item prices comes to about $240 + 63.39 + 114.04 + 308.02 + 49.44 = $774.89.

Flight time with this load is not published (**UNCONFIRMED**). Expect less than the stock 7 min.

### Option B: Crazyflie 2.1 Brushless (legs; guards add 3 g)

| Item | Mass (g) | Basis |
|---|---|---|
| Board + frame + props + legs + battery holder | 15.7 | DERIVED (34 − 9.1 − 9.2); the split between these parts is not published |
| 4 × 08028 brushless motors | 9.2 | 2.3 g each "with cable" (RobotShop UK listing) |
| 350 mAh battery | 9.1 | Bitcraze 350 mAh page; assumed to be the same pack (**UNCONFIRMED**) |
| *Stock takeoff mass, legs* | *34.0* | Bitcraze |
| Flow deck v2 | 1.6 | Bitcraze |
| Multi-ranger | 2.3 | Bitcraze |
| AI deck 1.1 | 4.4 | Bitcraze |
| Extra long pin headers | 0.5 | **ESTIMATE** |
| **Total takeoff mass, legs** | **≈42.8** (with guards ≈45.8) | DERIVED |
| Payload used vs limit | 8.8 of 40 g | **inside the published limit**, with large margin |
| Thrust-to-weight | ≈2.8 (120 g / 42.8 g) | DERIVED |

Cost (Bitcraze prices):

| Item | Price |
|---|---|
| STEM ranging bundle Brushless | $640 |
| AI deck 1.1 | $240 |
| 2 × spare 350 mAh batteries | $24 |
| Long pins | $2 |
| **Total** | **$906** |

Room for later additions: Lighthouse deck (+2.7 g, but UART1-conditional with the AI deck) or a charging dock ($40). Note that Option B exceeds the 40 g target mass; Option A meets it.

**Pick**:
- Option A if the 30–40 g target and price matter most. The airframe is in stock in the US today (RobotShop, 9 units).
- Option B for payload margin, thrust headroom for control experiments, and guards indoors. But the Brushless is "Re-stocking soon" at RobotShop US, and Bitcraze shows no stock label for it.
- For both options the AI deck is the supply bottleneck (Bitcraze out of stock; RobotShop US 2 left).

---

## Unconfirmed items

- Digi-Key, Mouser, Seeed Studio direct and Amazon US listings, prices and stock: not found or not readable.
- Bitcraze stock for items with no label; whether Bitcraze ships to the US and how long it takes.
- RobotShop US stock for Multi-ranger, Crazyradio 2.0, 350 mAh battery and the STEM ranging Brushless bundle (not shown on the pages).
- Exact contents of the STEM ranging 2.1+ bundle and the AI bundle.
- Component masses for the 2.1+ (motors, props, board), the battery holder deck and the pin headers.
- Whether the Brushless 350 mAh battery is the same pack as the 9.1 g one.
- Loaded flight times for both configurations.
- Physical clearance of the AI deck under the Multi-ranger.
- CrazySim on Gazebo Harmonic, and its Flow/Multi-ranger simulation.
- FCC authorization status of the Crazyflie models.
- Minimum Loco node count.
- Release status of DORY/NanoCockpit AI-deck examples after 2026-05-27.

## Sources (all seen 2026-10-26)

| URL | Supports |
|---|---|
| https://store.bitcraze.io/products/crazyflie-2-1-plus | 2.1+ $240 USD, SKU 114993491, 29 g, kit contents |
| https://bitcraze.io/products/crazyflie-2-1-plus/ | 2.1+ 29 g, 15 g payload, 7 min, 40 min charge, MCUs, sensors |
| https://cdn.robotshop.com/media/B/BCZ/RB-Bcz-25/pdf/crazyflie_2_1_plus-datasheet.pdf | 2.1+ datasheet (2024-06-19): 29 g, 15 g, 7 min, 250 mAh |
| https://bitcraze.io/products/crazyflie-2-1-brushless | Brushless 34/37 g, 40 g payload, 10 min, 30 g thrust per motor, LED-ring exception |
| https://cdn.robotshop.com/media/B/BCZ/RB-Bcz-25/pdf/crazyflie_2_1_brushless-datasheet.pdf | Brushless datasheet rev 3 (2025-01-11): 350 mAh included, specs |
| https://store.bitcraze.io/products/crazyflie-2-1-brushless | Brushless $480 USD, SKU 100060743, kit contents |
| https://www.bitcraze.io/documentation/tutorials/getting-started-with-crazyflie-brushless/ | Brushless box contents, client OS notes |
| https://store.bitcraze.io/collections/bundles | Bundle prices and out-of-stock labels |
| https://store.bitcraze.io/collections/all (pages 1–5) | All item prices, stock labels, Crazyradio $43, 350 mAh $12, decks |
| https://store.bitcraze.io/collections/decks | Deck prices, AI deck out of stock, no Z-ranger listed |
| https://www.bitcraze.io/2024/08/introducing-the-new-crazyflie-2-1 | 2.1 discontinued, replaced by 2.1+; 47-17 props, battery 1 g lighter |
| https://bitcraze.io/products/old-products/crazyflie-2-0 | 2.0 discontinued, replaced by 2.1+; 42 g max takeoff |
| https://www.bitcraze.io/products/old-products/z-ranger-deck-v2/ | Z-ranger v2 discontinued, 1.6 g, use Flow v2 instead |
| https://www.bitcraze.io/products/flow-deck-v2/ | Flow v2 1.6 g, sensors, bottom mount |
| https://www.bitcraze.io/products/multi-ranger-deck/ | Multi-ranger 2.3 g, 5 directions, top mount, no avoidance by default |
| https://bitcraze.io/products/ai-deck | AI deck 4.4 g, GAP8/ESP32/HM01B0, pin use |
| https://mouser.com/pdfDocs/ai_deck_1_1-datasheet.pdf | AI deck datasheet (2021-02-12): 4.4 g, 3–5 V up to 300 mA |
| https://bitcraze.io/products/lighthouse-positioning-deck/ | Lighthouse deck 2.7 g, top, UART1 |
| https://bitcraze.io/products/loco-positioning-deck | Loco deck 3.3 g, top/bottom, needs nodes |
| https://www.bitcraze.io/products/led-ring-deck/ | LED-ring 3.3 g, not Brushless out of the box, IO3 conflict with Flow |
| https://www.bitcraze.io/products/color-led-deck/ | Color LED deck 3.5 g, top and bottom variants |
| https://bitcraze.io/documentation/system/platform/cf2-expansiondecks | Compatibility matrix, pin use, UART1/UART2/IO4 conflicts, stacking and pin rules |
| https://www.bitcraze.io/documentation/hardware/250mah_battery/250mah_battery-datasheet.pdf | 250 mAh battery 7.1 g, 15C |
| https://store.bitcraze.io/products/350mah-lipo-battery | 350 mAh battery $12, 9.1 g, SKU 114993131 |
| https://www.bitcraze.io/?p=12536 | 350 mAh battery needs 9 mm pins; up to 10 min hover (2023-10-16) |
| https://store.bitcraze.io/collections/all/products/crazyradio-2-0 | Crazyradio 2.0 $43 USD, SKU 114993492, nRF52 |
| https://www.robotshop.com/products/bitcraze-crazyflie-21 | US: 2.1+ $240, in stock 9 units, mfr 114993491 |
| https://robotshop.com/products/bitcraze-crazyflie-21-brushless | US: Brushless $480, "Re-stocking soon" |
| https://robotshop.com/products/seeedstudio-crazyflie-21-version-open-source-micro-quadcopter-drone | US: Seeed 2.1+ $240, On Demand, 27 g listed |
| https://robotshop.com/products/bitcraze-crazyflie-2x-flow-deck-v2 | US: Flow v2 $63.39, in stock 5 |
| https://www.robotshop.com/products/bitcraze-multi-ranger-deck | US: Multi-ranger $114.04, mfr 114991485 |
| https://www.robotshop.com/products/bitcraze-ai-deck-11 | US: AI deck $308.02, only 2 left |
| https://www.robotshop.com/products/bitcraze-crazyradio-20 | US: Crazyradio 2.0 $49.44 |
| https://www.robotshop.com/products/bitcraze-350mah-lipo-battery | US: 350 mAh $16.37 |
| https://www.robotshop.com/products/bitcraze-thrust-upgrade-bundle-for-crazyflie-2x | US: thrust upgrade $19.28, +20 g thrust, −15% flight time |
| https://www.robotshop.com/products/bitcraze-stem-ranging-bundle-crazyflie-21-brushless | US: STEM ranging Brushless $735.25 |
| https://uk.robotshop.com/products/bitcraze-crazyflie-21-brushless-motor-08028-10000kv | 08028 motor 2.3 g with cable |
| https://eu.robotshop.com/products/bitcraze-ai-bundle-crazyflie-21 | AI bundle 2.1+ contents |
| https://www.generationrobots.com/en/404337-stem-ranging-bundle-crazyflie-21-brushless.html | STEM ranging Brushless contents; EUR 822 incl. VAT; 2 available |
| https://www.generationrobots.com/en/403746-nano-drone-programmable-crazyflie-21-uav-getting-started-bundle.html | Getting started bundle contents (CF + Crazyradio) |
| https://www.generationrobots.com/en/404391-crazyflie-21-brushless.html | Brushless EUR 600 incl. VAT, delivery within 2 weeks |
| https://bitcraze.io/documentation/tutorials/getting-started-with-stem-drone-bundle | STEM drone bundle items; tested on Ubuntu 22.04 |
| https://www.bitcraze.io/documentation/repository/aideck-gap8-examples/master/examples/ | List of AI deck examples |
| https://www.bitcraze.io/documentation/repository/aideck-gap8-examples/master/examples/face-detection/ | Face detection details; Autotiler unavailable; DORY suggested |
| https://github.com/orgs/bitcraze/discussions/1854 | Autotiler outage timeline 2025-03 to 2026-05; DORY direction |
| https://arxiv.org/pdf/2103.10873 | PULP-Frontnet onboard person following |
| https://arxiv.org/abs/2601.07476 | NanoCockpit framework paper (2026) |
| https://pypi.org/pypi/cflib/json, https://pypi.org/pypi/cfclient/json | cflib 0.1.34 / cfclient 2026.8.1, Python >=3.10, classifiers to 3.13 (fetched via API) |
| https://bitcraze.io/documentation/repository/crazyflie-lib-python/master/installation/install | cflib needs Python 3.10+; venv recommended |
| https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/installation/usb_permissions/ | udev rules |
| https://github.com/bitcraze/crazyflie-simulation (cloned) | README "not actively maintained"; Webots/Gazebo docs; last commit 2026-03-19 |
| https://github.com/IMRCLab/crazyswarm2 (cloned) | 24.04/Py3.12/Jazzy support; sim backend; firmware 2025.02; last commit 2026-09-11 |
| https://github.com/bitcraze/crazyflie-firmware (cloned, master 2026-10-22) | CF_MASS constants, the 39.3 g Brushless comment, bindings build (tested locally) |
| https://github.com/SOARLabOSU/CrazySim, llanesc/crazyflie-firmware, llanesc/crazyflie-simulation (cloned) | CrazySim README, platforms, gz-sim 8/7 CMake, commit dates |
| https://github.com/CrazyflieTHI/sim_cf2, https://github.com/gsilano/CrazyS, https://github.com/utiasDSL/crazyflow, https://github.com/utiasDSL/gym-pybullet-drones (cloned) | Platform support and last commit dates |
| https://bitcraze.io/development/external-projects/ | Bitcraze's list of simulators |
| https://community.robotshop.com/blog/show/us-drone-tariffs-what-changes-on-september-3-and-february-9 | 2026 US drone tariff timeline (post dated 2026-08-20) |
| https://www.akingump.com/en/insights/alerts/fcc-adds-all-foreign-made-uas-and-uas-critical-components-to-covered-list | FCC Covered List action of 2025-12-22; existing authorizations unaffected |
| https://www.wsgr.com/print/v2/content/49063276/Not-All-Drones-After-All:-FCC-Exempts-Certain-Foreign-Made-Drones-and-Critical-Components-from-Covered-List-and-Issues-Guidance-for-DoW-and-DHS-Conditional-Approvals.pdf | FCC/DoW follow-up of 2026-01-07 (Blue UAS / Buy American exemptions) |
