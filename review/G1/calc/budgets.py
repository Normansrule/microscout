#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2 (G1 rev B approved 2026-10-07; updated for the G2 schematics)
# SPDX-License-Identifier: MIT
"""Gate G1 rev B budgets for MicroScout (2S brushless, ducted durable frame).

Weight, thrust-to-weight, agility (flip), power, hover time, peak current,
component sizing, impact energy and parts cost.

Every input is tagged:
  SOURCED    - value read from the cited page (datasheet, vendor listing, test)
  ESTIMATE   - engineering estimate; method stated; replace with measurement
  ASSUMPTION - design choice or generic constant; human to confirm
Run:  python3 review/G1/calc/budgets.py   (writes review/G1/budgets.md)
No result here is a measurement. All outputs are DRAFT - UNVERIFIED.
Rev A (brushed 8520, 1S) is preserved at git tag g1-rev-a.
"""
import csv
import math
import pathlib
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE.parent / "budgets.md"
REV = "rev B"


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
SRC = {
    "S1": "ESP32-S3-WROOM-1 datasheet v1.8 Table 6-4 https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf",
    "S2": "ICM-42688-P datasheet v1.6 (0.88 mA 6-axis low-noise) https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ds-000347-icm-42688-p-v1.6.pdf",
    "S3": "BMP390 datasheet (drone use case 570 uA) https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf",
    "S4": "QMC5883P datasheet https://www.qstcorp.com/upload/pdf/202512/2C939E5AA0704285BC3BE71132B8629B.pdf",
    "S5": "VL53L1X datasheet (16 mA avg, 40 mA peak) https://www.st.com/resource/en/datasheet/vl53l1x.pdf",
    "S6": "VL53L5CX datasheet (313 mW at 3.3 V) https://www.st.com/resource/en/datasheet/vl53l5cx.pdf",
    "S7": "PMW3901MB datasheet (Bitcraze-hosted, 9 mA run) https://wiki.bitcraze.io/_media/projects:crazyflie2:expansionboards:pot0189-pmw3901mb-txqt-ds-r1.00-200317_20170331160807_public.pdf",
    "S8": "INA226 datasheet https://www.ti.com/lit/ds/symlink/ina226.pdf",
    "S9": "OV2640 datasheet (UCTronics copy, 140 mW compressed) https://www.uctronics.com/download/cam_module/OV2640DS.pdf",
    "S10": "WS2812B-2020 datasheet (Mouser copy) https://www.mouser.com/pdfDocs/WS2812B-2020_V10_EN_181106150240761.pdf",
    "S11": "MLT-5020 listing (100 mA) https://jlcpcb.com/partdetail/Jiangsu_HuanengElec-MLT5020/C94598",
    "S12": "TPS62162 product page (3-17 V in, 1 A, fixed 3.3 V) https://www.ti.com/product/TPS62162 - efficiency at our load UNCONFIRMED",
    "S13": "TPS62133 product page (3-17 V, 3 A); LCSC lists TPS62133RGTR as fixed 5 V https://www.lcsc.com/product-detail/C73973.html - efficiency UNCONFIRMED",
    "S14": "GNB 2S 550 mAh 100C LiHV XT30 listing: 29 g +/-1, 12x18x69 mm, JST-XH charge plug https://www.fpvfaster.com.au/products/gaoneng-gnb-550mah-2s-100c-7-6v-lihv-lipo-battery-long-type-xt30-dg",
    "S15": "Happymodel EX1103 11000KV vendor table (retailer copy): 3.8 g; 7.4 V, Gemfan 2023 3-blade: 81.8 g at 5.04 A (2.19 g/W), max 121.9 g at 9.20 A (68.1 W, 1.79 g/W) https://druav.com/en-us/products/happymodel-ex1103-brushless-motor",
    "S16": "Prop weights: Gemfan 2015 2-blade 0.5 g https://www.getfpv.com/gemfan-durable-2015-2-blade-propeller-set-of-8-1-5mm-shaft.html ; HQProp T2x2x3 0.75 g https://www.unmannedtechshop.co.uk/products/hqprop-durable-prop-t2x2x3-grey",
    "S17": "BetaFPV ELRS Lite 0.46 g https://betafpv.com/collections/rx/products/elrs-lite-receiver ; RadioMaster RP1 V2 2.2 g https://radiomasterrc.com/products/rp1-expresslrs-2-4ghz-nano-receiver",
    "S18": "Reference: Happymodel Mobula8 85 mm, 2S, EX1103, 43 g dry with camera https://www.getfpv.com/micro-quadcopters/micro-rtf-bnf/happymodel-mobula8-1-2s-85mm-analog-drone.html ; BetaFPV Meteor85 43.85 g dry, 2S 450 mAh, 7 min claimed https://betafpv.com/collections/all/products/meteor85-brushless-whoop-quadcopter-2022",
    "S19": "Commercial PP whoop frames 5.8-7.8 g at 80 mm (Meteor75 Pro 7.73 g) https://www.getfpv.com/betafpv-meteor75-pro-brushless-whoop-frame-black.html",
    "S20": "Betaflight rate guide: freestyle 850-1200 deg/s https://betaflight.com/docs/wiki/guides/current/Rate-Calculator",
    "S21": "BQ25887 product page: 2 A boost, 93.4 % at 5 V in / 7.6 V / 1 A, balancing up to 400 mA https://www.ti.com/product/BQ25887",
    "S22": "HL 60N03D: 30 V, 60 A, 4.7 mOhm, PDFN3333 https://lcsc.com/product-detail/MOSFETs_HL-60N03D_C7471100.html (gate-drive condition of the 4.7 mOhm UNCONFIRMED)",
    "S23": "Amass XT30: 15 A continuous, 30 A peak (retailer listing) https://shop.pimoroni.com/products/amass-xt30-connector",
    "S24": "UM2884 (~84 kB VL53L5CX firmware over I2C) https://www.st.com/resource/en/user_manual/um2884-a-guide-to-using-the-vl53l5cx-multizone-timeofflight-ranging-sensor-with-wide-field-of-view-ultra-lite-driver-uld-stmicroelectronics.pdf",
    "S25": "Drop tests: IEC 60068-2-31 procedure run as 1000 mm falls https://stg.westpak.com/testing-services/reliability/tumble-testing/ ; MIL-STD-810 transit drop 1.22 m, 26 drops https://gorillacasestore.com/blogs/news/mil-std-810g-vs-810h-what-the-newer-drop-standard-adds",
    "S26": "HP MJF PA11 datasheet: 1.05 g/cm3, elongation 50 % XY / 35 % Z, Izod 5 kJ/m2 https://3dprinting.com/wp-content/uploads/2019/02/HP-PA-11-TDS-4AA7-0715ENE.pdf ; Bambu TPU 95A: 1.20 g/cm3, elongation >700 % https://polyalkemi.no/wp-content/uploads/2023/06/Bambu_TPU_95A_Technical_Data_Sheet.pdf",
    "S27": "Shunt 1 mOhm 2 W 2512 (HoJLR2512-2W-1mR) https://fat.lcsc.com/product-detail/Current-Sense-Resistors-Shunt-Resistors_Milliohm-HoJLR2512-2W-1mR-1-75ppm_C2924520.html",
    "S29": "FD6288Q gate driver: supply 5.0-20 V, 3.3/5 V logic (LCSC listing) https://lcsc.com/product-detail/Others_Fortior-Tech-FD6288Q_C328453.html",
    "S30": "Bitcraze Flow deck v2: 21x28x4 mm, 1.6 g, USD 55 (product page and datasheet Rev 1) https://www.bitcraze.io/products/flow-deck-v2/",
    "S28": "Academic collision data: FlexiQuad (405 g) undamaged at 3 and 4.5 m/s frontal hits https://arxiv.org/pdf/2511.05426",
}

