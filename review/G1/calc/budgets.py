#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Gate G1 budgets for MicroScout: weight, thrust-to-weight, power, flight time,
prop clearance, charger/shunt/MOSFET calculations, I2C timing and parts cost.

Every input is tagged:
  SOURCED    - value read from the cited page (datasheet, vendor listing, test)
  ESTIMATE   - engineering estimate; method stated; replace with measurement
  ASSUMPTION - design choice or generic material constant; human to confirm
Run:  python3 review/G1/calc/budgets.py   (writes review/G1/budgets.md)
No result here is a measurement. All outputs are DRAFT - UNVERIFIED.
"""
import csv
import math
import pathlib
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE.parent / "budgets.md"


@dataclass
class V:
    value: float
    unit: str
    kind: str          # SOURCED / ESTIMATE / ASSUMPTION
    source: str
    lo: float = None   # optional range
    hi: float = None

    def rng(self):
        lo = self.value if self.lo is None else self.lo
        hi = self.value if self.hi is None else self.hi
        return lo, hi


# --------------------------------------------------------------------------
# Sources (short keys used in tables)
SRC = {
    "S1": "ESP32-S3-WROOM-1 datasheet v1.8 Table 6-4 https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf",
    "S2": "BMI270 datasheet https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi270-ds000.pdf",
    "S3": "BMP390 datasheet (drone use case) https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf",
    "S4": "QMC5883P datasheet https://www.qstcorp.com/upload/pdf/202512/2C939E5AA0704285BC3BE71132B8629B.pdf",
    "S5": "VL53L1X datasheet https://www.st.com/resource/en/datasheet/vl53l1x.pdf",
    "S6": "VL53L5CX datasheet https://www.st.com/resource/en/datasheet/vl53l5cx.pdf",
    "S7": "PMW3901MB datasheet (Bitcraze-hosted) https://wiki.bitcraze.io/_media/projects:crazyflie2:expansionboards:pot0189-pmw3901mb-txqt-ds-r1.00-200317_20170331160807_public.pdf",
    "S8": "INA226 datasheet https://www.ti.com/lit/ds/symlink/ina226.pdf",
    "S9": "OV2640 datasheet (UCTronics copy) https://www.uctronics.com/download/cam_module/OV2640DS.pdf",
    "S10": "WS2812B-2020 datasheet (Mouser copy) https://www.mouser.com/pdfDocs/WS2812B-2020_V10_EN_181106150240761.pdf",
    "S11": "MLT-5020 listing https://jlcpcb.com/partdetail/Jiangsu_HuanengElec-MLT5020/C94598",
    "S12": "TPS63802 datasheet Fig 10-5 https://www.ti.com/lit/ds/symlink/tps63802.pdf",
    "S13": "TPS61023 datasheet Fig 6-1 https://www.ti.com/lit/ds/symlink/tps61023.pdf",
    "S14": "GNB 660 mAh 1S HV listing https://www.gaoneng.shop/products/gaoneng-gnb-lihv-1s-3.8v-660mah-90c-ph2.0-cabled-lipo-battery",
    "S15": "8520 vendor listings: xyzhobby 4.5 g https://xyzhobby.com/product/15276/ ; SpeedyFPV 5 g https://speedyfpv.com/products/usaq-8520-coreless-brushed-motor-set-53-000rpm-with-2cw-2ccw-65mm-propellers ; iFuture 5.0-5.5 g https://ifuturetech.org/product/8520-magnetic-micro-coreless-motor-for-micro-quadcopters/",
    "S16": "Gemfan 65 mm prop 0.5 g https://www.getfpv.com/gemfan-65mm-micro-propellers-1mm-shaft-set-of-8.html",
    "S17": "BetaFPV ELRS Lite 0.46 g https://betafpv.com/collections/rx/products/elrs-lite-receiver ; RadioMaster RP1 V2 2.2 g https://radiomasterrc.com/products/rp1-expresslrs-2-4ghz-nano-receiver",
    "S18": "Crazyflie 2.1 datasheet (29 g, 250 mAh 7.1 g battery) https://www.bitcraze.io/documentation/hardware/crazyflie_2_1/crazyflie_2_1-datasheet.pdf ; BetaFPV 7x16 motor 2.95 g https://betafpv.com/products/7x16mm-19000kv-brushed-motors-2cw-2ccw",
    "S19": "remma.net 8x20 motor tests citing ~33-36 gf with 60 mm props on LiPo https://www.remma.net/?p=1243 (secondhand; not 55 mm)",
    "S20": "Not Black Magic motor test stand: generic 8520 + Hubsan H107 prop, 4-5 g/W at 3.5-4.2 V https://notblackmagic.com/projects/motor-test-stand/",
    "S21": "8520 current: iFuture rated load ~1.6-1.8 A; RIC-8520D rated 2.27 A, stall 15.1 A https://www.ricmotor.com/details/8520-coreless-motor ; IntoFPV measured stall 10.57 A https://intofpv.com/t-racerstar-8520-motors-vs-bg-cheapies",
    "S22": "BQ24074 datasheet (K_ISET 890 A*Ohm typ, 797-975) https://www.ti.com/lit/ds/symlink/bq24074.pdf",
    "S23": "AO3400A datasheet (Rds(on) max 48 mOhm at Vgs 2.5 V) https://www.aosmd.com/res/datasheets/AO3400A.pdf",
    "S24": "DMP2008UFG datasheet (9.8 mOhm max at Vgs -2.5 V) https://www.diodes.com/datasheet/download/DMP2008UFG.pdf",
    "S25": "UM2884 (~84 kB VL53L5CX firmware over I2C) https://www.st.com/resource/en/user_manual/um2884-a-guide-to-using-the-vl53l5cx-multizone-timeofflight-ranging-sensor-with-wide-field-of-view-ultra-lite-driver-uld-stmicroelectronics.pdf",
    "S26": "RotorBuilds 27142: 100 mm 8520 build, 59-65 g AUW, 5-6 min on 1S 650 mAh https://rotorbuilds.com/build/27142",
    "S27": "JST PH datasheet (2 A AC/DC, AWG24) https://www.jst-mfg.com/product/pdf/eng/ePH.pdf ; BetaFPV BT2.0 vendor claim 9 A continuous https://betafpv.com/products/bt2-0-1s-whoop-cable-pigtail",
}

# --------------------------------------------------------------------------
# Geometry / design assumptions
MOTOR_TO_MOTOR_MM = V(95, "mm", "ASSUMPTION", "brief: 90-100 mm; 95 mm chosen (D-019)")
PROP_MM = V(55, "mm", "ASSUMPTION", "brief: 55-65 mm; 55 mm chosen (D-019)")
V_NOM = V(3.7, "V", "ASSUMPTION", "1S nominal voltage used for current conversion")
CAP_MAH = V(660, "mAh", "SOURCED", "S14")
USABLE_FRAC = V(0.80, "-", "ASSUMPTION", "land with ~20% remaining; human to set from LiPo practice")
HV_DERATE = V(0.90, "-", "ESTIMATE", "LiHV pack charged only to 4.2 V (D-013) delivers less than rated capacity; reduction unquantified - placeholder")

# PCB weight inputs
PCB_CORE_MM = (40, 40)          # central body (ASSUMPTION; settled at G3)
ARM_MM = (25, 9)                # each arm incl. motor pad: corner at 28.3 mm + 25 mm reaches past the 47.5 mm motor radius (ASSUMPTION)
PCB_THK_CM = 0.10               # 1.0 mm board (brief)
FR4_DENSITY = V(1.85, "g/cm3", "ASSUMPTION", "typical FR-4 laminate density; confirm for fab's laminate")
CU_THK_UM = 35 * 2 + 17.5 * 2   # 1 oz outer, 0.5 oz inner (ASSUMPTION; stackup at G3)
CU_COVER = 0.6                  # average copper coverage fraction (ESTIMATE)
CU_DENSITY = 8.96               # g/cm3, copper (material constant)

# Printed parts inputs (PLA)
PLA_DENSITY = V(1.24, "g/cm3", "ASSUMPTION", "typical PLA; check filament spec")
CANOPY = dict(w=50, l=64, h=16, wall=0.8)           # mm; length set by the 58 mm battery + margin (ESTIMATE)
GUARD = dict(clear=3.0, ring_t=1.0, ring_h=4.0)     # mm: radial clearance, wall, height (ESTIMATE)


def pcb_mass():
    area_cm2 = (PCB_CORE_MM[0] * PCB_CORE_MM[1] + 4 * ARM_MM[0] * ARM_MM[1]) / 100.0
    fr4 = area_cm2 * PCB_THK_CM * FR4_DENSITY.value
    cu = area_cm2 * (CU_THK_UM * 1e-4) * CU_COVER * CU_DENSITY
    return area_cm2, fr4, cu


def printed_mass():
    c = CANOPY
    # open-bottom box shell surface ~ top + 4 sides
    surf_mm2 = c["w"] * c["l"] + 2 * (c["w"] + c["l"]) * c["h"]
    canopy_g = surf_mm2 * c["wall"] / 1000.0 * PLA_DENSITY.value
    d_ring = PROP_MM.value + 2 * GUARD["clear"]
    ring_vol_mm3 = math.pi * d_ring * GUARD["ring_t"] * GUARD["ring_h"]
    guards_g = 4 * ring_vol_mm3 / 1000.0 * PLA_DENSITY.value
    struts_g = 1.5   # ESTIMATE: 8 struts tying rings to canopy/arms
    feet_g = 1.0     # ESTIMATE
    holders_g = 4 * 0.5  # ESTIMATE: printed motor clamps
    return canopy_g, guards_g, struts_g, feet_g, holders_g, d_ring


def weight_table():
    area, fr4, cu = pcb_mass()
    canopy, guards, struts, feet, holders, d_ring = printed_mass()
    items = [
        ("Battery 1S 660 mAh HV (GNB)", V(15.5, "g", "SOURCED", "S14 (15.5 g +/-1)", 14.5, 16.5)),
        ("Motors 4x 8520", V(4 * 5.0, "g", "SOURCED", "S15 (4.5-5.5 g each, vendor-dependent)", 4 * 4.5, 4 * 5.5)),
        ("Props 4x 55 mm", V(4 * 0.5, "g", "ESTIMATE", "S16 is a 65 mm prop at 0.5 g; 55 mm weight UNCONFIRMED", 4 * 0.4, 4 * 1.0)),
        (f"PCB bare 1.0 mm FR-4 ({area:.1f} cm2) incl. copper", V(fr4 + cu, "g", "ESTIMATE",
            f"area x thickness x density ({FR4_DENSITY.value} g/cm3) + copper {CU_THK_UM:.0f} um x {CU_COVER:.0%} coverage", (fr4 + cu) * 0.85, (fr4 + cu) * 1.2)),
        ("Electronic components incl. ESP32 module", V(7.0, "g", "ESTIMATE",
            "Crazyflie 2.1 (S18): 29 g - 7.1 g battery - 4x~2.95 g motors = ~10 g for PCB+parts+mounts; this board has more parts", 5.0, 10.0)),
        ("Camera module OV2640 + FPC", V(2.0, "g", "ESTIMATE", "UNCONFIRMED; weigh chosen module", 1.0, 3.0)),
        ("ELRS receiver", V(0.46, "g", "SOURCED", "S17 (Lite 0.46 g; RP1 2.2 g)", 0.46, 2.2)),
        ("Canopy shell (PLA)", V(canopy, "g", "ESTIMATE", f"open box shell {CANOPY['w']}x{CANOPY['l']}x{CANOPY['h']} mm, {CANOPY['wall']} mm wall, PLA {PLA_DENSITY.value} g/cm3", canopy * 0.7, canopy * 1.4)),
        (f"Prop guards 4 rings (dia {d_ring:.0f} mm)", V(guards, "g", "ESTIMATE", f"pi x D x {GUARD['ring_t']} x {GUARD['ring_h']} mm per ring", guards * 0.7, guards * 1.5)),
        ("Guard struts", V(struts, "g", "ESTIMATE", "8 struts", 1.0, 3.0)),
        ("Landing feet", V(feet, "g", "ESTIMATE", "4 feet", 0.5, 1.5)),
        ("Motor holders (printed)", V(holders, "g", "ESTIMATE", "4 clamps", 1.0, 3.0)),
        ("Battery cradle (printed)", V(1.5, "g", "ESTIMATE", "holds 58x18x7.8 mm pack under the board", 1.0, 2.5)),
        ("Battery leads, strap, fasteners, solder", V(2.0, "g", "ESTIMATE", "allowance", 1.0, 3.5)),
    ]
    return items


def main():
    L = []
    w = L.append
    w("STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1")
    w("")
    w("# G1 budgets (generated by `review/G1/calc/budgets.py` - do not hand-edit)")
    w("")
    w("Tags: **SOURCED** = read from the cited page; **ESTIMATE** = engineering estimate (method given, replace with a measurement); "
      "**ASSUMPTION** = design choice or generic constant. Nothing here is measured. Source keys (S1...) are listed at the end.")
    w("")

    # ---------------- Weight
    items = weight_table()
    tot = sum(v.value for _, v in items)
    tlo = sum(v.rng()[0] for _, v in items)
    thi = sum(v.rng()[1] for _, v in items)
    w("## 1. Weight budget")
    w("")
    w("| Item | Nominal (g) | Range (g) | Tag | Basis |")
    w("|---|---:|---:|---|---|")
    for name, v in items:
        lo, hi = v.rng()
        w(f"| {name} | {v.value:.1f} | {lo:.1f}-{hi:.1f} | {v.kind} | {v.source} |")
    w(f"| **Takeoff weight** | **{tot:.1f}** | **{tlo:.1f}-{thi:.1f}** | CALC | sum |")
    w("")
    w(f"Formula: W_takeoff = sum(items). Nominal {tot:.1f} g vs brief target < 80 g; worst case {thi:.1f} g. "
      f"Reference point: a 100 mm 8520 build flew at 59-65 g AUW on 1S 650 mAh (S26).")
    w("")

    # ---------------- Thrust to weight
    w("## 2. Thrust-to-weight (T/W)")
    w("")
    w("No measured static thrust for an 8520 with a **55 mm** prop at ~3.7 V was found. The only figure is a secondhand "
      "~33-36 gf per motor with **60 mm** props (S19). Three scenarios bracket it; 28 gf is an ASSUMED lower value for the smaller 55 mm prop.")
    w("")
    w("Formula: T/W = (4 x T_motor) / W_takeoff. Hover throttle fraction (thrust) ~ W / (4 x T_motor).")
    w("")
    w("| T per motor (gf) | Tag | T/W at nominal {:.1f} g | T/W at worst {:.1f} g | T/W at 80 g |".format(tot, thi))
    w("|---:|---|---:|---:|---:|")
    for t, tag in ((28, "ASSUMPTION"), (33, "SOURCED S19 (60 mm)"), (36, "SOURCED S19 (60 mm)")):
        w(f"| {t} | {tag} | {4*t/tot:.2f} | {4*t/thi:.2f} | {4*t/80:.2f} |")
    w("")
    w(f"Reading: T/W is {4*28/tot:.1f}-{4*36/tot:.1f} at nominal weight and drops to {4*28/thi:.1f} at worst-case weight. Below ~2 leaves thin margin for altitude-hold and gust rejection "
      "(ASSUMPTION: common rule of thumb, not a requirement in the brief). This is the main G1 risk - see open question OQ-3.")
    w("")

    # ---------------- Electronics power
    w("## 3. Power budget")
    w("")
    w("### 3a. 3.3 V rail (TPS63802 output)")
    w("")
    rail33 = [
        # name, I_peak_mA, I_avg_mA, kind, source
        ("ESP32-S3 module (Wi-Fi TX 802.11b 20.5 dBm peak)", 355, 200, "SOURCED peak / ESTIMATE avg", "S1 peak; average while streaming UNCONFIRMED - measure at G6"),
        ("BMI270 IMU (performance mode, via 1.8 V LDO)", 0.97, 0.97, "SOURCED", "S2"),
        ("BMP390 (drone use case)", 0.57, 0.57, "SOURCED", "S3"),
        ("QMC5883P (high-power mode 100 Hz)", 0.6, 0.6, "SOURCED", "S4"),
        ("4x VL53L1X (16 mA avg, 40 mA peak each)", 160, 64, "SOURCED", "S5"),
        ("VL53L5CX (313 mW at 3.3 V AVDD/IOVDD)", 313 / 3.3, 313 / 3.3, "SOURCED + CALC", "S6; I = P/V"),
        ("PMW3901 run mode (via 1.8 V LDO)", 9, 9, "SOURCED", "S7"),
        ("INA226", 0.33, 0.33, "SOURCED", "S8"),
        ("OV2640 (140 mW compressed) via 2.8 V/1.2 V LDOs", 140 / 1.2, 140 / 1.2, "SOURCED + ESTIMATE", "S9; worst case assumes all power on the 1.2 V LDO: I = 140 mW / 1.2 V"),
        ("Buzzer MLT-5020 (intermittent)", 100, 0, "SOURCED", "S11; excluded from average"),
    ]
    w("| Load | Peak (mA) | Average (mA) | Tag | Source / method |")
    w("|---|---:|---:|---|---|")
    pk = av = 0.0
    for n, p, a, k, s in rail33:
        pk += p
        av += a
        w(f"| {n} | {p:.1f} | {a:.1f} | {k} | {s} |")
    w(f"| **Total 3.3 V** | **{pk:.0f}** | **{av:.0f}** | CALC | sum |")
    w("")
    w(f"TPS63802 rating: 2 A for V_IN >= 2.3 V at V_OUT 3.3 V (S12) -> margin over peak = 2000 / {pk:.0f} = {2000/pk:.1f}x. "
      "The ESP32-S3 datasheet also requires a supply able to deliver >= 500 mA to the module.")
    eff33 = V(0.90, "-", "ESTIMATE", "S12 Fig 10-5 read ~88-92% at V_IN 3.6 V, 300-500 mA")
    p33_batt = 3.3 * av / 1000 / eff33.value
    w("")
    w(f"Battery-side power for 3.3 V average: P = 3.3 V x {av:.0f} mA / eta({eff33.value:.2f}) = **{p33_batt:.2f} W** "
      f"-> I = P / {V_NOM.value} V = **{p33_batt/V_NOM.value*1000:.0f} mA**.")
    w("")
    w("### 3b. 5 V rail (TPS61023 output)")
    w("")
    led_max = 4 * 3 * 16
    rail5 = [
        ("4x WS2812B-2020 at full white", led_max, 50, "SOURCED peak basis / ESTIMATE avg",
         "S10 tests each colour at 16 mA; full-white current not stated -> 3 x 16 mA per LED (CALC). Average assumes dim status lighting (ESTIMATE)"),
        ("ELRS receiver", 100, 100, "ESTIMATE", "UNCONFIRMED - no vendor current found; placeholder to replace from receiver spec or bench"),
    ]
    w("| Load | Peak (mA) | Average (mA) | Tag | Source / method |")
    w("|---|---:|---:|---|---|")
    pk5 = av5 = 0.0
    for n, p, a, k, s in rail5:
        pk5 += p
        av5 += a
        w(f"| {n} | {p:.0f} | {a:.0f} | {k} | {s} |")
    w(f"| **Total 5 V** | **{pk5:.0f}** | **{av5:.0f}** | CALC | sum |")
    eff5 = V(0.85, "-", "ESTIMATE", "S13 Fig 6-1 read ~80-90% at 0.2-0.5 A")
    p5_batt = 5.0 * av5 / 1000 / eff5.value
    w("")
    w(f"Battery-side: P = 5 V x {av5:.0f} mA / {eff5.value:.2f} = **{p5_batt:.2f} W** -> **{p5_batt/V_NOM.value*1000:.0f} mA** at {V_NOM.value} V. "
      f"Boost input current at peak and V_IN = 3.0 V: 5 x {pk5:.0f} / (0.85 x 3.0) = {5*pk5/(0.85*3.0):.0f} mA (TPS61023 switch limit 3.7 A valley; usable output current at 3.0 V UNCONFIRMED - check at G2).")
    w("")

    # ---------------- Motor power, hover, flight time
    w("### 3c. Motors, hover and flight time")
    w("")
    w("Hover power uses a measured thrust efficiency for a generic 8520 + Hubsan H107 prop: 4-5 g/W at 3.5-4.2 V (S20). Not our prop - ESTIMATE.")
    w("")
    w("Formulas: P_hover = W / eta_gW;  I_motors = P_hover / V_nom;  I_total = I_motors + I_3V3,batt + I_5V,batt;  "
      "t_flight = (C x HV_derate x usable) / I_total.")
    w("")
    w("| W (g) | eta (g/W) | P_hover (W) | I_motors (A) | I_total (A) | Flight time (min) |")
    w("|---:|---:|---:|---:|---:|---:|")
    elec_a = (p33_batt + p5_batt) / V_NOM.value
    flight = {}
    for W in (tot, thi, 80.0):
        for eta in (5.0, 4.0):
            P = W / eta
            Im = P / V_NOM.value
            It = Im + elec_a
            t = CAP_MAH.value / 1000 * HV_DERATE.value * USABLE_FRAC.value / It * 60
            flight[(round(W, 1), eta)] = (It, t)
            w(f"| {W:.1f} | {eta:.0f} | {P:.1f} | {Im:.2f} | {It:.2f} | {t:.1f} |")
    w("")
    w(f"Electronics at battery: {elec_a:.2f} A (3.3 V + 5 V averages above). Capacity {CAP_MAH.value:.0f} mAh (S14) x {HV_DERATE.value:.2f} HV derate (ESTIMATE, D-013) x usable {USABLE_FRAC.value:.0%} (ASSUMPTION). "
      "Cross-check: S26 reports 5-6 min for a 59-65 g 8520 build without camera/sensors, consistent in magnitude.")
    w("")
    w("### 3d. Peak battery current (sizing connector, fuse, traces, FETs)")
    w("")
    i_full_lo, i_full_hi = 1.6, 2.27
    peak_lo = 4 * i_full_lo + pk / 1000 / eff33.value * 3.3 / 3.0 + pk5 / 1000 * 5 / (0.85 * 3.0)
    peak_hi = 4 * i_full_hi + pk / 1000 / eff33.value * 3.3 / 3.0 + pk5 / 1000 * 5 / (0.85 * 3.0)
    w(f"Per-motor full-throttle current 1.6-2.27 A (vendor/maker figures, S21). Electronics peak referred to a 3.0 V battery. "
      f"I_peak = 4 x I_motor + I_3V3,pk x 3.3/(0.90 x 3.0) + I_5V,pk x 5/(0.85 x 3.0) = **{peak_lo:.1f}-{peak_hi:.1f} A**. "
      "Motor stall can reach 10.6 A (measured, S21) to 15.1 A (maker table, S21) per motor for short transients (start-up, blocked prop).")
    w("")
    w(f"Connector check: JST-PH is rated 2 A per contact (S27). Estimated hover current {flight[(round(tot,1),5.0)][0]:.1f}-{flight[(round(tot,1),4.0)][0]:.1f} A and peak {peak_lo:.1f}-{peak_hi:.1f} A "
      "exceed that rating. BT2.0 is claimed 9 A continuous by its vendor (no formal datasheet, S27). -> Open question OQ-2 / D-011.")
    w("")

    # ---------------- Component calcs
    w("## 4. Component calculations")
    w("")
    kiset, klo, khi = 890.0, 797.0, 975.0
    i_target = 0.5
    r_iset = kiset / i_target
    w("### 4a. BQ24074 charge current (S22)")
    w("")
    w(f"I_CHG = K_ISET / R_ISET, K_ISET = {kiset:.0f} A*Ohm typ ({klo:.0f}-{khi:.0f}). Target {i_target*1000:.0f} mA "
      f"(~{i_target/(CAP_MAH.value/1000):.2f}C for {CAP_MAH.value:.0f} mAh, ASSUMPTION: conservative below 1C). "
      f"R_ISET = {kiset:.0f}/{i_target} = {r_iset:.0f} Ohm -> nearest E96 **1.78 kOhm**. "
      f"Resulting I_CHG range = {klo/1780*1000:.0f}-{khi/1780*1000:.0f} mA (typ {kiset/1780*1000:.0f} mA). "
      "R_ISET must be within 590 Ohm-8.9 kOhm (datasheet) - OK. Input current limit: USB500 mode via EN1/EN2 (ASSUMPTION: no Type-C current advertisement is read).")
    w("")
    w("### 4b. INA226 shunt (S8)")
    w("")
    vsh = 0.08192
    imax_design = 12.0
    r_max = vsh / imax_design
    r_sel = 0.005
    w(f"Full-scale shunt voltage +/-81.92 mV. Design max measurable current {imax_design:.0f} A (ASSUMPTION: above the ~{peak_hi:.0f} A full-throttle estimate). "
      f"R_shunt <= 81.92 mV / {imax_design:.0f} A = {r_max*1000:.2f} mOhm -> select **5 mOhm**: range = 81.92/5 = {vsh/r_sel:.1f} A, "
      f"LSB = 2.5 uV / 5 mOhm = {2.5e-6/r_sel*1000:.2f} mA. Dissipation P = I^2 R: at 5 A = {25*r_sel:.3f} W, at 9 A = {81*r_sel:.3f} W, "
      f"at 16 A transient = {256*r_sel:.2f} W -> choose a >= 1 W part at G2.")
    w("")
    w("### 4c. Motor MOSFET AO3400A (S23)")
    w("")
    rds = 0.048
    for i in (1.0, 1.6, 2.27):
        w(f"- I = {i:.2f} A: P = I^2 x 48 mOhm = {i*i*rds*1000:.0f} mW (worst-case Rds(on) max at Vgs 2.5 V; actual gate drive 3.3 V gives lower Rds - curve value at 3.3 V UNCONFIRMED).")
    w("- Stall 10.6 A transient: P = 5.4 W - must be short; firmware ramp limits and the 15 A fuse bound it. SOT-23 thermal resistance check at G3.")
    w("")
    w("### 4d. Series drop in the battery path (S24)")
    w("")
    r_fet = 0.0098
    for i in (5.0, 9.0):
        drop = i * (2 * r_fet + r_sel)
        w(f"- {i:.0f} A through Q1 + Q2 (2 x 9.8 mOhm max at -2.5 V) + 5 mOhm shunt: V_drop = {i:.0f} x {2*r_fet*1000+r_sel*1000:.1f} mOhm = **{drop*1000:.0f} mV** "
          f"(+ fuse, connector, traces - UNCONFIRMED); FET loss {i*i*r_fet*1000:.0f} mW each.")
    w("")
    w("### 4e. Prop clearance (adjacent props on a square X frame)")
    w("")
    w("Adjacent motor spacing s = D / sqrt(2) (D = diagonal motor-to-motor). Tip gap g = s - d_prop.")
    w("")
    w("| D (mm) | s (mm) | gap, 55 mm props | gap, 65 mm props |")
    w("|---:|---:|---:|---:|")
    for D in (90, 95, 100):
        s = D / math.sqrt(2)
        w(f"| {D} | {s:.1f} | {s-55:.1f} | {s-65:.1f} |")
    w("")
    w("Guard rings need radial clearance plus wall thickness per prop; 65 mm props leave <= 5.7 mm between tips even at 100 mm, so guards would overlap. -> 55 mm at 95 mm (D-019).")
    w("")
    w("### 4f. VL53L5CX firmware upload time on a 400 kHz I2C bus (S25)")
    w("")
    nbytes = 84 * 1024
    t = nbytes * 9 / 400e3
    w(f"t ~ bytes x 9 bits (8 data + ACK) / f_SCL = {nbytes} x 9 / 400 kHz = **{t:.2f} s** per boot (ignores address/command overhead; ESTIMATE). "
      "The bus runs at 400 kHz because VL53L1X and QMC5883P are 400 kHz devices.")
    w("")

    # ---------------- Cost
    w("## 5. Parts cost (per drone, from bom/drone-bom-g1.csv)")
    w("")
    rows = [l for l in (REPO / "bom" / "drone-bom-g1.csv").read_text().splitlines() if not l.startswith("#")]
    known = 0.0
    missing = []
    w("| Ref | Part | Qty | Unit USD | Line USD |")
    w("|---|---|---:|---:|---:|")
    for r in csv.DictReader(rows):
        if r["status"] not in ("SELECTED", "CONDITIONAL"):
            continue
        q = int(r["qty"])
        if r["unit_usd"]:
            u = float(r["unit_usd"])
            known += u * q
            w(f"| {r['ref']} | {r['mpn']} | {q} | {u:.3f} | {u*q:.2f} |")
        else:
            missing.append(f"{r['ref']} {r['mpn']}")
    w(f"| | **Subtotal of priced lines** | | | **{known:.2f}** |")
    w("")
    w(f"Prices are the LCSC break covering the 5-drone quantity, as listed per line in the BOM (`price_break` column), seen 2026-10-04 (they move daily); no shipping or tariffs. "
      f"Not priced (UNCONFIRMED): {'; '.join(missing)}; plus all passives, PCB fabrication, assembly and JLCPCB extended-part fees.")
    w("")
    w(f"**Finding:** priced lines alone are ${known:.0f} per drone against the ~$75 target, before the battery, barometer, camera, props, passives, "
      "PCB and assembly. The target is very likely exceeded - open question OQ-5 lists the cost levers.")
    w("")
    w("## Sources")
    w("")
    for k, s in SRC.items():
        w(f"- **{k}**: {s}")
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}  weight nominal {tot:.1f} g  range {tlo:.1f}-{thi:.1f} g  cost subtotal ${known:.2f}")


if __name__ == "__main__":
    main()
