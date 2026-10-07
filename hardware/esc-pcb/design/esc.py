# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""MicroScout 4-in-1 ESC board (rev B, AM32) - schematic source.

Per motor: Artery AT32F421G8U7 running AM32 (target OPENESC_20_F421 pin map, D-050),
Fortior FD6288Q gate driver, 6x HL 60N03D N-MOSFETs, back-EMF dividers.
Run: python3 hardware/esc-pcb/design/esc.py
Licence of this hardware description: CERN-OHL-S-2.0.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "sch"))
from schgen import Project  # noqa: E402

LIB = {"microscout": str(REPO / "hardware" / "libraries" / "microscout.kicad_sym")}
OUT = REPO / "hardware" / "esc-pcb"
IND_2520 = "Inductor_SMD:L_Changjiang_FNR252012S"

# AM32 OPENESC_20_F421 (Inc/targets.h, HARDWARE_GROUP_AT_B + AT_045), AM32 commit 50234143
AM32_PINS = {
    "PA10": "AH", "PB1": "AL", "PA9": "BH", "PB0": "BL", "PA8": "CH", "PA7": "CL",
    "PA0": "BEMF_A", "PA4": "BEMF_B", "PA5": "BEMF_C", "PA1": "BEMF_COM",
}
UNUSED = ["PF0", "PF1", "PA2", "PA3", "PA6", "PA15", "PB3", "PB5", "PB6", "PB7"]