# --------------------------------------------------------------------------
# Geometry and design assumptions
MOTOR_TO_MOTOR_MM = V(95, "mm", "ASSUMPTION", "brief: 90-100 mm; 95 mm kept (D-019 rev B)")
PROP_MM = V(52.2, "mm", "SOURCED", "Gemfan Hurricane 2023 3-blade: 52.17 mm per the Mobula8 listing (S18)")
DUCT_CLEAR_MM = 1.0       # radial prop-tip clearance (ASSUMPTION, checked at G5)
DUCT_WALL_MM = 0.9        # duct wall (ASSUMPTION)
DUCT_H_MM = 11.0          # duct height (ASSUMPTION)
V_NOM = V(7.4, "V", "ASSUMPTION", "2S nominal voltage used for current conversion")
CAP_MAH = V(550, "mAh", "SOURCED", "S14")
USABLE_FRAC = V(0.80, "-", "ASSUMPTION", "land with ~20 % remaining")
HV_DERATE = V(0.92, "-", "ESTIMATE", "LiHV pack charged to 8.4 V instead of 8.7 V (D-033) gives less than rated capacity; reduction unquantified - placeholder")

FR4_DENSITY = 1.85        # g/cm3, typical FR-4 (ASSUMPTION)
CU_DENSITY = 8.96         # g/cm3
PA11_DENSITY = 1.05       # S26
TPU_DENSITY = 1.20        # S26

FC_BOARD_MM = (40, 40)    # flight-controller board (ASSUMPTION; settled at G3)
ESC_BOARD_MM = (30, 30)   # 4-in-1 ESC board (ASSUMPTION; settled at G3)


