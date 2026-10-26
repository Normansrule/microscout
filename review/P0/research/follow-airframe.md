> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate. Research notes compiled on 2026-10-26 from the sources listed at the end; items not checked against a primary source are marked UNCONFIRMED.

# Wisp Follow: Airframe, Propulsion, Battery and Camera Research

Date of research: 2026-10-26. Web research only. No repo files were changed.

**Labels used**
- **CLAIM**: a figure from a maker or retailer spec sheet, not independently measured.
- **MEASURED**: from an independent review (for example Oscar Liang), with the method stated where known.
- **ESTIMATE**: my own calculation. The assumptions are stated next to it.
- **UNCONFIRMED**: not verified in this session. Weigh or check it before relying on it.

**Limits of this research.** The IntoFPV forum blocked automated reading (robots_disallowed), and the session's web-search budget ran out before the speed section was finished. As a result, **I found no GPS-logged top speed for any sub-250 g 3-3.5 inch quad.** Section 5 relies on a physics estimate, flagged as such, plus the few reference points I could verify.

---

## 0. Summary

| | **A "Vlog"** (3 in ducted, 4S) | **B "Fast"** (3.5 in open toothpick, 6S, removable guards) |
|---|---|---|
| Frame | GEPRC CineLog30 V3 (78 g, integral guards) | GEPRC Smart 35 (47.9 g) or BetaFPV X-Knight 35 (43.2 g) |
| Motors | GEPRC SPEEDX2 1404 3850KV (the motor of the CineLog30 V3 BNF) | T-Motor Pacer P1604 2850KV (6S) |
| Props | HQProp DT76mm x3 V2 (ducted) | Gemfan 3520-3 (the prop in T-Motor's thrust table) |
| Battery | GNB 4S 550 mAh 90C (57 g) or 4S 650 mAh HV 120C (70 g) | GNB 6S 550 mAh 90C (85 g); 6S 450 mAh as the light option |
| Camera | DJI O4 Air Unit, 8.2 g (4K60 onboard recording plus FPV link) | DJI O4 Air Unit, 8.2 g |
| Mass of these parts | ~198 g (4S 550) / ~211 g (4S 650), ESTIMATE total | ~203 g (6S 550, no guards) / ~228 g (with guards) |
| **Mass left for electronics** | **~52 g (4S 550) / ~39 g (4S 650)** | **~47 g without guards / ~22 g with guards (6S 550)** |
| Static thrust-to-weight at 240 g | ~5.8-7.5 : 1, ESTIMATE (no maker table found) | **10.3 : 1** (from the T-Motor CLAIM table) |
| Top speed (ESTIMATE, level flight) | ~75-100 km/h | ~100-140 km/h on 6S; ~90-120 km/h on 4S |
| Hover time with the 35-45 g payload (ESTIMATE) | ~5-7 min | ~5.5-7 min |

**Pi Zero 2 W verdict.** The Pi Zero 2 W fits Config A. It fits Config B only with the guards removed, or on a 4S or 6S 450 mAh pack. A guarded 6S 550 mAh Fast build leaves about 22 g, which is not enough for 35-45 g of electronics.

**3.5 inch ducted frames do not fit.** Every 3.5 inch cinewhoop frame I checked weighs 114-214 g on its own, which leaves too little for the 35-45 g of electronics (see Section 1). The ducted Vlog variant has to be a 3 inch frame.

---

## 1. Frames

| Frame | Type | Frame mass | Wheelbase | Stack / motor mount | Price, stock (2026-10-26) | Source | Fit for Wisp? |
|---|---|---|---|---|---|---|---|
| GEPRC CineLog30 V3 (GEP-CL30 V3) | 3 in ducted, integral guard | **78 g ±2** CLAIM | 128 mm | 25.5×25.5 / **9×9** | $71.99, **sold out** at Pyrodrone | Pyrodrone | **Best ducted option.** The kit includes ducts, 3 canopies and an aluminium lens mount. |
| GEPRC CineLog35 V2 | 3.5 in ducted | 133.7 g CLAIM | 142 mm | 25.5 / 12×12; 95 mm guard ID | In stock (few) at GetFPV; price not shown | GetFPV | Too heavy. With 1505 motors the total is about 278 g, ESTIMATE. |
| BetaFPV Pavo35 | 3.5 in ducted | 113.9 g CLAIM | 148 mm | 25.5 / 12 mm M2 | $64.99, **out of stock** at GetFPV | GetFPV | Marginal. With P1604 motors and 4S 550 the total is ~240 g, leaving ~10 g. Not viable. |
| SpeedyBee Bee35 Standard (O4 Pro) | 3.5 in ducted | 138 g CLAIM | 153 mm | 20/25.5/30.5 / 12×12 | In stock at GetFPV; frame price not shown | GetFPV | Too heavy |
| Axisflying CineON C35 V2 | 3.5 in ducted | 140.7 g CLAIM | 152 mm | 20 & 25.5 / 12×12 | Out of stock at GetFPV | GetFPV | Too heavy |
| Axisflying C35 V3 (no LED) | 3.5 in ducted | 206 ±5 g CLAIM | 160 mm | 20 & 25.5 / 9 & 12 | $58.49 at GetFPV; stock count not shown | GetFPV | Too heavy |
| iFlight ProTek35 V1.4 | 3.5 in ducted | 213.5 g CLAIM | 151 mm | n/a / 12×12 | $64.99, **out of stock** at GetFPV | GetFPV | Too heavy |
| Diatone MX-C Taycan 3 in | 3 in ducted | 175 g CLAIM | 158 mm | 20/30.5 / 12 | Stock status conflicting at GetFPV | GetFPV | Too heavy |
| Flywoo FlyLens 85 V1.3 | 2 in ducted | 25.5 g (27 g with hardware) CLAIM | n/a | 25.5 / 6.6 mm | $29.99, in stock at MyFPVStore | MyFPVStore | 2 inch props: too little thrust for a ~240 g quad |
| BetaFPV Pavo Pico II (O4) | ~2 in whoop | 19 g + 9 g duct CLAIM | 80 mm frame | 25.5 / 3×M1.4 φ6.6 | €14.90, 2 pcs at FPV24 | FPV24 | Too small for this payload |
| **GEPRC Smart 35 (GEP-ST35)** | 3.5 in open toothpick | **47.9 g** with prints and reinforced arm, CLAIM | 155 mm | 26.5 & 20 / **9×9 & 12×12** | AU$89.99, **sold out** at FPVFaster (AU) | FPVFaster | **Best Fast option** |
| **BetaFPV X-Knight 35** | 3.5 in open toothpick | **43.22 g** CLAIM | 155 mm | 26.5 or 20 / 9×9 or 12×12 | $25.99, **sold out** at BetaFPV | BetaFPV | Alternative Fast frame |
| AvionRC Ikon 3 | 3 in open (squished-X) | ~45 g incl. TPU CLAIM | 140 mm | 20×20 / 9 mm | CHF 59.90; stock not stated | fpvracing.ch | Alternative 3 inch open frame |
| Ummagawd 2Fiddy V1.5 | 3.5-4 in ultralight | 51 g CLAIM (the same page also says 0.2375 lb ≈ 108 g) | n/a | 30.5/20/whoop | $74.99; out of stock at MyFPVStore | MyFPVStore, RDQ | Weight conflict, UNCONFIRMED |

**Not checked (UNCONFIRMED):** the HDZero/Flywoo Explorer frames, Rotor Riot frames, and the Axisflying Avata 3.5 frame kit. The search budget ran out before I reached them.

**Bolt-on guards for the Fast variant.** GEPRC's 3 inch prop guard (for the Cinequeen, 9×9 mount) weighs **6.3 g each** (CLAIM, Unmanned Tech, sold out), about 25 g for four. I found no verified mass for a 3.5 inch guard set. For Config B I assume ~25 g for four guards, ESTIMATE, UNCONFIRMED.

**Room for the Pi Zero 2 W (65×30 mm).** No maker page gives a payload deck size, so this is UNCONFIRMED for every frame.
- The CineLog30 V3 (128 mm wheelbase) and both 155 mm toothpicks have center bodies roughly the length of a 65 mm board.
- Plan a printed TPU mount above the 25.5/26.5 mm stack, or under the battery strap. Test-fit it in CAD before buying.

---

## 2. Motors and props

### 2.1 Maker thrust tables found (CLAIM unless stated)

| Motor | Mass | KV / cells | Prop | Max thrust per motor | Current / power at 100% | Source |
|---|---|---|---|---|---|---|
| **T-Motor Pacer P1604** | **11.6 g** (with cable) | **2850KV / 6S** | GF3520-3 | **618.8 g** at 24.9 V | 15.8 A / 394.6 W | T-Motor table reproduced at rcdrone.top; mass also from GetFPV |
| T-Motor Pacer P1604 | 11.6 g | 3800KV / 4S | GF3520-3 | **514.1 g** at 16.5 V | 16.8 A / 277.8 W | same |
| T-Motor F1408-II | 12.7 g bare / 14.9 g with cable | 2800KV | GF3028-3 | 390.5 g on 4S; 557.1 g on 5S (20.9 V); **726.4 g on 6S** (25.1 V) | 8.6 A / 15.4 A on 6S | T-Motor store |
| T-Motor F1408-II | 14.95 g | 2800KV | HQ3520-3, 4S | 530.9 g | 12.45 A / 208 W | T-Motor store |
| T-Motor F1408-II | 14.95 g | 3950KV | GFD90-3 (ducted 3.5 in), 3S | 555.1 g | 21.8 A / 270 W | T-Motor store |
| T-Motor F1204 | 6.9 g | 5000KV 3S / 6500KV 2S | HQ3020 | 171.8 g / 156.3 g | — | T-Motor store. Too weak for this build. |
| Axisflying C206 (2006) | 22 g | 2750KV / 6S | not stated | "over 0.9 kg" | ~21.5 A | FPV24 (discontinued) |

### 2.2 Motors without a usable thrust table (mass, KV only)

| Motor | Mass | KV | Notes | Source |
|---|---|---|---|---|
| T-Motor F1404 | 9.34 g with cable | 2900 / 3800 / 4600 | 3800KV: 304 W, 19 A peak (60 s). No thrust table. Sold out at rcdrone ($36.51). | GetFPV, rcdrone.top |
| GEPRC SPEEDX2 1404 | 10.5 g with wire | 3000 / 4600 (the CineLog30 V3 BNF uses **3850KV**, mass UNCONFIRMED) | 3000KV: 160 W max | GetFPV |
| GEPRC SPEEDX2 1505 | 12.7 g | 4300KV, 4S | 340.9 W, 21.56 A peak (3 s); $17.12; 2 in stock | Rotor Village |
| iFlight XING 1504 | 12.4 g | 3100 / 3900, 3-6S | — | GetFPV |
| BrotherHobby VY 1504.5 | 12 g | 2650 / 2950 (6S) / 3950 | — | GetFPV |
| BrotherHobby Avenger 1507 | 15.5 g | 2800 / 3600 / 4100 | Maker suggests a 135-155 g AUW 3 in build on Gemfan 3052 | GetFPV Learn |
| BetaFPV 1404 | 8.49 g | 4500KV, 3-4S | Paired with Gemfan D63 (2.5 in). Sold out. | BetaFPV |

**Independent tests.** Recursion Labs (IntoFPV, Apr 2022) bench-tested 1404-class motors on 3, 3.5 and 4 inch props: Flywoo NIN 1404 V2, Xing 1404, T-Motor F1404, BH VY 1504.5, and F1404 against F1408. The numbers are only in charts and video, so I could not extract them (UNCONFIRMED).

### 2.3 Prop masses

I did not find verified masses for the HQ DT76mm x3 V2 or the Gemfan 3520-3. As a working ESTIMATE, UNCONFIRMED, I use **~1.5-2 g per 3 in ducted tri-blade** and **~2-2.5 g per 3.5 in tri-blade**. Weigh a set before finalising.

### 2.4 Thrust-to-weight at ~240 g all-up mass

| Setup | Static thrust (4 motors) | T/W at 240 g | Basis |
|---|---|---|---|
| P1604 2850KV, 6S, GF3520-3 | 2475 g | **10.3 : 1** | CLAIM table |
| P1604 3800KV, 4S, GF3520-3 | 2056 g | **8.6 : 1** | CLAIM table |
| F1408-II 2800KV, 6S, GF3028-3 | 2906 g | 12.1 : 1 | CLAIM table. Motors are ~13 g heavier per set than the P1604. |
| SPEEDX2 1404 3850KV, 4S, DT76 ducted | ~1400-1800 g | **~5.8-7.5 : 1** | ESTIMATE, bracketed by the 1408/1604 tables. No 1404 + 3 in table found. |

---

## 3. Batteries

| Pack | Mass | Capacity / C | Price, stock (2026-10-26) | Source |
|---|---|---|---|---|
| **GNB 4S 550 mAh 90C** (XT30) | **57 g ±2** | 550 mAh / 90C cont., 180C burst; 72×18×24 mm | $18.99, **in stock** | Pyrodrone |
| BetaFPV LAVA 4S 550 mAh 75C | 56.5 g | 550 / 75C; 67×15.5×26 mm | CAD 32.97 per 2-pack, out of stock | Rotor Village |
| **GNB 4S 650 mAh HV 120C** | **70 g** | 650 / 120C; 63×30×21 mm | $23.99 (Pyrodrone, sold out); $20.99 (RDQ, stock not shown) | Pyrodrone, RDQ |
| GNB 4S 850 mAh HV 60C/120C | ~73 g (looks low for 850 mAh 4S HV, UNCONFIRMED) | 850 / 60C cont. | $23.99, sold out | Pyrodrone |
| GNB 4S 850 mAh 80C | 102 g ±3 | 850 / 80C | not checked | KiwiQuads |
| Tattu R-Line V5 4S 850 mAh 150C | 100 g ±20 | 850 / 150C | $22.99, sold out / pre-order | WREKD |
| GNB 6S 450 mAh 80C (long) | **not listed**: ~70 g ESTIMATE, scaled from the 550 mAh pack | 450 / 80C | $24.99, stock not shown | RDQ |
| **GNB 6S 550 mAh 90C** (long) | **85 g ±3** | 550 / 90C; 36×18×73 mm | $14.99, pre-order | RDQ |
| GNB 6S 650 mAh 80C | 124 g ±5 (embedded data says 105) | 650 / 80C | $20.99, pre-order | WREKD |
| Molicel P30B 18650 cell | ~47 g per cell | 3000 mAh, 30 A | $6.99 | IMR Batteries |
| Molicel P45B 21700 3S1P pack (Flywoo) | 224.3 g | 4500 mAh, 45 A | £16.89, sold out | Unmanned Tech |

**Current-limit warning (ESTIMATE from the CLAIM figures).** At full throttle, four P1604 2850KV motors draw 4 × 15.8 = 63 A. Continuous ratings fall short of that:
- 6S 550 mAh 90C: 49.5 A
- 6S 450 mAh 80C: 36 A
- 4S 550 mAh 90C (P1604 3800KV): 49.5 A, against 67 A at full throttle
- 4S 650 mAh 120C: 78 A, which does cover it

Short bursts will rely on the burst ratings. The resulting voltage sag will lower top speed below the static-thrust prediction.

**Li-ion does not fit this payload.**
- A 4S1P 18650 pack weighs ≥188 g in cells alone (4 × 47 g), and a 4S 21700 pack is heavier.
- Oscar Liang's Flywoo Explorer LR (a 4 in quad, 163 g dry) got ~28 min at a 50 km/h cruise on 4S 18650, MEASURED. But 163 g plus a ≥188 g pack is ≥350 g, ESTIMATE, well over 250 g.
- A 2S 21700 pack (~150 g, ESTIMATE) would need very high-KV motors and still leaves no room for 35-45 g of electronics.

---

## 4. Camera

The DJI O4 Air Unit is the FPV link and the 4K60 recorder in one 8.2 g module. That makes it the strongest choice for both configs. The Pi camera is used only for tracking and is counted in the electronics budget.

| Camera | Mass | Recording | Stabilisation | Price, stock | Source |
|---|---|---|---|---|---|
| **DJI O4 Air Unit** | **8.2 g with camera** (5.1 g without; 9.2 g with lens mount) | 4K 16:9 at 30/50/60; 4K 4:3 at 60; 1080p up to 120; 23 GB internal, no SD card | RockSteady 3.0+ (standard angle only), or off with Gyroflow | AU$189, sold out (FPVFaster AU); Adorama "no longer available"; **US stock UNCONFIRMED** | FPVFaster, Adorama, DJI |
| DJI O4 Air Unit Pro | 32 g total (15.6 g without camera); antenna ~2.1 g each | 4K up to 120 fps | RockSteady 3.0+, or Gyroflow | $289, in stock at GetFPV | GetFPV |
| RunCam Thumb Pro W | 16 g | 4K30, 2.7K60, 1080p120 | Built-in gyro, Gyroflow | $99.99; stock not shown | RunCam |
| RunCam Thumb 2 | 27.8 g (reader-measured 27.48 g bare, 31.24 g with TPU cover) | 4K60, 2.7K60, 1080p120 | Onboard EIS, Gyroflow (.gcsv) | $99 (review); $119.99 at RDQ | Oscar Liang (Oct 2024), RDQ |
| Insta360 GO 3S | 39.1 g (Action Pod 96.3 g) | 4K 24/25/30; 2.7K50; 1080p up to 200 | 6-axis gyro (EIS method not named) | not checked | Insta360 |
| Insta360 GO Ultra | 53 g | 4K60; 1080p240 | FlowState, 360 Horizon Lock | £388.99, in stock (Scan UK) | Scan |
| GEPRC naked GoPro Hero 11 | 46.7 g | 5.3K60, 4K120 | HyperSmooth 5.0, Gyroflow, ReelSteady | $828.99, sold out | Pyrodrone |
| Caddx Walnut | 60 g (the text also says ~64 g) | 4K60 | Gyroflow | — | Oscar Liang. Too heavy. |
| Caddx Peanut | not found, UNCONFIRMED | — | — | — | — |
| Insta360 GO 3 (non-S) | not checked, UNCONFIRMED | — | — | — | — |
| Raspberry Pi Camera Module 3 / Wide | mass not listed, UNCONFIRMED | 1080p50, 720p120; 12 MP IMX708; PDAF autofocus; 75° / 120° FOV; 25×24×11.5 mm (Wide 12.4 mm) | none (tracking camera) | from $25; Wide €35.90, 10+ in stock at Welectron | Raspberry Pi, Welectron |

**Notes**
- The O4 Air Unit accepts **3.7-13.2 V**. On 4S (16.8 V) and 6S (25.2 V) it must run from a 9-10 V BEC (CLAIM, input range).
- DJI's OSD with ArduPilot works through MSP DisplayPort. That comes from my general knowledge and was not re-verified this session, so UNCONFIRMED.
- Analog or HDZero systems would save little over 8.2 g and lose the 4K recording, so I did not research them further.

---

## 5. Speed

### 5.1 What I could verify

| Aircraft | Mass | Top speed | Basis |
|---|---|---|---|
| GEPRC CineBot35 O4 Pro (3.5 in **ducted**, 6S, 2105.5 2450KV) | 391 g dry / 583 g AUW | **140-150 km/h** | Attributed to Oscar Liang by Unmanned Tech (15 Jul 2026). The method is not stated. Not sub-250, but it shows ducted 3.5 in can reach ~140 km/h given the power. |
| DJI Mini 5 Pro | 249.9 g | 18 m/s = **64.8 km/h** (19 m/s with Plus battery); 15 m/s in tracking | CLAIM (DJI, wind-tunnel test, via Dr Drone) |
| DJI Neo 2 | ~135 g | 16 m/s = 57.6 km/h (Manual); 8 m/s Sport; ActiveTrack up to 26.8 mph (~43 km/h) | CLAIM (Roberts Camera) |
| Flywoo Explorer LR (4 in, 4S 650, 242 g) | 242 g | 50 km/h **cruise** (not top speed) | MEASURED (Oscar Liang) |
| Sub-250 3-3.5 in FPV quads (Smart 35, Seeker3, RATEFPV S30 Pro, Pavo35, CineLog30) | — | **No top speed published** on any maker or review page I reached | — |

- **Fastest documented sub-250 g quad: not determined.** I found no GPS-logged speed for a sub-250 g 3-3.5 inch quad.
- Unmanned Tech's speed article (19 Jun 2026) gives no figure for 3 inch, 3.5 inch or cinewhoop classes. It warns that GPS reads ground speed (so wind matters), that runs should be two-way, and that dives are not level speed.
- A follow-up search session could look at Oscar Liang's 3 inch O4 buyer's guide (10 Oct 2025), YouTube GPS-OSD runs, and RCGroups.

### 5.2 Physics estimate (ESTIMATE)

**Model**
- In level flight at tilt θ: T·cosθ = W and T·sinθ = D, with D = ½ρ·CdA·v² (so drag power P = ½ρ·CdA·v³).
- ρ = 1.20 kg/m³, for sea level at San Pedro.
- Two bounds:
  - (i) **Static-thrust bound.** Thrust stays at the bench value at speed. This is unrealistically optimistic.
  - (ii) **Linear prop unloading.** T(v) = T0·(1 − v/v_p), where v_p is the pitch speed: RPM × pitch, with loaded RPM taken as 0.8 × KV × V. This is closer to reality.

**Assumptions**
- Static thrust T0 for B on 6S: 2475 g, the CLAIM table.
- Pitch speed for P1604 2850KV on 6S with a 2.0 in pitch prop: **48 m/s (173 km/h)**. For 3800KV on 4S: **42.5 m/s**.
- For A, T0 is 1400-1800 g (ESTIMATE). The DT76 pitch is assumed to be ~1.75 in (UNCONFIRMED), giving a pitch speed of **~36 m/s**.
- **CdA (assumed; not measured for these frames):**
  - Open 3.5 in toothpick: 0.005-0.010 m²
  - Toothpick with bolt-on guards: 0.010-0.015 m²
  - 3 in ducted whoop: 0.010-0.020 m²

| Config | CdA (m²) | Static-thrust bound | **Linear-unloading estimate** | Tilt at top speed |
|---|---|---|---|---|
| B 6S, open, 240 g | 0.005 | 323 km/h | **138 km/h** | 62° |
| B 6S, open | 0.0075 | 264 km/h | **129 km/h** | 68° |
| B 6S, open | 0.010 | 228 km/h | **122 km/h** | 71° |
| B 6S, guards, 250 g | 0.015 | 187 km/h | **110 km/h** | 74° |
| B 4S, open, 240 g | 0.0075 | 240 km/h | **114 km/h** | 63° |
| B 4S, open | 0.010 | 208 km/h | **108 km/h** | 66° |
| A 4S ducted, T0 1600 g, 245 g | 0.010 | 183 km/h | **92 km/h** | 58° |
| A 4S ducted | 0.015 | 149 km/h | **84 km/h** | 64° |
| A 4S ducted | 0.020 | 129 km/h | **79 km/h** | 67° |
| A, T0 range 1400-1800 g | 0.010-0.020 | — | **75-95 km/h** | 57-69° |

**Interpretation (ESTIMATE)**
- **On a light quad, top speed is limited by pitch speed and prop unloading, not by drag.** That is why 6S gains only ~10-15% over 4S (129 vs 114 km/h at CdA 0.0075), even though static thrust rises 20%.
- More pitch (for example a 3.5×2.8 tri-blade) or higher KV raises the ceiling. The cost is current, which the small packs already cannot supply continuously (Section 3).
- **Guards cost about 5-15%** in this model: from ~129 km/h open to ~110-122 km/h guarded, mostly through added CdA.
- **Ducts plus a 3 inch 4S setup** land at roughly 75-100 km/h. That is still well above the Mini 5 Pro claim (65 km/h) and above any realistic follow-me speed.
- Bound (i) is not physical: props lose almost all thrust well before 230-320 km/h. Use the linear-unloading column.

**ArduPilot limits.** In Stabilize and AltHold the lean angle is capped by `ANGLE_MAX`. Top speed needs ~60-75° of tilt per the table, so that cap must be raised for the Fast variant. Follow and Guided modes have their own speed caps. Both points are from general knowledge, not re-verified, so UNCONFIRMED.

---

## 6. Endurance

| Data point | Flight time | Basis |
|---|---|---|
| GEPRC Smart 35 (3.5 in, 150 g dry, 1404 3850KV, 3528 props), 4S 850 | ~6 min aggressive, **7-8 min relaxed cruise** | MEASURED (Oscar Liang, Jun 2021) |
| GEPRC Smart 35, 4S 650 | **4-5 min** | MEASURED (Oscar Liang) |
| Flywoo Explorer LR (4 in), 4S 650, 242 g | up to **8 min** cruise | MEASURED (Oscar Liang) |
| Flywoo Explorer LR, 4S 1000 | ~12 min | MEASURED (Oscar Liang; this is likely over 250 g) |
| Flywoo Explorer LR, 4S 18650 Li-ion | **~28 min at 50 km/h** (Flywoo claims 38) | MEASURED, but **over 250 g** |
| Explorer LR 4 (newer, 154 g bare) | 5-8 min sport (4S 750); 25-30 min gentle on 4S 18650 | Unmanned Tech guide (Jul 2026) |
| GEPRC CineLog30 V3 O4 Pro (187 g dry), 4S 660-720 HV | **8'10"** at slow cruise | CLAIM (GetFPV) |
| GEPRC CineLog35 V2 (262 g), 1050-1300 mAh | 5'00"-8'30" | CLAIM |
| BetaFPV Pavo35 HD 6S | "12 minute flight time" | CLAIM (RDQ) |
| Typical 3 in cinewhoop, 4S 850-1100 | 6-8 min | Unmanned Tech guide (Mar 2026), conditions unstated |
| **DJI Mini 5 Pro** | **36 min** at 21.6 km/h (52 min with the Plus battery); "typical" **21 min** | CLAIM (DJI via Dr Drone) |
| **DJI Neo 2** | 18 min, **17 min with prop guards** | CLAIM |

**Wisp Follow hover estimate (ESTIMATE)**
- Hover efficiency comes from the P1604 table at 20% throttle: 3.5 g/W on 4S and 2.9 g/W on 6S. Hover at ~60 g per motor is below that point, so these numbers are conservative.
- Electronics load is assumed at **~6 W** (Pi Zero 2 W plus O4 plus FC, GPS and sensors), UNCONFIRMED.
- 80% of pack energy is treated as usable.

| Pack | Estimated hover |
|---|---|
| 4S 550 | ~5.2 min |
| 4S 650 | ~6.2 min |
| 6S 450 | ~5.6 min |
| 6S 550 | ~6.8 min |

Ducts usually improve hover efficiency, so Config A may beat these figures, but that was not quantified. Follow-me cruise at 15-30 km/h should land near hover-to-slightly-better times. **Plan on 5-7 min per pack**, about a quarter of what a DJI Mini 5 Pro gets.

---

## 7. Proposed configurations

### Config A: "Vlog" (3 in ducted, 4S, quiet, best footage)

| Part | Choice | Mass (g) | Basis | Price / supplier / stock |
|---|---|---|---|---|
| Frame | GEPRC CineLog30 V3 (ducts, canopy, aluminium lens mount) | 78 | CLAIM ±2 | $71.99 Pyrodrone, **sold out**. Check fpvracing.ch and RDQ. |
| Motors ×4 | GEPRC SPEEDX2 1404 3850KV (9×9, as in the CineLog30 V3 BNF) | 42 | ESTIMATE (10.5 g sibling-KV figure; 3850KV mass UNCONFIRMED) | GetFPV price not shown; stock unclear. Alternative: T-Motor F1404 3800KV at 9.34 g (37.4 g for four), mount pattern UNCONFIRMED. |
| Props ×4 | HQProp DT76mm x3 V2 | ~7 | ESTIMATE, UNCONFIRMED | Included with the BNF; separate stock not checked |
| Battery | GNB 4S 550 90C (option: 4S 650 HV 120C, 70 g) | 57 | CLAIM | $18.99 Pyrodrone, **in stock** (650: $20.99 RDQ) |
| Camera | DJI O4 Air Unit with lens mount | 9.2 | CLAIM | AU$189 FPVFaster (sold out); **US stock UNCONFIRMED** |
| Screws, straps, XT30 pigtail, antenna holder | — | ~5 | ESTIMATE | — |
| **Subtotal** | | **~198 g** (4S 550) / **~211 g** (4S 650) | ESTIMATE | |
| **Left for electronics** | | **~52 g / ~39 g** | ESTIMATE | |

**Verdict.** The 35-45 g electronics stack, including the Pi Zero 2 W, fits comfortably with 4S 550 and just fits with 4S 650.

**Performance (ESTIMATE)**
- T/W ~5.8-7.5 : 1
- Top speed ~75-100 km/h
- Hover ~5-6 min (4S 550) or ~6-7 min (4S 650)

**Caveats**
- The FC must be a 25.5 mm whoop-pattern ArduPilot H7 board.
- If that FC is not an AIO with an ESC, a separate 4-in-1 ESC (~5-8 g, UNCONFIRMED) comes out of the electronics budget.

### Config B: "Fast" (3.5 in open toothpick, 6S, removable guards)

| Part | Choice | Mass (g) | Basis | Price / supplier / stock |
|---|---|---|---|---|
| Frame | GEPRC Smart 35 (or BetaFPV X-Knight 35 at 43.22 g) | 47.9 | CLAIM | AU$89.99 FPVFaster, **sold out**; X-Knight 35 $25.99 BetaFPV, **sold out** |
| Motors ×4 | T-Motor Pacer P1604 2850KV (6S) | 46.4 | CLAIM 11.6 g each | $22 each at rcdrone.top (sold out); GetFPV stock unclear |
| Props ×4 | Gemfan 3520-3 (the prop in T-Motor's table) | ~9 | ESTIMATE, UNCONFIRMED | not checked |
| Battery | GNB 6S 550 90C (light option: GNB 6S 450 80C, ~70 g ESTIMATE) | 85 | CLAIM ±3 | $14.99 RDQ, **pre-order** (450: $24.99 RDQ) |
| Camera | DJI O4 Air Unit with lens mount (on a ≤13.2 V BEC) | 9.2 | CLAIM | as above |
| Screws, straps, XT30, antenna holder | — | ~5 | ESTIMATE | — |
| **Subtotal (no guards)** | | **~203 g** | ESTIMATE | |
| Removable guards ×4 | 3.5 in TPU or moulded set | ~25 | ESTIMATE, UNCONFIRMED (GEPRC 3 in guard is 6.3 g each) | — |
| **Left for electronics** | | **~47 g with no guards; ~22 g with guards** | ESTIMATE | |

**Swap-in set to make the guarded build legal.** If guards are needed near people, use a 6S 450 pack (~70 g, ESTIMATE): ~188 g without guards (~62 g left), ~213 g with guards (~37 g left, borderline). Or go to 4S with P1604 3800KV motors and the GNB 4S 550 (57 g): ~175 g without guards (~75 g left), ~200 g with guards (~50 g left).

**Performance (ESTIMATE)**
- 6S: T/W **10.3 : 1** (CLAIM thrust), top speed **~120-140 km/h** open, ~110-120 km/h guarded
- 4S: T/W **8.6 : 1**, top speed ~105-120 km/h
- Hover ~5.5-7 min

**Honest assessment of the Pi Zero 2 W in Config B.** It fits only with the guards off, or with the 6S 450 or 4S pack. With guards on and a 6S 550 pack, it does not fit.

Even when it fits by mass:
- A 65×30 mm board on a 155 mm toothpick sits in the airflow and adds CdA.
- Vibration on a 10:1 quad is higher, which is worse for the Pi camera tracking.
- The 6S ESC current (~63 A at full throttle) and packs rated 36-50 A continuous are a mismatch that needs an ESC current limit. That is an engineering judgment, not measured.

If the owner wants maximum speed, a practical split is to fly Config B **without the Pi**: ArduPilot Follow using GPS from a ground beacon or phone, with the O4 recording. The Pi tracking payload then stays on Config A.

---

## 8. Unknowns to resolve before buying

1. **Measured sub-250 3-3.5 inch top speeds.** None was found this session. Next places to check: Oscar Liang's 3 inch O4 guide, YouTube GPS-OSD speed runs, RCGroups.
2. **Prop masses** (DT76 x3 V2, GF3520-3) and **3.5 inch guard mass**. Weigh them.
3. **Mass of the SPEEDX2 1404 3850KV**, and a thrust table for any 1404 on 3 inch ducted props.
4. **GNB 6S 450 mass**. RDQ does not list it. Also the suspiciously light 73 g figure for the GNB 4S 850 HV.
5. **US stock and price of the DJI O4 Air Unit (lite)**. Both the CineLog30 V3 frame and both toothpick frames were sold out at the retailers checked.
6. **Pi Zero 2 W mounting space** on each frame, and the Pi Camera Module 3 mass. Neither is listed.
7. **CdA** for these airframes. My values are assumptions. A GPS-logged two-way pass would calibrate the model.
8. **FAA.** The rule that recreational drones under 250 g need no registration or Remote ID was not re-verified in this session, so UNCONFIRMED. All-up mass must be weighed with the battery and every accessory.

---

## Sources (all seen 2026-10-26)

| URL | Supports |
|---|---|
| https://www.getfpv.com/geprc-cl35-cinelog-35-v2-frame-kit.html | CineLog35 V2 frame: 133.7 g, 142 mm, 25.5/12×12, in stock |
| https://www.getfpv.com/betafpv-pavo35-cinewhoop-frame-kit.html | Pavo35 frame: 113.9 g, 148 mm, $64.99, out of stock |
| https://www.getfpv.com/axisflying-c35-v3-frame-kit-w-o-led.html | C35 V3: 206 g, 160 mm, $58.49 |
| https://www.getfpv.com/axisflying-cineon-c35-3-5-frame-kit-w-aluminum-camera-plates.html | C35 V2: 140.7 g, 152 mm, out of stock |
| https://www.getfpv.com/iflight-protek35-v1-4-cinewhoop-frame-kit.html | ProTek35 V1.4: 213.5 g, $64.99, out of stock |
| https://www.getfpv.com/speedybee-bee35-standard-frame-kit-o4-pro-version.html | Bee35: 138 g, 153 mm |
| https://www.getfpv.com/diatone-mx-c-taycan-3-cinewhoop-frame-kit.html | Taycan MX-C 3 in: 175 g, 158 mm |
| https://www.myfpvstore.com/2vnz | FlyLens 85 frame: 25.5/27 g, 2 in, $29.99 |
| https://www.fpv24.com/en/betafpv/betafpv-pavo-pico-ii-whoop-quadcopter-frame-for-dji-o4-o4-pro-black | Pavo Pico II frame: 19 g + 9 g duct |
| https://pyrodrone.com/collections/3-inch-frames/products/geprc-gep-cl30-v3-cinelog30-v3-3-0-o4-compatible-drone-frame-kit | CineLog30 V3 frame: 78 g, 128 mm, 9×9, $71.99, sold out |
| https://www.getfpv.com/geprc-cinelog30-v3-drone-w-dji-o4-pro.html | CineLog30 V3 BNF: 187 g, SPEEDX2 1404 3850KV, DT76 x3 V2, 8'10" claim |
| https://wrekd.com/products/geprc-bnf-cinelog35-v2-analog-6s-3-5-cinewhoop-elrs-2-4ghz-gps | CineLog35 V2 BNF: 262 g, 2105.5 2150KV, 5-8.5 min claim |
| https://www.racedayquads.com/products/betafpv-bnf-pavo35-hd-6s-3-5-cinewhoop-for-dji-o3-without-o3-unit-choose-your-receiver | Pavo35 HD 6S: 12 min claim, $299.99 |
| https://www.fpvfaster.com.au/collections/frame/products/geprc-gep-st35-3-5-inch-fpv-smart-35-drone-frame-kit | Smart 35 frame: 47.9 g, 155 mm, 9×9/12×12, AU$89.99, sold out |
| https://betafpv.com/products/x-knight-35-frame-kit | X-Knight 35: 43.22 g, 155 mm, $25.99, sold out |
| https://fpvracing.ch/en/frames/4171-avionrc-ikon-3-frame.html | Ikon 3: 45 g, 140 mm, 3 in |
| https://myfpvstore.com/hmzm | 2Fiddy: 51 g (conflicting 108 g), $74.99 |
| https://www.racedayquads.com/products/ummagawd-2fiddy-v1-5-ultra-light-freestyle-3-5-4-frame-kit | 2Fiddy V1.5: $59.99 |
| https://www.unmannedtechshop.co.uk/products/geprc-3-prop-guard-4pc | GEPRC 3 in guard: 6.3 g each |
| https://pyrodrone.com/collections/deepspacefpv-products/products/deepspacefpv-seeker3-3inch-4s-with-gps-no-vtx-cam-sub250g-freestyle-fpv-drone-choose-receiver | Seeker3: Aether 1505, HQ 3×3×3, sub-250 claim, no speed |
| https://www.unmannedtechshop.co.uk/blogs/knowledge-base/deepspace-seeker3-vs-seeker35-vs-seeker5-fpv-drone | Seeker3 ~178 g; Seeker35 270-278 g dry (not sub-250) |
| https://www.fpvfaster.com.au/products/ratefpv-s30-pro-analog-3-inch-freestyle-4s-fpv-drone-elrs | RATEFPV S30 Pro: 166 g with O4, 1505 4300KV, no speed claim |
| https://rcdrone.top/products/t-motor-p1604-fpv-motor-kv2850 | P1604 thrust tables (T-Motor CLAIM), 11.6 g, $22 |
| https://www.getfpv.com/t-motor-pacer-p1604-motor-2850kv-3800kv.html | P1604: 11.6 g, 394.6 W / 277.8 W |
| https://store.tmotor.com/goods.php?id=1272 | F1408-II mass and thrust tables |
| https://store.tmotor.com/goods.php?id=1147 | F1204 mass and thrust tables |
| https://www.getfpv.com/t-motor-f1404-2900kv-3800kv-4600kv-motor-gray-red.html | F1404: 9.34 g, power figures |
| https://rcdrone.top/products/t-motor-f1404-kv3800-kv4600-3 | F1404: $36.51, sold out |
| https://www.getfpv.com/micro-quadcopters/micro-motors/geprc-speedx2-1404-motor-3000kv-4600kv.html | SPEEDX2 1404: 10.5 g |
| https://rotorvillage.ca/geprc-speedx2-1505-4300kv-motor/ | SPEEDX2 1505: 12.7 g, $17.12 |
| https://www.getfpv.com/iflight-xing-1504-fpv-nextgen-motor-3100kv-3900kv.html | XING 1504: 12.4 g |
| https://www.getfpv.com/brotherhobby-vy-1504-5-2650kv-2950kv-3950kv-motor.html | VY 1504.5: 12 g |
| https://www.getfpv.com/learn/?p=2786 | Avenger 1507: 15.5 g |
| https://betafpv.com/collections/brushless-motors/products/1404-4500kv-brushless-motors | BetaFPV 1404: 8.49 g, sold out |
| https://www.fpv24.com/en/axisflying/axisflying-c206-2006-6s-2750kv-fpv-motor | C206: 22 g, >0.9 kg claim |
| https://intofpv.com/printthread.php?tid=20429 | Recursion Labs 1404 test list (data in charts only) |
| https://pyrodrone.com/collections/500-1000mah/products/gaoneng-gnb-550mah-14-8v-4s-90c-lipo-battery-xt30 | GNB 4S 550: 57 g, $18.99, in stock |
| https://pyrodrone.com/collections/4s-batteries/products/gaoneng-gnb-650mah-15-2v-4s-120c-hv-lipo-battery-xt30 | GNB 4S 650 HV: 70 g, $23.99 |
| https://www.racedayquads.com/products/gaoneng-gnb-15-2v-4s-650mah-120c-lihv-micro-battery-xt30 | GNB 4S 650: $20.99 |
| https://pyrodrone.com/collections/all-products/products/gaoneng-gnb-850mah-4s-15-2v-60c-120c-xt30 | GNB 4S 850 HV: ~73 g |
| https://kiwiquads.co.nz/product/gnb-battery-14-8v-850mah-4s/comment-page-2 | GNB 4S 850 80C: 102 g |
| https://wrekd.com/products/tattu-r-line-version-5-0-850mah-4s-14-8v-150c-lipo-battery-pack-with-xt30-plug | Tattu R-Line V5 4S 850: 100 g, $22.99 |
| https://rotorvillage.ca/betafpv-lava-4s-550mah-75c-xt30-lipo-2pcs/ | LAVA 4S 550: 56.5 g |
| https://www.racedayquads.com/products/gaoneng-gnb-22-2v-6s-550mah-90c-lipo-micro-battery-long-type-xt30 | GNB 6S 550: 85 g, $14.99, pre-order |
| https://racedayquads.com/products/gaoneng-gnb-22-2v-6s-450mah-80c-lipo-micro-battery-long-type-xt30 | GNB 6S 450: $24.99, mass not listed |
| https://wrekd.com/products/gnb-650mah-22-2v-6s-80c-xt30-lipo-battery | GNB 6S 650: 124 g |
| https://imrbatteries.com/products/molicel-p30b-18650-3000mah-30a-battery | P30B: ~47 g per cell |
| https://www.unmannedtechshop.co.uk/products/flywoo-explorer-molicell-p45b-21700-3s1p-4500mah-lionpack-battery | P45B 3S1P pack: 224.3 g |
| https://oscarliang.com/flywoo-explorer-lr/ | Explorer LR: 163 g, 242 g AUW; 8 / 12 / 28 min measured; 50 km/h cruise |
| https://www.unmannedtechshop.co.uk/blogs/knowledge-base/flywoo-explorer-lr-4-sub-250g-long-range-micro-fpv-guide | Explorer LR 4: 154 g; 5-8 / 25-30 min |
| https://oscarliang.com/geprc-smart-35/ | Smart 35: 150 g dry; 6 / 7-8 / 4-5 min measured |
| https://fpv24.com/en/blog/40/geprcsmart35 | Smart 35: ~4-5 min |
| https://www.fpvfaster.com.au/products/dji-o4-air-unit | O4 Air Unit: 8.2 g, 4K60, 3.7-13.2 V, RockSteady/Gyroflow, AU$189 |
| https://www.adorama.com/DJIO4A.html | O4 Air Unit modes, Gyroflow, no longer available |
| https://www.dji.com/fi/o4-air-unit | O4 Air Unit: 8.2 g, 4K60; O4 Pro: 4K120 |
| https://www.getfpv.com/drone-brands/dji/dji-o4-air-unit-pro.html | O4 Pro: 32 g, $289, in stock |
| https://oscarliang.com/runcam-thumb-2 | Thumb 2: 27.8 g, 4K60, Gyroflow, $99 |
| https://www.racedayquads.com/products/runcam-thumb-2-4k-hd-action-camera | Thumb 2: 27 g, $119.99 |
| https://shop.runcam.com/runcam-thumb-pro | Thumb Pro W: 16 g, 4K30, Gyroflow, $99.99 |
| https://www.insta360.com/specs/go3s | GO 3S: 39.1 g, 4K30 |
| https://www.scan.co.uk/products/insta360-go-ultra-standard-bundle-midnight-black-4k60fps-1080p240fps-megaview-fov-flowstate-stabilis | GO Ultra: 53 g, 4K60, £388.99, in stock |
| https://pyrodrone.com/collections/all-products/products/geprc-naked-gopro-hero-11-camera | Naked Hero 11: 46.7 g, $828.99, sold out |
| https://oscarliang.com/caddx-walnut/ | Caddx Walnut: 60 g |
| https://raspberrypi.com/products/camera-module-3 | Camera Module 3: dimensions, 1080p50, FOV, from $25 |
| https://welectron.com/Official-Raspberry-Pi-Camera-Module-3-Wide | Camera Module 3 Wide: €35.90, in stock |
| https://www.unmannedtechshop.co.uk/blogs/knowledge-base/geprc-cinebot35-o4-pro-cinewhoop-review | CineBot35: 583 g, 140-150 km/h (attributed to Oscar Liang) |
| https://www.unmannedtechshop.co.uk/de/blogs/knowledge-base/fpv-drone-top-speed-how-fast-real-world-by-build-class | Speed measurement caveats; no 3 in figures |
| https://blog.unmanned.tech/best-cinewhoops-2026-complete-guide/ | Typical 3 in flight time; ducts trade speed for safety |
| https://oscarliang.com/tag/sub250/ | Existence of the 3 in O4 buyer's guide (10 Oct 2025); no figures in excerpt |
| https://drdrone.ca/pages/dji-mini-5-pro-technical-specifications | Mini 5 Pro: 249.9 g, 36 / 52 min, 18 / 19 m/s |
| https://robertscamera.com/dji-neo-2-fly-more-combo | Neo 2: 135 g, 18 / 17 min, 16 m/s Manual |
| https://www.notebookcheck.net/Up-to-118-mph-Extremely-fast-drone-with-DJI-technology-and-FPV-goggles-now-available.1132795.0.html | 118 mph is an iFlight 5 in 6S claim (not sub-250) |