def channel(p, ch):
    s = p.sheet(f"motor{ch}", f"Motor {ch}")
    n = lambda x: f"M{ch}_{x}"          # noqa: E731
    base = ch * 100
    s.block(f"Motor {ch} MCU - AT32F421G8U7 with AM32 (pin map: AM32 target OPENESC_20_F421)",
            ["PWM: TMR1 CH1-3 + complementary outputs, active high (FD6288 outputs follow inputs; no USE_INVERTED flags).",
             "BEMF comparator inputs PA0/PA4/PA5, neutral PA1. DShot in on PB4 (TMR3 CH1). SWD pads for the first",
             "bootloader flash; later updates over the signal wire. VDD/VDDA decoupling 100 nF each + 1 uF (datasheet Fig. 8;",
             "pin assignment of the values UNCONFIRMED). BOOT0 10 k to GND; NRST 100 nF (value UNCONFIRMED)."])
    conn = {"VDD": "+3V3_ESC", "VDDA": "+3V3_ESC", "NRST": n("NRST"), "BOOT0": n("BOOT0"),
            "PA13/SWDIO": n("SWDIO"), "PA14/SWCLK": n("SWCLK"), "PB4": f"MOT{ch}_DSHOT", "VSS": "GND", "EP_VSS": "GND"}
    for pin, sig in AM32_PINS.items():
        conn[pin] = n(sig)
    for pin in UNUSED:
        conn[pin] = None
    s.add("microscout:AT32F421G8U7", f"U{base + 1}", "AT32F421G8U7", "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.6x2.6mm",
          conn, LCSC="C2765098", MPN="AT32F421G8U7", Manufacturer="Artery")
    s.C(f"C{base + 1}", "100n", "+3V3_ESC", "GND")
    s.C(f"C{base + 2}", "100n", "+3V3_ESC", "GND")
    s.C(f"C{base + 3}", "1u", "+3V3_ESC", "GND")
    s.C(f"C{base + 4}", "100n", n("NRST"), "GND")
    s.R(f"R{base + 1}", "10k", n("BOOT0"), "GND")
    for i, sig in enumerate(["SWDIO", "SWCLK", "NRST"]):
        s.TP(f"TP{base + 1 + i}", n(sig))

    s.block(f"Motor {ch} gate driver - FD6288Q (Fortior datasheet V1.6 section 1.5)",
            ["VCC = VDRV, 9.6 V from the FC boost (D-054); FD6288 VCC 5-20 V, UVLO 4.6 V typ / 5.0 V max rising.",
             "Bootstrap: external Schottky (FD6288 has none) + 1 uF per phase. Cboot >= Qg / dV = 34 nC / 0.1 V = 0.34 uF;",
             "1 uF gives ~34 mV droop per cycle. 10 Ohm gate resistors: agent choice for edge control, tune at G6.",
             "JSMSEMI second source lists 8-20 V VCC (below a 2S pack) - not fitted until its datasheet is read (OQ-13)."])
    drv = {"VCC": "VDRV", "COM": "GND", "EP": "GND", "NC": None,
           "HIN1": n("AH"), "HIN2": n("BH"), "HIN3": n("CH"), "LIN1": n("AL"), "LIN2": n("BL"), "LIN3": n("CL")}
    for k, ph in enumerate("ABC", start=1):
        drv[f"VB{k}"] = n(f"VB_{ph}")
        drv[f"HO{k}"] = n(f"HO_{ph}")
        drv[f"VS{k}"] = n(f"PH_{ph}")
        drv[f"LO{k}"] = n(f"LO_{ph}")
    s.add("microscout:FD6288Q", f"U{base + 2}", "FD6288Q", "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
          drv, LCSC="C328453", MPN="FD6288Q", Manufacturer="Fortior Tech", Alternate="JSMSEMI FD6288Q C7466367 (VCC min UNCONFIRMED)")
    s.C(f"C{base + 5}", "1u", "VDRV", "GND")
    s.C(f"C{base + 6}", "100n", "VDRV", "GND")
    for k, ph in enumerate("ABC"):
        s.D(f"D{base + 1 + k}", "1N5819WS", "VDRV", n(f"VB_{ph}"), LCSC="C191023", MPN="1N5819WS")
        s.C(f"C{base + 7 + k}", "1u", n(f"VB_{ph}"), n(f"PH_{ph}"))

    s.block(f"Motor {ch} power stage - 6x HL 60N03D (30 V; 4.7 mOhm typ / 6 mOhm max at 10 V gate drive; Qg 34 nC)",
            ["Conduction loss at 9.2 A (vendor max current): two FETs conduct, P = 9.2^2 x 2 x 4.7 mOhm = 0.80 W typ (budgets 4c),",
             "1.0 W at 6 mOhm max. 47 k gate-source resistors hold every FET off while the drivers are unpowered (FD6288",
             "datasheet application circuit R2; D-036 keeps VBAT on the bridge when off). 2x 10 uF 25 V across the bridge;",
             "the 100 uF polymer bulk capacitor is on the power sheet."])
    for k, ph in enumerate("ABC"):
        s.R(f"R{base + 10 + 2 * k}", "10", n(f"HO_{ph}"), n(f"GH_{ph}"))
        s.R(f"R{base + 11 + 2 * k}", "10", n(f"LO_{ph}"), n(f"GL_{ph}"))
        s.add("microscout:NMOS_PDFN3333", f"Q{base + 1 + 2 * k}", "HL60N03D", "Package_SO:Vishay_PowerPAK_1212-8_Single",
              {"G": n(f"GH_{ph}"), "D": "VBAT", "S": n(f"PH_{ph}")}, LCSC="C7471100", MPN="HL 60N03D", Manufacturer="HL")
        s.add("microscout:NMOS_PDFN3333", f"Q{base + 2 + 2 * k}", "HL60N03D", "Package_SO:Vishay_PowerPAK_1212-8_Single",
              {"G": n(f"GL_{ph}"), "D": n(f"PH_{ph}"), "S": "GND"}, LCSC="C7471100", MPN="HL 60N03D", Manufacturer="HL")
        s.R(f"R{base + 30 + 2 * k}", "47k", n(f"GH_{ph}"), n(f"PH_{ph}"))
        s.R(f"R{base + 31 + 2 * k}", "47k", n(f"GL_{ph}"), "GND")
    s.C(f"C{base + 10}", "10u", "VBAT", "GND", pkg="0805")
    s.C(f"C{base + 11}", "10u", "VBAT", "GND", pkg="0805")
    for k, ph in enumerate("ABC"):
        s.add("Connector_Generic:Conn_01x01", f"J{base + 1 + k}", "motor pad", "Connector_Wire:SolderWirePad_1x01_SMD_1x2mm",
              {"1": n(f"PH_{ph}")}, Note="Motor wire pad")

    s.block(f"Motor {ch} back-EMF sensing (topology traced from OpenESC-20x20, CERN-OHL-S-2.0; values scaled for 2S)",
            ["Each phase: 10 k to the sense node, 2.2 k to GND -> 8.8 V x 2.2 / 12.2 = 1.59 V max (OpenESC uses 1 k for 6S).",
             "Each sense node: 10 k to the common (virtual neutral) node on PA1."])
    for k, ph in enumerate("ABC"):
        s.R(f"R{base + 20 + 3 * k}", "10k", n(f"PH_{ph}"), n(f"BEMF_{ph}"))
        s.R(f"R{base + 21 + 3 * k}", "2.2k", n(f"BEMF_{ph}"), "GND")
        s.R(f"R{base + 22 + 3 * k}", "10k", n(f"BEMF_{ph}"), n("BEMF_COM"))