def board_mass(dims, thk_cm=0.10, cu_um=105, cover=0.6):
    a = dims[0] * dims[1] / 100.0
    return a, a * thk_cm * FR4_DENSITY + a * cu_um * 1e-4 * cover * CU_DENSITY


def duct_frame_mass():
    """Ducted one-piece frame estimate: 4 duct rings + arms + centre tray + motor mounts (PA11)."""
    d_in = PROP_MM.value + 2 * DUCT_CLEAR_MM
    ring = math.pi * (d_in + DUCT_WALL_MM) * DUCT_WALL_MM * DUCT_H_MM          # mm3
    mount = 4 * 120.0          # motor boss + 3 spokes each (ESTIMATE, mm3)
    tray = 42 * 46 * 1.0 * 0.55  # perforated centre tray (ESTIMATE, mm3)
    links = 8 * 18 * 3 * 1.2   # duct-to-tray links (ESTIMATE, mm3)
    vol = 4 * ring + mount + tray + links
    return vol, vol / 1000 * PA11_DENSITY


CAD_REPORT = REPO / "mechanical" / "concept" / "out" / "concept_report.json"


def cad_masses():
    """Printed-part masses from the CadQuery concept model, if it has been built."""
    import json
    if CAD_REPORT.exists():
        parts = json.loads(CAD_REPORT.read_text())["parts"]
        return {k: v["mass_g"] for k, v in parts.items()}
    return {}


def weight_table():
    _, fc = board_mass(FC_BOARD_MM)
    _, esc = board_mass(ESC_BOARD_MM, cu_um=2 * 70 + 2 * 35)   # 2 oz outer for motor current (ASSUMPTION)
    fvol, frame = duct_frame_mass()
    cad = cad_masses()
    frame_basis = f"{fvol/1000:.1f} cm3 x {PA11_DENSITY} g/cm3 (hand estimate); commercial 80 mm PP frames 5.8-7.8 g (S19)"
    if "frame_pa11" in cad:
        frame = cad["frame_pa11"]
        frame_basis = f"CAD concept volume x {PA11_DENSITY} g/cm3 (mechanical/concept); commercial 80 mm PP frames 5.8-7.8 g (S19)"
    canopy = cad.get("canopy_tpu", 3.0) + cad.get("battery_strap", 0.8)
    canopy_basis = "CAD concept volume x 1.20 g/cm3 (canopy + strap)" if cad else "printed shell ~2.5 cm3 x 1.20 g/cm3"
    return [
        ("Battery 2S 550 mAh HV (GNB, XT30)", V(29.0, "g", "SOURCED", "S14 (29 g +/-1)", 28.0, 30.0)),
        ("Motors 4x EX1103 11000KV", V(4 * 3.8, "g", "SOURCED", "S15 (3.8 g each)", 4 * 3.7, 4 * 4.0)),
        ("Props 4x 2-inch 3-blade", V(2.6, "g", "ESTIMATE", "S16: 0.5 g (2-blade) to 0.75 g (3-blade) per prop", 2.0, 3.0)),
        ("Ducted frame (one piece, PA11)", V(frame, "g", "ESTIMATE", frame_basis, frame * 0.8, frame * 1.2)),
        ("Canopy + battery strap (TPU 95A)", V(canopy, "g", "ESTIMATE", canopy_basis, canopy * 0.8, canopy * 1.5)),
        ("Flight-controller PCB (bare, 4-layer)", V(fc, "g", "ESTIMATE", f"{FC_BOARD_MM[0]}x{FC_BOARD_MM[1]} mm x 1.0 mm FR-4 + copper", fc * 0.85, fc * 1.2)),
        ("FC components incl. ESP32 module", V(5.0, "g", "ESTIMATE", "module + sensors + charger + passives; weigh at G6", 3.5, 7.0)),
        ("ESC PCB (bare, 2 oz outer)", V(esc, "g", "ESTIMATE", f"{ESC_BOARD_MM[0]}x{ESC_BOARD_MM[1]} mm", esc * 0.85, esc * 1.2)),
        ("ESC components (4 MCU, 4 drivers, 24 FETs)", V(2.0, "g", "ESTIMATE", "commercial 12 A whoop AIOs weigh 2.7-5.1 g complete", 1.5, 3.0)),
        ("Camera + FPC", V(2.0, "g", "ESTIMATE", "UNCONFIRMED; weigh chosen module", 1.0, 3.0)),
        ("ToF satellite boards (3 side + 1 front) + wires", V(2.0, "g", "ESTIMATE", "4 small boards (G2: front sensor moved off the FC, D-052)", 1.3, 3.0)),
        ("Flow deck v2 (optical flow + down ToF)", V(1.6, "g", "SOURCED", "S30 (G2, D-047)", 1.6, 1.8)),
        ("ELRS receiver", V(0.46, "g", "SOURCED", "S17 (Lite 0.46 g; RP1 2.2 g)", 0.46, 2.2)),
        ("XT30 lead + motor wires", V(2.5, "g", "ESTIMATE", "allowance", 1.5, 3.5)),
        ("Soft-mount grommets + screws", V(1.2, "g", "ESTIMATE", "4 grommets, 4 M2 screws", 0.8, 2.0)),
    ]


# --------------------------------------------------------------------------
# Propulsion
T_MAX_TABLE_G = 121.9   # S15 max thrust per motor, 7.4 V, open prop
I_MAX_TABLE_A = 9.20    # S15 max current per motor
THRUST_SCENARIOS = (
    (85, "ASSUMPTION: -30 % for ducts + sag"),
    (100, "ASSUMPTION: battery sag to ~7 V"),
    (122, "SOURCED S15 vendor table, open prop"),
)
ETA_GW = (3.5, 2.5)            # hover efficiency bracket g/W (ESTIMATE: S15 gives 2.19 g/W at 82 g; hover is ~20 g/motor where small motors are typically more efficient)
I_MOTOR_FULL_A = (7.0, I_MAX_TABLE_A)   # per-motor full-throttle current (ASSUMPTION lower bound / S15)
MOTOR_TAU_S = V(0.030, "s", "ASSUMPTION", "first-order thrust response time of a 1103 motor; measure at G6")
RATE_TARGET_DPS = 1000         # S20 freestyle range 850-1200 deg/s

# --------------------------------------------------------------------------
# Electrical load tables (name, peak mA, average mA, tag, source)
RAIL33 = [
    ("ESP32-S3 module (Wi-Fi TX 802.11b 20.5 dBm peak)", 355, 200, "SOURCED peak / ESTIMATE avg", "S1 peak; average while streaming UNCONFIRMED - measure at G6"),
    ("ICM-42688-P IMU (6-axis low-noise)", 0.88, 0.88, "SOURCED", "S2"),
    ("BMP388 barometer (BMP390 drone-use-case figure)", 0.57, 0.57, "SOURCED", "S3; BMP388 fitted at G2 (D-045) - current UNCONFIRMED"),
    ("QMC5883P (high-power mode 100 Hz)", 0.6, 0.6, "SOURCED", "S4"),
    ("4x VL53L1X: 3 satellites + Flow deck (16 mA avg, 40 mA peak each)", 160, 64, "SOURCED", "S5"),
    ("VL53L5CX (313 mW at 3.3 V AVDD/IOVDD)", 313 / 3.3, 313 / 3.3, "SOURCED + CALC", "S6; I = P/V"),
    ("PMW3901 run mode (on the Flow deck, deck regulators)", 9, 9, "SOURCED", "S7"),
    ("INA226", 0.33, 0.33, "SOURCED", "S8"),
    ("OV2640 (140 mW compressed) via 2.8 V/1.2 V LDOs", 140 / 1.2, 140 / 1.2, "SOURCED + ESTIMATE", "S9; worst case I = 140 mW / 1.2 V"),
    ("Buzzer MLT-5020 (intermittent)", 100, 0, "SOURCED", "S11; excluded from average"),
]
LED_MAX_MA = 4 * 3 * 16
RAIL5 = [
    ("4x WS2812B-2020 at full white", LED_MAX_MA, 50, "SOURCED peak basis / ESTIMATE avg", "S10: 16 mA per colour -> 3 x 16 mA per LED (CALC); dim status average (ESTIMATE)"),
    ("ELRS receiver", 100, 100, "ESTIMATE", "UNCONFIRMED placeholder"),
]
RAILESC = [   # ESC board's own TPS62162 from VDRV since G2 (D-048)
    ("4x AT32F421 ESC MCUs", 80, 60, "ESTIMATE", "UNCONFIRMED - no datasheet current read yet; 15-20 mA each assumed"),
]
EFF33 = V(0.85, "-", "ESTIMATE", "TPS62162 7.4 V -> 3.3 V at ~0.5 A; datasheet curve not read (S12)")
EFFBOOST = V(0.85, "-", "ESTIMATE", "MT3608 boost VBAT -> 9.6 V VDRV at ~50 mA (G2, D-054); curve not read")
EFF5 = V(0.88, "-", "ESTIMATE", "TPS62133 7.4 V -> 5 V at 0.1-0.3 A; datasheet curve not read (S13)")


# --------------------------------------------------------------------------
# Helpers shared with tools/viz and software/microscout_sdk tests
def rail_totals(rail):
    return sum(r[1] for r in rail), sum(r[2] for r in rail)


def electronics_battery_current_a():
    _, av33 = rail_totals(RAIL33)
    _, aves = rail_totals(RAILESC)
    _, av5 = rail_totals(RAIL5)
    p = 3.3 * av33 / 1000 / EFF33.value + 3.3 * aves / 1000 / (EFF33.value * EFFBOOST.value) + 5.0 * av5 / 1000 / EFF5.value
    return p / V_NOM.value