def build():
    p = Project("microscout-esc", OUT, "MicroScout 4-in-1 ESC", "G2-draft-1", LIB)
    s = p.sheet("power", "Power and link")
    s.block("Link to the flight controller (JST-SH 8, mirrors FC J7) and battery wire pads",
            ["VDRV (9.6 V, D-054) is switched by the FC's soft switch (D-036): when the drone is off, the drivers and MCUs here",
             "are unpowered and the 47 k gate-source resistors hold the FETs off.",
             "Battery current arrives on J2/J3 wire pads from FC J8/J9 (after the FC's current shunt)."])
    s.add("Connector_Generic_MountingPin:Conn_01x08_MountingPin", "J1", "FC link (JST-SH 8)",
          "Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal",
          {"1": "VDRV", "2": "GND", "3": "MOT1_DSHOT", "4": "MOT2_DSHOT", "5": "MOT3_DSHOT", "6": "MOT4_DSHOT",
           "7": "GND", "8": None, "MP": "GND"}, LCSC="C160407", MPN="SM08B-SRSS-TB(LF)(SN)")
    s.add("Connector_Generic:Conn_01x01", "J2", "VBAT pad", "Connector_Wire:SolderWirePad_1x01_SMD_5x10mm", {"1": "VBAT"})
    s.add("Connector_Generic:Conn_01x01", "J3", "GND pad", "Connector_Wire:SolderWirePad_1x01_SMD_5x10mm", {"1": "GND"})
    s.CP("C1", "100u 25V", "VBAT", "GND", "Capacitor_SMD:CP_Elec_6.3x5.9", LCSC="C2939798",
         MPN="SVS1EM101E06E00RAXXX", Rating="25 V polymer, ESR 45 mOhm, ripple 2.2 A")
    s.add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", {"1": "GND"})
    s.add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", "", {"1": "VBAT"})
    s.add("power:PWR_FLAG", "#FLG03", "PWR_FLAG", "", {"1": "VDRV"})

    s.block("ESC logic 3.3 V - TPS62162 from VDRV (D-048; same circuit as the FC 3.3 V rail)",
            ["Load: 4x AT32F421 (~25 mA each at 120 MHz, ESTIMATE). VIN 9.6 V (rated 3-17 V). EN tied to VIN: on whenever",
             "VDRV is on."])
    s.add("Regulator_Switching:TPS62162DSG", "U1", "TPS62162", "Package_SON:WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
          {"PGND": "GND", "VIN": "VDRV", "EN": "VDRV", "AGND": "GND", "FB": "GND", "VOS": "+3V3_ESC",
           "SW": "SW_3V3E", "PG": None, "PAD": "GND"}, LCSC="C40256", MPN="TPS62162DSGR", Manufacturer="Texas Instruments")
    s.C("C2", "10u", "VDRV", "GND", pkg="0805")
    s.L("L1", "2.2u", "SW_3V3E", "+3V3_ESC", IND_2520, LCSC="C5832372", MPN="FTC252012S2R2MBCA", Rating="Isat 3.8 A")
    s.C("C3", "22u", "+3V3_ESC", "GND", pkg="0805")
    s.add("power:PWR_FLAG", "#FLG04", "PWR_FLAG", "", {"1": "+3V3_ESC"})
    s.TP("TP1", "+3V3_ESC")
    s.TP("TP2", "GND")
    for ch in range(1, 5):
        channel(p, ch)
    return p


if __name__ == "__main__":
    proj = build()
    proj.write()
    print(f"wrote {OUT.relative_to(REPO)} ({len(proj.parts)} parts incl. flags, {len(proj.sheets)} sheets)")