def hover_total_current_a(weight_g, eta_gw):
    return weight_g / eta_gw / V_NOM.value + electronics_battery_current_a()


def flight_time_min(weight_g, eta_gw, cap_mah=None):
    cap = CAP_MAH.value if cap_mah is None else cap_mah
    return cap / 1000 * HV_DERATE.value * USABLE_FRAC.value / hover_total_current_a(weight_g, eta_gw) * 60


def weight_totals():
    items = weight_table()
    return (sum(v.value for _, v in items), sum(v.rng()[0] for _, v in items), sum(v.rng()[1] for _, v in items))


def inertia_estimate():
    """Point/slab estimate of Ixx, Iyy, Izz (kg m^2) about the centre of mass, including the
    height of each mass (battery on top). Heights are concept-model values (ESTIMATE)."""
    s = MOTOR_TO_MOTOR_MM.value / math.sqrt(2) / 1000 / 2      # motor x/y offset (m)
    items = dict(weight_table())
    m_rot = (items["Motors 4x EX1103 11000KV"].value + items["Props 4x 2-inch 3-blade"].value) / 4 / 1000
    m_duct = items["Ducted frame (one piece, PA11)"].value * 0.7 / 4 / 1000   # 70 % of frame mass in ducts
    r_duct = (PROP_MM.value / 2 + DUCT_CLEAR_MM) / 1000
    m_bat = items["Battery 2S 550 mAh HV (GNB, XT30)"].value / 1000
    L, H, Wd = 0.069, 0.012, 0.018                                # battery dims (S14), long axis forward
    m_core = (sum(v.value for _, v in items.items()) - 4 * 1000 * (m_rot + m_duct) - 1000 * m_bat) / 1000
    core = 0.040                                                  # core as 40 mm square plate
    # heights above the duct bottom (m), from the concept model (ESTIMATE)
    z_rot, z_duct, z_bat, z_core = 0.007, 0.0055, 0.0304, 0.011
    m_tot = 4 * m_rot + 4 * m_duct + m_bat + m_core
    zc = (4 * m_rot * z_rot + 4 * m_duct * z_duct + m_bat * z_bat + m_core * z_core) / m_tot
    dz = lambda z: (z - zc) ** 2
    par = 4 * m_rot * dz(z_rot) + 4 * m_duct * dz(z_duct) + m_bat * dz(z_bat) + m_core * dz(z_core)
    Ixx = 4 * m_rot * s**2 + 4 * m_duct * (s**2 + r_duct**2 / 2) + m_bat * (Wd**2 + H**2) / 12 + m_core * core**2 / 12 + par
    Iyy = 4 * m_rot * s**2 + 4 * m_duct * (s**2 + r_duct**2 / 2) + m_bat * (L**2 + H**2) / 12 + m_core * core**2 / 12 + par
    Izz = 4 * m_rot * 2 * s**2 + 4 * m_duct * (2 * s**2 + r_duct**2) + m_bat * (L**2 + Wd**2) / 12 + m_core * core**2 / 6
    return Ixx, Iyy, Izz


def top_speed_estimate(weight_g, t_motor_g, cda=0.010, v_pitch=59.0, rho=1.225):
    """Level-flight speed where tilted thrust balances drag; thrust falls linearly with
    axial inflow T = T0 (1 - v_ax / v_pitch). cda, v_pitch: ASSUMPTIONS. Upper bound."""
    g = 9.81
    m = weight_g / 1000
    t0 = 4 * t_motor_g / 1000 * g
    best = 0.0
    for i in range(1, 890):
        th = math.radians(i / 10)
        lo, hi = 0.0, 80.0
        for _ in range(60):
            v = (lo + hi) / 2
            T = t0 * max(0.0, 1 - v * math.sin(th) / v_pitch)
            fx = T * math.sin(th) - 0.5 * rho * cda * v * v
            lo, hi = (v, hi) if fx > 0 else (lo, v)
        v = lo
        T = t0 * max(0.0, 1 - v * math.sin(th) / v_pitch)
        if T * math.cos(th) >= m * g:
            best = max(best, v)
    return best


# --------------------------------------------------------------------------
def main():
    L = []
    w = L.append
    w("STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2 (G1 rev B approved 2026-10-07)")
    w("")
    w("# Budgets - G1 rev B, updated for the G2 schematics (generated by `review/G1/calc/budgets.py` - do not hand-edit)")
    w("")
    w("G2 changes: Flow deck v2 and four ToF satellite boards added to the weight; ESC MCUs moved to the ESC board's own 3.3 V regulator (D-048); "
      "parts cost now read from `bom/drone-bom-g2.csv`, which is generated from the schematics. The G1-approved numbers are in git history (commit 1ea3e59).")
    w("")
    w("Rev B is the 2S brushless, ducted-frame redesign for agility (flips), speed and crash survival. Rev A (brushed, 1S, PCB-as-frame) is at git tag `g1-rev-a`. "
      "Tags: **SOURCED** = read from the cited page; **ESTIMATE** = engineering estimate (method given); **ASSUMPTION** = design choice or generic constant. Nothing here is measured.")
    w("")

    items = weight_table()
    tot, tlo, thi = weight_totals()
    w("## 1. Weight budget")
    w("")
    w("| Item | Nominal (g) | Range (g) | Tag | Basis |")
    w("|---|---:|---:|---|---|")
    for name, v in items:
        lo, hi = v.rng()
        w(f"| {name} | {v.value:.1f} | {lo:.1f}-{hi:.1f} | {v.kind} | {v.source} |")
    w(f"| **Takeoff weight** | **{tot:.1f}** | **{tlo:.1f}-{thi:.1f}** | CALC | sum |")
    w("")
    w(f"Formula: W = sum(items). Nominal {tot:.1f} g against the < 80 g target. Reference: Mobula8 (85 mm, 2S, same motor, with camera) is 43 g dry, ~72 g with a 29 g pack (S18). "
      "Ours carries five ToF sensors, optical flow, a larger frame and on-board charging.")
    w("")

    w("## 2. Thrust-to-weight and agility")
    w("")
    w("Formula: T/W = 4 x T_motor / W. Hover throttle (thrust fraction) = W / (4 x T_motor).")
    w("")
    w(f"| T per motor (g) | Basis | T/W at {tot:.1f} g | T/W at worst {thi:.1f} g | hover thrust fraction |")
    w("|---:|---|---:|---:|---:|")
    for t, tag in THRUST_SCENARIOS:
        w(f"| {t} | {tag} | {4*t/tot:.2f} | {4*t/thi:.2f} | {tot/(4*t):.0%} |")
    w("")
    Ixx, Iyy, Izz = inertia_estimate()
    s = MOTOR_TO_MOTOR_MM.value / math.sqrt(2) / 1000 / 2
    w(f"Inertia (ESTIMATE, point/slab model incl. the top-mounted battery height): Ixx = {Ixx:.2e}, Iyy = {Iyy:.2e}, Izz = {Izz:.2e} kg m2. Motor offset from each axis = D/(2 sqrt 2) = {s*1000:.1f} mm.")
    w("")
    w("| T per motor (g) | max pitch torque (N m) | angular accel (rad/s2) | time to 1000 deg/s (ms, ignoring motor lag) |")
    w("|---:|---:|---:|---:|")
    for t, _ in THRUST_SCENARIOS:
        tau = 2 * t / 1000 * 9.81 * s
        a = tau / Iyy
        w(f"| {t} | {tau:.3f} | {a:,.0f} | {math.radians(RATE_TARGET_DPS)/a*1000:.0f} |")
    w("")
    w(f"Torque = 2 x T_max x arm (one pair at full thrust, the other at zero). Motor response ({MOTOR_TAU_S.value*1000:.0f} ms, ASSUMPTION) dominates, so reaching "
      f"{RATE_TARGET_DPS} deg/s (freestyle range 850-1200 deg/s, S20) takes roughly 3 x tau ~ {3*MOTOR_TAU_S.value*1000:.0f} ms. A 360 deg flip at that rate takes ~{360/RATE_TARGET_DPS+3*MOTOR_TAU_S.value:.2f} s. "
      "The simulator (`software/microscout_sdk`) flies the full flip with motor lag and reports altitude lost.")
    w("")
    vt = [top_speed_estimate(tot, t) for t, _ in THRUST_SCENARIOS]
    w(f"Level top-speed upper bound (ESTIMATE; CdA 0.010 m2 for the ducted ~126 mm frame and prop pitch speed 59 m/s are ASSUMPTIONS; real props lose more thrust): "
      + ", ".join(f"{t} g/motor -> {v:.0f} m/s" for (t, _), v in zip(THRUST_SCENARIOS, vt))
      + ". Requirement R-21 sets a conservative 10 m/s target to be measured at G7.")
    w("")

    w("## 3. Power budget")
    w("")
    w("### 3a. 3.3 V rail (TPS62162 buck from 2S)")
    w("")
    w("| Load | Peak (mA) | Average (mA) | Tag | Source / method |")
    w("|---|---:|---:|---|---|")
    for n, p, a, k, src in RAIL33:
        w(f"| {n} | {p:.1f} | {a:.1f} | {k} | {src} |")
    pk, av = rail_totals(RAIL33)
    w(f"| **Total 3.3 V** | **{pk:.0f}** | **{av:.0f}** | CALC | sum |")
    w("")
    w(f"TPS62162 is rated 1 A (S12): margin over peak = 1000 / {pk:.0f} = {1000/pk:.2f}x. The ESC MCUs moved to the ESC board's own TPS62162 at G2 (D-048):")
    pke, ave = rail_totals(RAILESC)
    w("")
    w(f"| ESC board 3.3 V | {pke:.0f} | {ave:.0f} | ESTIMATE | {RAILESC[0][4]} |")
    w("")
    w("### 3b. 5 V rail (TPS62133 buck from 2S)")
    w("")
    w("| Load | Peak (mA) | Average (mA) | Tag | Source / method |")
    w("|---|---:|---:|---|---|")
    for n, p, a, k, src in RAIL5:
        w(f"| {n} | {p:.0f} | {a:.0f} | {k} | {src} |")
    pk5, av5 = rail_totals(RAIL5)
    w(f"| **Total 5 V** | **{pk5:.0f}** | **{av5:.0f}** | CALC | sum |")
    w("")
    elec = electronics_battery_current_a()
    w(f"Electronics at the battery: (3.3 x {av:.0f} mA / {EFF33.value} + 3.3 x {ave:.0f} mA / ({EFF33.value} x {EFFBOOST.value} boost) + 5 x {av5:.0f} mA / {EFF5.value}) / {V_NOM.value} V = **{elec*1000:.0f} mA**.")
    w("")
    w("### 3c. Hover current and hover time")
    w("")
    w("Formulas: P_hover = W / eta; I = P_hover / V_nom + I_elec; t = C x HV_derate x usable / I.")
    w("")
    w("| W (g) | eta (g/W) | P_hover (W) | I_total (A) | Hover time (min) |")
    w("|---:|---:|---:|---:|---:|")
    for W in (tot, thi, 80.0):
        for eta in ETA_GW:
            w(f"| {W:.1f} | {eta} | {W/eta:.1f} | {hover_total_current_a(W, eta):.2f} | {flight_time_min(W, eta):.1f} |")
    w("")
    w(f"Capacity {CAP_MAH.value:.0f} mAh (S14) x {HV_DERATE.value} (ESTIMATE) x {USABLE_FRAC.value:.0%} usable (ASSUMPTION). eta bracket: S15 gives 2.19 g/W at 82 g per motor; "
      "at ~20 g per motor (hover) small motors usually run more efficiently, so 2.5-3.5 g/W is assumed. Aggressive flying draws several times hover current; expect 2-3 min of acro per pack (ESTIMATE). "
      "Cross-check: Meteor85 (2S 450 mAh, 1103) claims 7 min (S18).")
    w("")
    w("### 3d. Peak current")
    w("")
    ipk = 4 * I_MAX_TABLE_A + (pk / 1000 * 3.3 / EFF33.value + pke / 1000 * 3.3 / (EFF33.value * EFFBOOST.value) + pk5 / 1000 * 5 / EFF5.value) / 6.0
    w(f"I_peak = 4 x {I_MAX_TABLE_A} A (S15 full throttle) + electronics at a sagged 6.0 V = **{ipk:.1f} A**. "
      f"XT30 is rated 15 A continuous / 30 A peak (S23): full-throttle bursts exceed the peak rating, so firmware limits motor output to keep battery current <= 30 A "
      f"(DR-06), and the connector choice stays an open question (OQ-2). Hover ({hover_total_current_a(tot, 3.0):.1f} A) is well inside the 15 A continuous rating; sustained hard acro "
      "(ESTIMATE 10-15 A average) approaches it.")
    w("")

    w("## 4. Component calculations")
    w("")
    r_sh = 0.001
    w(f"**4a. Shunt (INA226, S8, S27).** Full scale 81.92 mV / 1 mOhm = {0.08192/r_sh:.0f} A; LSB 2.5 uV / 1 mOhm = 2.5 mA. "
      f"P = I^2 R: hover {hover_total_current_a(tot, 3.0):.1f} A -> {hover_total_current_a(tot, 3.0)**2*r_sh*1000:.0f} mW; 30 A limit -> {30**2*r_sh:.2f} W; {ipk:.0f} A burst -> {ipk**2*r_sh:.2f} W "
      "(2 W part; bursts only).")
    w("")
    w("**4b. Reverse polarity (D-035, OQ-10).** Ground-return FETs do not work here: the charger's JST-XH balance lead ties pack negative straight to board ground, "
      "bypassing them. Rev B relies on keyed XT30 and JST-XH connectors; a high-side ideal-diode controller with back-to-back N-FETs is the alternative (part TBD). "
      "No fuse: a firmware limit cannot clear a shorted ESC FET on a 100C pack - residual risk stated in R-13 and the flying guide (unplug after flight).")
    w("")
    r_fet = 0.0047
    i_m = I_MAX_TABLE_A
    w(f"**4c. ESC conduction loss per channel.** Two FETs conduct at a time: P = I^2 x 2R = {i_m}^2 x 2 x 4.7 mOhm = {i_m**2*2*r_fet:.2f} W peak per channel "
      "(switching loss checked at G6). FD6288Q drivers need a 5-20 V supply (S29): at G2 their supply VDRV comes from VBAT through the TPS22810 switch (U24, enabled by the logic "
      "soft switch, D-036) and an MT3608 boost to 9.6 V (U25, D-054), so drivers are unpowered when the drone is off and keep margin above their 5 V UVLO when the pack sags. "
      "With 10 V-class gate drive the 4.7 mOhm (typ) figure applies; 6 mOhm max gives 1.0 W.")
    w("")
    w(f"**4d. Charger (S21).** BQ25887 boosts 5 V USB to the 2S pack and balances cells (needs the pack's JST-XH balance lead). At 0.5C = {CAP_MAH.value/2:.0f} mA into 7.6 V "
      f"the USB draw is 7.6 x {CAP_MAH.value/2/1000:.3f} / (0.934 x 5.0) = {7.6*CAP_MAH.value/2/1000/(0.934*5):.2f} A - inside the 0.5 A any USB port supplies, so the input limit "
      "defaults to 500 mA (set over I2C by firmware; the charger cannot read the USB-C CC pins itself).")
    w("")
    d_in = PROP_MM.value + 2 * DUCT_CLEAR_MM
    d_out = d_in + 2 * DUCT_WALL_MM
    sp = MOTOR_TO_MOTOR_MM.value / math.sqrt(2)
    w(f"**4e. Duct clearance.** Duct inner diameter {d_in:.1f} mm, outer {d_out:.1f} mm. Adjacent motor spacing D/sqrt2 = {sp:.1f} mm, so neighbouring ducts are "
      f"{sp-d_out:.1f} mm apart - room for the linking struts.")
    w("")
    nbytes = 84 * 1024
    w(f"**4f. VL53L5CX firmware upload (S24).** {nbytes} B x 9 bit / 400 kHz = {nbytes*9/400e3:.2f} s per boot (ESTIMATE).")
    w("")

    w("## 5. Crash and drop energy")
    w("")
    m = tot / 1000
    w("| Case | Speed (m/s) | Energy (J) | Basis |")
    w("|---|---:|---:|---|")
    w(f"| 1.0 m drop onto a hard floor | {math.sqrt(2*9.81*1.0):.1f} | {m*9.81*1.0:.2f} | IEC 60068-2-31 run as 1000 mm falls (S25) |")
    w(f"| 1.22 m transit drop | {math.sqrt(2*9.81*1.22):.1f} | {m*9.81*1.22:.2f} | MIL-STD-810 (S25) |")
    for v in (3.0, 5.0, 10.0):
        w(f"| Wall hit at {v:.0f} m/s | {v:.1f} | {0.5*m*v*v:.2f} | KE = 1/2 m v^2 |")
    w("")
    w("Design response (D-030, D-031): the ducts and bumpers take the load in PA11 / TPU (elongation 35-50 % and > 500 %, S26), the boards are soft-mounted and never "
      "part of the load path, and the cheap parts (props, canopy, ducts) fail first. Requirement R-22 targets survival of 26 drops from 1.0 m and frontal hits at 3 m/s; "
      "faster crashes may break replaceable parts. An academic 405 g quad survived 4.5 m/s frontal hits undamaged (S28) - different scale, for orientation only.")
    w("")

    w("## 6. Parts cost (per drone, from bom/drone-bom-g2.csv)")
    w("")
    rows = [l for l in (REPO / "bom" / "drone-bom-g2.csv").read_text().splitlines() if not l.startswith("#")]
    known, missing = 0.0, []
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
    w(f"Prices: LCSC/vendor pages seen 2026-10-04 to 2026-10-07 at the break covering five drones (BOM `price_break` column); no shipping or tariffs. "
      f"Not priced (UNCONFIRMED): {'; '.join(missing)}; plus passives, PCBs, assembly and the printed frame.")
    w("")
    w(f"**Finding:** priced lines are ${known:.0f} per drone at G2 (G1: $137), before PCBs and assembly. The owner accepted a higher cost than the ~$75 target (D-044, OQ-5). "
      "Largest G2 additions: the Bitcraze Flow deck ($55, D-047), the BMP388 and the Fortior FD6288Q drivers, and the ESC passives now that every part is listed.")
    w("")
    w("## Sources")
    w("")
    for k, s_ in SRC.items():
        w(f"- **{k}**: {s_}")
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}  weight {tot:.1f} g ({tlo:.1f}-{thi:.1f})  cost ${known:.2f}")


if __name__ == "__main__":
    main()
