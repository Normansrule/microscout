# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""MicroScout flight-controller board (rev B) - schematic source.

Run:  python3 hardware/drone-pcb/design/fc.py   (writes hardware/drone-pcb/*.kicad_sch)
Every value here is a first-pass G2 choice; the reasoning and datasheet references are in
review/G2/reference-designs.md. Licence of this hardware description: CERN-OHL-S-2.0.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "sch"))
from schgen import Project  # noqa: E402

LIB = {"microscout": str(REPO / "hardware" / "libraries" / "microscout.kicad_sym")}
OUT = REPO / "hardware" / "drone-pcb"

QFN_RGE = "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm"
IND_2520 = "Inductor_SMD:L_Changjiang_FNR252012S"


def build():
    p = Project("microscout-fc", OUT, "MicroScout flight controller", "G2-draft-1", LIB)

    # ======================================================================== POWER
    s = p.sheet("power", "Power")
    s.block("Battery input and current sense (D-035: no fuse, no reverse FET; keyed XT30)",
            ["XT30 pin 1 = pack +, pin 2 = pack - (footprint polarity to confirm at G3).",
             "RS1 high-side 1 mOhm: INA226 full scale 81.92 mV / 1 mOhm = 81.9 A; LSB 2.5 mA (budgets 4a).",
             "Input filter per INA226 datasheet 6.4.2: <=10 Ohm per input + 0.1 uF differential."])
    s.add("Connector_Generic:Conn_01x02", "J2", "XT30PW-M", "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal",
          {"1": "VBAT_RAW", "2": "GND"}, LCSC="C431092", MPN="XT30PW-M30.G.Y", Manufacturer="Changzhou Amass")
    s.R("RS1", "1m", "VBAT_RAW", "VBAT", pkg="2512")
    s.R("R1", "10", "VBAT_RAW", "INA_INP")
    s.R("R2", "10", "VBAT", "INA_INN")
    s.C("C1", "100n", "INA_INP", "INA_INN")
    s.add("Sensor_Energy:INA226", "U9", "INA226", "Package_SO:VSSOP-10_3x3mm_P0.5mm",
          {"A1": "GND", "A0": "GND", "Alert": "EXP_INT_N", "SDA": "I2C_SDA", "SCL": "I2C_SCL",
           "VS": "+3V3", "GND": "GND", "Vbus": "VBAT", "Vin-": "INA_INN", "Vin+": "INA_INP"},
          LCSC="C49851", MPN="INA226AIDGSR", Manufacturer="Texas Instruments")
    s.C("C2", "100n", "+3V3", "GND")
    s.add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", {"1": "GND"})

    s.block("Logic supply OR-ing (D-046): logic runs from the battery or from USB alone",
            ["VLOGIC = max(VBAT, VBUS) - Vf. With USB only (no battery) the board can be powered on and flashed.",
             "VLOGIC peak load ~4.9 W -> ~0.9 A at 5.5 V, ~1.1 A from USB alone: SS34 (3 A, SMA) instead of SOD-323 parts.",
             "On USB alone firmware must cap the load (Wi-Fi TX power, camera, LEDs) to stay near 500 mA (DR-09).",
             "R20 bleeds VBUS so D2 reverse leakage cannot fake 'USB present' when only the battery is plugged in."])
    s.D("D2", "SS34", "VBUS", "VLOGIC", fp="Diode_SMD:D_SMA", LCSC="C8678", MPN="SS34", Rating="40 V 3 A, Vf 0.55 V at 3 A")
    s.D("D3", "SS34", "VBAT", "VLOGIC", fp="Diode_SMD:D_SMA", LCSC="C8678", MPN="SS34", Rating="40 V 3 A, Vf 0.55 V at 3 A")
    s.R("R20", "100k", "VBUS", "GND")
    s.C("C3", "10u", "VLOGIC", "GND", pkg="0805")
    s.add("power:PWR_FLAG", "#FLG03", "PWR_FLAG", "", {"1": "VLOGIC"})

    s.block("2S charger from USB 5 V with cell balancing - BQ25887 (datasheet SLUSD89, EVM SLUUC12)",
            ["PSEL high (REGN) = 500 mA input; ILIM 2.2 k -> 1110/2200 = 0.50 A hardware cap.",
             "TS: no pack thermistor - fixed 10 k to GND with the 5.23 k / 30.1 k divider (EVM JP7 method) = 58.9 % REGN.",
             "MID via 300 Ohm (reverse-plug protection, pin 9 note). CBSET 150 Ohm: balance ~4.35/150 = 29 mA, 0.13 W.",
             "STAT drives the red charge LED from REGN, so it works while the drone is off."])
    s.add("microscout:BQ25887_RGE", "U2", "BQ25887", QFN_RGE,
          {"~{PG}": "VBUS_DET", "STAT": "CHG_STAT", "CD": "GND", "SDA": "I2C_SDA", "SCL": "I2C_SCL",
           "~{INT}": "CHG_INT_N", "TS": "CHG_TS", "ILIM": "CHG_ILIM", "MID": "CHG_MID", "CBSET": "CHG_CBSET",
           "REGN": "CHG_REGN", "BTST": "CHG_BTST", "BAT": "VBAT", "SNS": "CHG_SNS", "SW": "CHG_SW",
           "GND": "GND", "EP": "GND", "PMID": "CHG_PMID", "VBUS": "VBUS", "PSEL": "CHG_PSEL"},
          LCSC="C2761614", MPN="BQ25887RGER", Manufacturer="Texas Instruments")
    s.C("C4", "1u", "VBUS", "GND")
    s.C("C5", "10u", "CHG_PMID", "GND", pkg="0805")
    s.L("L1", "1u", "CHG_PMID", "CHG_SW", IND_2520, LCSC="C5832370", MPN="FTC252012S1R0MBCA", Rating="Isat 5.6 A, DCR 35 mOhm")
    s.C("C6", "47n", "CHG_BTST", "CHG_SW")
    s.C("C7", "4.7u", "CHG_REGN", "GND", pkg="0603")
    s.C("C8", "22u", "CHG_SNS", "GND", pkg="0805")
    s.C("C9", "22u", "CHG_SNS", "GND", pkg="0805")
    s.C("C10", "10u", "VBAT", "GND", pkg="0805")
    s.R("R3", "10k", "CHG_REGN", "CHG_PSEL")
    s.R("R4", "2.2k", "CHG_ILIM", "GND")
    s.R("R5", "5.23k", "CHG_REGN", "CHG_TS")
    s.R("R6", "30.1k", "CHG_TS", "GND")
    s.R("R7", "10k", "CHG_TS", "GND")
    s.R("R8", "300", "CHG_MID", "BAL_MID")
    s.R("R9", "150", "CHG_CBSET", "BAL_MID", pkg="1206")
    s.R("R10", "1k", "CHG_REGN", "CHG_LED_A")
    s.add("Device:LED", "D4", "red", "LED_SMD:LED_0603_1608Metric", {"A": "CHG_LED_A", "K": "CHG_STAT"},
          LCSC="C2286", MPN="KT-0603R")
    s.R("R11", "10k", "+3V3", "VBUS_DET")
    s.R("R12", "10k", "+3V3", "CHG_INT_N")
    s.add("Connector_Generic:Conn_01x03", "J6", "JST-XH 3 (balance)", "Connector_JST:JST_XH_S3B-XH-A_1x03_P2.50mm_Horizontal",
          {"1": "GND", "2": "BAL_MID", "3": None}, LCSC="C157928", MPN="S3B-XH-A(LF)(SN)",
          Note="Pin 1 pack -, pin 2 mid, pin 3 pack + left open (UNCONFIRMED pack wiring)")
    s.add("power:PWR_FLAG", "#FLG04", "PWR_FLAG", "", {"1": "VBUS"})

    s.block("Soft power switch - LTC2954-1 (datasheet 2954fb, Fig. 5 values for ONT/PDT)",
            ["EN (open drain) enables the 3.3 V and 5 V bucks and the ESC gate-driver supply switch U24 (D-036).",
             "KILL: 100 k pull-up to 3V3; pulled low by the MCU through D5 (GPIO48 cannot hold KILL high, D-055) or by",
             "the undervoltage detector U23 through Q5 (disabled while USB is present, D-055). Vf(D5) at 33 uA ~0.2 V < 0.57 V.",
             "t_ON = 0.033 uF / 1.56e-4 uF/ms + 1 ms = 213 ms press to turn on; C_PDT 1 uF -> 6.4 s power-down window."])
    s.add("microscout:LTC2954-1", "U8", "LTC2954-1", "Package_TO_SOT_SMD:TSOT-23-8",
          {"VIN": "VLOGIC", "~{PB}": "PWR_BTN", "~{KILL}": "PWR_KILL_N", "ONT": "PWR_ONT", "PDT": "PWR_PDT",
           "EN": "PWR_EN", "~{INT}": "PWR_BTN_INT_N", "GND": "GND"},
          LCSC="C683782", MPN="LTC2954CTS8-1#TRPBF", Manufacturer="Analog Devices")
    s.C("C11", "100n", "VLOGIC", "GND")
    s.C("C12", "33n", "PWR_ONT", "GND")
    s.C("C13", "1u", "PWR_PDT", "GND")
    s.R("R13", "100k", "VLOGIC", "PWR_EN")
    s.R("R14", "100k", "+3V3", "PWR_KILL_N")
    s.R("R15", "10k", "+3V3", "PWR_BTN_INT_N")
    s.D("D5", "1N5819WS", "PWR_KILL_N", "MCU_KILL_N", LCSC="C191023", MPN="1N5819WS")
    s.add("Switch:SW_Push", "SW3", "POWER", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
          {"1": "PWR_BTN", "2": "GND"}, LCSC="C318884", MPN="TS-1187A-B-A-B")

    s.block("Hardware battery undervoltage cut-off - TLV6700 (R-13, D-053, D-055) - last resort behind the firmware",
            ["Trip: V = 0.3945 V x (1.5 M + 110 k) / 110 k = 5.77 V (2.89 V/cell); release 0.400 x 14.64 = 5.85 V.",
             "C24 filters load sag: tau = (1.5 M || 110 k) x 4.7 uF = 0.48 s, so throttle punches do not cut power.",
             "Q5 disconnects the cut-off while USB is present (VBUS_DET low): TLV6700 holds OUTA low below its UVLO and",
             "VBAT is not 0 V without a battery (charger battery detection, D3 leakage), which would block USB-only power-on.",
             "Firmware lands first at 3.4 V/cell under load."])
    s.add("microscout:TLV6700DDC", "U23", "TLV6700", "Package_TO_SOT_SMD:TSOT-23-6",
          {"VDD": "VBAT", "INA+": "UV_SENSE", "INB-": "GND", "OUTA": "UV_KILL_N", "OUTB": None, "GND": "GND"},
          LCSC="C2868382", MPN="TLV6700DDCR", Manufacturer="Texas Instruments")
    s.R("R16", "1.5M", "VBAT", "UV_SENSE")
    s.R("R17", "110k", "UV_SENSE", "GND")
    s.C("C24", "4.7u", "UV_SENSE", "GND")
    s.C("C14", "100n", "VBAT", "GND")
    s.add("Transistor_FET:AO3400A", "Q5", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
          {"G": "VBUS_DET", "D": "PWR_KILL_N", "S": "UV_KILL_N"}, LCSC="C20917", MPN="AO3400A")

    s.block("3.3 V buck - TPS62162 fixed 3.3 V, 1 A (datasheet Fig. 35: 2.2 uH, 10 uF in, 22 uF out)",
            ["FB to AGND on fixed versions; VOS to the output capacitor. PG pulled up to 3V3, brought to a test point."])
    s.add("Regulator_Switching:TPS62162DSG", "U3", "TPS62162", "Package_SON:WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
          {"PGND": "GND", "VIN": "VLOGIC", "EN": "PWR_EN", "AGND": "GND", "FB": "GND", "VOS": "+3V3",
           "SW": "SW_3V3", "PG": "PG_3V3", "PAD": "GND"},
          LCSC="C40256", MPN="TPS62162DSGR", Manufacturer="Texas Instruments")
    s.C("C15", "10u", "VLOGIC", "GND", pkg="0805")
    s.L("L2", "2.2u", "SW_3V3", "+3V3", IND_2520, LCSC="C5832372", MPN="FTC252012S2R2MBCA", Rating="Isat 3.8 A, DCR 55 mOhm")
    s.C("C16", "22u", "+3V3", "GND", pkg="0805")
    s.R("R18", "100k", "+3V3", "PG_3V3")
    s.TP("TP1", "PG_3V3")
    s.add("power:PWR_FLAG", "#FLG05", "PWR_FLAG", "", {"1": "+3V3"})

    s.block("5 V buck - TPS62133 fixed 5 V, 3 A (datasheet Table 9-1: 2.2 uH, 10 uF + 0.1 uF in, 22 uF out, 3.3 nF SS)",
            ["Loads: ELRS receiver, 4x WS2812B, LED buffer, buzzer. FSW low = 2.5 MHz; DEF low = nominal 5.0 V."])
    s.add("Regulator_Switching:TPS62130", "U4", "TPS62133", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm",
          {"SW": "SW_5V", "PG": "PG_5V", "FB": "GND", "GND": "GND", "FSW": "GND", "DEF": "GND",
           "SS/TR": "SS_5V", "VIN": "VLOGIC", "EN": "PWR_EN", "VOS": "+5V"},
          LCSC="C73973", MPN="TPS62133RGTR", Manufacturer="Texas Instruments",
          Note="Symbol is the TPS62130 family symbol; TPS62133 = fixed 5.0 V (FB to AGND)")
    s.C("C17", "10u", "VLOGIC", "GND", pkg="0805")
    s.C("C18", "100n", "VLOGIC", "GND")
    s.L("L3", "2.2u", "SW_5V", "+5V", IND_2520, LCSC="C5832372", MPN="FTC252012S2R2MBCA", Rating="Isat 3.8 A, DCR 55 mOhm")
    s.C("C19", "22u", "+5V", "GND", pkg="0805")
    s.C("C20", "3.3n", "SS_5V", "GND")
    s.R("R19", "100k", "+5V", "PG_5V")
    s.TP("TP2", "PG_5V")
    s.add("power:PWR_FLAG", "#FLG06", "PWR_FLAG", "", {"1": "+5V"})

    s.block("ESC gate-driver supply: TPS22810 switch (D-036) + MT3608 boost to 9.6 V (D-054), and the ESC board link",
            ["VDRV = 9.6 V for the 4x FD6288Q drivers and the ESC board's own 3.3 V regulator (D-048). A boost keeps the",
             "drivers well above their 5.0 V UVLO when a 2S pack sags under load, and gives 10 V-class gate drive.",
             "VOUT = 0.6 V x (1 + 150 k / 10 k) = 9.6 V. D = 1 - Vin/Vout = 0.08-0.38. Load ~50 mA (ESC 3.3 V + drivers).",
             "Ripple dI = 6 V x 0.38 / (10 uH x 1.2 MHz) = 0.19 A p-p, far below the 4 A switch limit.",
             "QOD on VOUT discharges VDRV_SW when off; the boost then passes 0 V. CT 3.3 nF: ~0.7 ms rise."])
    s.add("microscout:TPS22810DBV", "U24", "TPS22810", "Package_TO_SOT_SMD:SOT-23-6",
          {"VIN": "VBAT", "EN/UVLO": "PWR_EN", "CT": "DRV_CT", "VOUT": "VDRV_SW", "QOD": "VDRV_SW", "GND": "GND"},
          LCSC="C205990", MPN="TPS22810DBVR", Manufacturer="Texas Instruments")
    s.C("C21", "1u", "VBAT", "GND")
    s.C("C23", "3.3n", "DRV_CT", "GND")
    s.add("microscout:MT3608", "U25", "MT3608", "Package_TO_SOT_SMD:SOT-23-6",
          {"IN": "VDRV_SW", "EN": "VDRV_SW", "SW": "BOOST_SW", "FB": "BOOST_FB", "NC": None, "GND": "GND"},
          LCSC="C84817", MPN="MT3608", Manufacturer="Aerosemi")
    s.C("C25", "22u", "VDRV_SW", "GND", pkg="0805")
    s.L("L4", "10u", "VDRV_SW", "BOOST_SW", IND_2520, LCSC="C48888313", MPN="FTC252012S100MGCA",
        Rating="10 uH; Isat 1.6 A assumed from the MBCA variant (UNCONFIRMED)")
    s.D("D6", "1N5819WS", "BOOST_SW", "VDRV", LCSC="C191023", MPN="1N5819WS")
    s.R("R25", "150k", "VDRV", "BOOST_FB")
    s.R("R26", "10k", "BOOST_FB", "GND")
    s.C("C26", "22u", "VDRV", "GND", pkg="0805")
    s.C("C22", "100n", "VDRV", "GND")
    s.add("power:PWR_FLAG", "#FLG07", "PWR_FLAG", "", {"1": "VDRV"})
    s.add("Connector_Generic_MountingPin:Conn_01x08_MountingPin", "J7", "ESC link (JST-SH 8)",
          "Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal",
          {"1": "VDRV", "2": "GND", "3": "MOT1_LINK", "4": "MOT2_LINK", "5": "MOT3_LINK", "6": "MOT4_LINK",
           "7": "GND", "8": None, "MP": "GND"}, LCSC="C160407", MPN="SM08B-SRSS-TB(LF)(SN)")
    s.add("Connector_Generic:Conn_01x01", "J8", "ESC VBAT pad", "Connector_Wire:SolderWirePad_1x01_SMD_5x10mm",
          {"1": "VBAT"}, Note="20 AWG wire to ESC board; pad size set at G3")
    s.add("Connector_Generic:Conn_01x01", "J9", "ESC GND pad", "Connector_Wire:SolderWirePad_1x01_SMD_5x10mm",
          {"1": "GND"}, Note="20 AWG wire to ESC board; pad size set at G3")
    for i, net in enumerate(["VBAT", "VLOGIC", "+3V3", "+5V", "VDRV", "GND"]):
        s.TP(f"TP{10 + i}", net)

    # ======================================================================== MCU
    m = p.sheet("mcu", "MCU and USB")
    m.block("ESP32-S3-WROOM-1-N8R2 (pin table: review/G1/pin-allocation.csv; module datasheet Table 3-1, section 9)",
            ["3V3: 22 uF + 2x 0.1 uF (datasheet peripheral schematic). EN: 10 k + 1 uF RC (datasheet section 9).",
             "Strapping: GPIO0 10 k up (BOOT button to GND), GPIO3 10 k up, GPIO45 10 k down, GPIO46 100 k down (at Q3).",
             "GPIO1 is spare (test point). DShot outputs have 100 k pull-downs (motor stopped during reset) and 1 k series",
             "resistors that limit current into an unpowered ESC MCU (e.g. USB-only power). GPIO48 reaches KILL through D5."])
    m.add("RF_Module:ESP32-S3-WROOM-1", "U1", "ESP32-S3-WROOM-1-N8R2", "RF_Module:ESP32-S3-WROOM-1",
          {"GND": "GND", "3V3": "+3V3", "EN": "ESP_EN", "IO0": "BOOT_N", "IO1": "SPARE_IO1", "IO2": "MOT1_DSHOT",
           "IO3": "EXP_INT_N", "IO4": "CAM_D0", "IO5": "CAM_D1", "IO6": "CAM_D2", "IO7": "CAM_D3", "IO8": "CAM_D4",
           "IO9": "CAM_D5", "IO10": "CAM_D6", "IO11": "SPI_MOSI", "IO12": "SPI_SCK", "IO13": "SPI_MISO",
           "IO14": "CAM_D7", "IO15": "CAM_XCLK", "IO16": "CAM_PCLK", "IO17": "CAM_VSYNC", "IO18": "CAM_HREF",
           "IO19": "USB_DN", "IO20": "USB_DP", "IO21": "MOT2_DSHOT", "IO35": "IMU_CS_N", "IO36": "FLOW_CS_N",
           "IO37": "IMU_INT1", "IO38": "MOT3_DSHOT", "IO39": "I2C_SDA", "IO40": "I2C_SCL", "IO41": "CRSF_RX",
           "IO42": "CRSF_TX", "TXD0": "U0TXD", "RXD0": "U0RXD", "IO45": "LED_DIN_3V3", "IO46": "BUZZER",
           "IO47": "MOT4_DSHOT", "IO48": "MCU_KILL_N"},
          LCSC="C2913204", MPN="ESP32-S3-WROOM-1-N8R2", Manufacturer="Espressif")
    m.C("C30", "22u", "+3V3", "GND", pkg="0805")
    m.C("C31", "100n", "+3V3", "GND")
    m.C("C32", "100n", "+3V3", "GND")
    m.R("R30", "10k", "+3V3", "ESP_EN")
    m.C("C33", "1u", "ESP_EN", "GND")
    m.add("Switch:SW_Push", "SW2", "RESET", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
          {"1": "ESP_EN", "2": "GND"}, LCSC="C318884", MPN="TS-1187A-B-A-B")
    m.R("R31", "10k", "+3V3", "BOOT_N")
    m.add("Switch:SW_Push", "SW1", "BOOT", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
          {"1": "BOOT_N", "2": "GND"}, LCSC="C318884", MPN="TS-1187A-B-A-B")
    m.R("R32", "10k", "+3V3", "EXP_INT_N")
    m.R("R33", "10k", "LED_DIN_3V3", "GND")
    for i, n in enumerate(["MOT1_DSHOT", "MOT2_DSHOT", "MOT3_DSHOT", "MOT4_DSHOT"]):
        m.R(f"R{34 + i}", "100k", n, "GND")
        m.R(f"R{42 + i}", "1k", n, f"MOT{i + 1}_LINK")
    m.TP("TP3", "SPARE_IO1")

    m.block("USB-C (device, USB 2.0) with ESD protection",
            ["CC1/CC2 5.1 k to GND (sink, Rd). USBLC6-2SC6 at the connector; 22 Ohm series resistors near the module",
             "(ESP32-S3 checklist 'initial value 22/33 Ohm'). VBUS feeds the charger and the logic OR-ing only."])
    m.add("Connector:USB_C_Receptacle_USB2.0_16P", "J1", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
          {"GND": "GND", "VBUS": "VBUS", "CC1": "USB_CC1", "CC2": "USB_CC2", "D+": "USB_C_DP", "D-": "USB_C_DN",
           "SBU1": None, "SBU2": None, "SHIELD": "GND"}, LCSC="C165948", MPN="TYPE-C-31-M-12")
    m.R("R38", "5.1k", "USB_CC1", "GND")
    m.R("R39", "5.1k", "USB_CC2", "GND")
    m.add("Power_Protection:USBLC6-2SC6", "U22", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
          {"I/O1": "USB_C_DP", "I/O2": "USB_C_DN", "GND": "GND", "VBUS": "VBUS"}, LCSC="C7519", MPN="USBLC6-2SC6")
    m.R("R40", "22", "USB_C_DP", "USB_DP")
    m.R("R41", "22", "USB_C_DN", "USB_DN")

    m.block("Debug pads (UART0 ROM log, EN, IO0) - optional 1.27 mm header, not fitted",
            ["Normal flashing and logging use native USB (GPIO19/20)."])
    m.add("Connector_Generic:Conn_01x06", "J5", "DEBUG", "Connector_PinHeader_1.27mm:PinHeader_1x06_P1.27mm_Vertical",
          {"1": "+3V3", "2": "GND", "3": "ESP_EN", "4": "BOOT_N", "5": "U0TXD", "6": "U0RXD"}, dnp=True)

    # ======================================================================== SENSORS
    n = p.sheet("sensors", "Sensors and expanders")
    n.block("I2C bus (400 kHz) pull-ups",
            ["2.2 k: rise time 0.8473 x 2.2 k x C_bus; 300 ns limit -> C_bus <= 160 pF. Estimate ~150 pF with 4 ToF wires",
             "(G2 estimate, measure at G6; 1.8 k is the fallback). Devices: 0x20/0x21 expanders, 0x29 ToF (re-addressed),",
             "0x2C mag, 0x30 camera SCCB, 0x40 INA226, 0x6B charger (datasheet also says 0x6A), 0x76 baro.",
             "The Flow deck's VL53L1x sits at 0x29 with no XSHUT: firmware re-addresses it first, before releasing any satellite."])
    n.R("R50", "2.2k", "+3V3", "I2C_SDA")
    n.R("R51", "2.2k", "+3V3", "I2C_SCL")

    n.block("IMU - ICM-42688-P on SPI2 (datasheet DS-000347 Table 10/11, Fig. 7)",
            ["VDD 0.1 uF + 2.2 uF, VDDIO 10 nF. RESV pins to GND; INT2/FSYNC to GND (unused). 4-wire SPI.",
             "CS pull-up 10 k keeps the IMU deselected while the ESP32 boots."])
    n.add("microscout:ICM-42688-P", "U12", "ICM-42688-P", "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
          {"VDD": "+3V3", "VDDIO": "+3V3", "AP_CS": "IMU_CS_N", "AP_SCLK": "SPI_SCK", "AP_SDI": "SPI_MOSI",
           "AP_SDO": "SPI_MISO", "INT1": "IMU_INT1", "INT2/FSYNC": "GND", "RESV": "GND", "RESV_GND": "GND", "GND": "GND"},
          LCSC="C1850418", MPN="ICM-42688-P", Manufacturer="TDK InvenSense")
    n.C("C50", "100n", "+3V3", "GND")
    n.C("C51", "2.2u", "+3V3", "GND", pkg="0603")
    n.C("C52", "10n", "+3V3", "GND")
    n.R("R52", "10k", "+3V3", "IMU_CS_N")

    n.block("Barometer - BMP388 fitted (BMP390 same footprint; BMP390 out of stock 2026-10-07, OQ-6)",
            ["I2C: CSB to VDDIO, SDO to GND -> 0x76. 100 nF on VDD and VDDIO (datasheet Fig. 25)."])
    n.add("microscout:BMP388", "U13", "BMP388", "Package_LGA:ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y",
          {"VDD": "+3V3", "VDDIO": "+3V3", "SDI": "I2C_SDA", "SCK": "I2C_SCL", "CSB": "+3V3", "SDO": "GND",
           "INT": "BARO_INT", "VSS": "GND"}, LCSC="C779278", MPN="BMP388", Manufacturer="Bosch Sensortec",
          Alternate="BMP390 C5124834 (same pinout)")
    n.C("C53", "100n", "+3V3", "GND")
    n.C("C54", "100n", "+3V3", "GND")

    n.block("Magnetometer - QMC5883P (address 0x2C fixed)",
            ["C1 pin: 4.7 uF, ESR < 200 mOhm (datasheet 4.3.3). 100 nF VDD decoupling added by the agent (not in the datasheet)."])
    n.add("microscout:QMC5883P", "U14", "QMC5883P", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y",
          {"VDD": "+3V3", "SDA": "I2C_SDA", "SCK": "I2C_SCL", "C1": "MAG_C1", "NC": None, "GND": "GND"},
          LCSC="C2847467", MPN="QMC5883P", Manufacturer="QST")
    n.C("C55", "4.7u", "MAG_C1", "GND")
    n.C("C56", "100n", "+3V3", "GND")

    n.block("I2C GPIO expanders - TCA6408A x2 (0x20 outputs, 0x21 inputs); RESET pulled up, INT wired-OR to GPIO3",
            ["Expander pins power up as inputs, so the external pulls set the safe state: ToF in reset (XSHUT low,",
             "LPn low on the satellite), camera powered down (PWDN high) and held in reset."])
    n.add("microscout:TCA6408A_RGT", "U10", "TCA6408A", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm",
          {"VCCI": "+3V3", "VCCP": "+3V3", "SDA": "I2C_SDA", "SCL": "I2C_SCL", "~{INT}": "EXP_INT_N",
           "~{RESET}": "EXP_RESET_N", "ADDR": "GND", "P0": None, "P1": "TOF_LEFT_XSHUT", "P2": "TOF_RIGHT_XSHUT",
           "P3": "TOF_REAR_XSHUT", "P4": "TOF_FWD_LPN", "P5": "CAM_PWDN", "P6": "CAM_RESET_N", "P7": None,
           "GND": "GND", "EP": "GND"}, LCSC="C181499", MPN="TCA6408ARGTR", Manufacturer="Texas Instruments")
    n.add("microscout:TCA6408A_RGT", "U11", "TCA6408A", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm",
          {"VCCI": "+3V3", "VCCP": "+3V3", "SDA": "I2C_SDA", "SCL": "I2C_SCL", "~{INT}": "EXP_INT_N",
           "~{RESET}": "EXP_RESET_N", "ADDR": "+3V3", "P0": "TOF_FWD_INT_N", "P1": "CHG_INT_N", "P2": "VBUS_DET",
           "P3": "PWR_BTN_INT_N", "P4": None, "P5": "BARO_INT", "P6": None, "P7": None,
           "GND": "GND", "EP": "GND"}, LCSC="C181499", MPN="TCA6408ARGTR", Manufacturer="Texas Instruments")
    n.C("C57", "100n", "+3V3", "GND")
    n.C("C58", "100n", "+3V3", "GND")
    n.R("R53", "10k", "+3V3", "EXP_RESET_N")
    n.R("R54", "10k", "CAM_PWDN", "+3V3")
    n.R("R55", "10k", "CAM_RESET_N", "GND")

    n.block("ToF satellite boards (hardware/tof-side x3, hardware/tof-front x1) - wire pads",
            ["Side boards: VL53L1X, XSHUT 10 k pull-down on the satellite. Front board: VL53L5CX, LPn/INT/I2C_RST pulls on",
             "the satellite. Firmware re-addresses every sensor at boot (all power up at 0x29)."])
    for ref, side in (("J11", "LEFT"), ("J12", "RIGHT"), ("J13", "REAR")):
        n.add("Connector_Generic:Conn_01x05", ref, f"ToF {side.lower()}", "Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical",
              {"1": "+3V3", "2": "GND", "3": "I2C_SDA", "4": "I2C_SCL", "5": f"TOF_{side}_XSHUT"},
              Note="Solder pads for a 5-wire flex/cable; footprint set at G3")
    n.add("Connector_Generic:Conn_01x06", "J14", "ToF front", "Connector_PinHeader_1.27mm:PinHeader_1x06_P1.27mm_Vertical",
          {"1": "+3V3", "2": "GND", "3": "I2C_SDA", "4": "I2C_SCL", "5": "TOF_FWD_LPN", "6": "TOF_FWD_INT_N"},
          Note="Solder pads for a 6-wire flex/cable; footprint set at G3")

    n.block("Optical flow - Bitcraze Flow deck v2 (PMW3901 + VL53L1x), wired to pads (OQ-4)",
            ["Deck pins used: VCC, GND, SCK, MISO, MOSI, IO_3 (PMW3901 CS), SDA, SCL (Bitcraze deck pinout).",
             "Fed from 3.3 V; the Crazyflie supplies 3.0 V - whether 3.3 V is within the deck's limits is UNCONFIRMED (G2 check).",
             "CS pull-up 10 k keeps the flow sensor deselected during boot."])
    n.add("microscout:FlowDeck_Link", "J10", "Flow deck v2", "Connector_PinHeader_1.27mm:PinHeader_1x08_P1.27mm_Vertical",
          {"VCC": "+3V3", "GND": "GND", "SCK": "SPI_SCK", "MISO": "SPI_MISO", "MOSI": "SPI_MOSI", "CS_IO3": "FLOW_CS_N",
           "SDA": "I2C_SDA", "SCL": "I2C_SCL"}, Note="Pads; module bought from Bitcraze (~$55)")
    n.R("R56", "10k", "+3V3", "FLOW_CS_N")

    # ======================================================================== CAMERA AND IO
    c = p.sheet("io", "Camera, LEDs, buzzer, receiver")
    c.block("Camera - OV2640 on a 24-pin 0.5 mm FPC (pinout: Espressif ESP32-S3-EYE MB v2.2, J4)",
            ["AVDD + DOVDD 2.8 V (as ESP32-S3-EYE); DVDD 1.2 V (OV2640 datasheet core 1.14-1.26 V; the S3-EYE uses 1.5 V -",
             "conflict noted, G2 check against the purchased module). Rails are always on with 3V3 (D-049); PWDN (pulled high)",
             "keeps the sensor in standby. SCCB is on the main 3.3 V I2C bus (as on the S3-EYE) - level margin is a G2 check."])
    c.add("Connector_Generic_MountingPin:Conn_01x24_MountingPin", "J3", "OV2640 FPC 24P", "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal",
          {"1": None, "2": "GND", "3": "I2C_SDA", "4": "+2V8", "5": "I2C_SCL", "6": "CAM_RESET_N", "7": "CAM_VSYNC",
           "8": "CAM_PWDN", "9": "CAM_HREF", "10": "+1V2", "11": "+2V8", "12": "CAM_D7", "13": "CAM_XCLK",
           "14": "CAM_D6", "15": "GND", "16": "CAM_D5", "17": "CAM_PCLK", "18": "CAM_D4", "19": "CAM_D0",
           "20": "CAM_D3", "21": "CAM_D1", "22": "CAM_D2", "23": None, "24": None, "MP": "GND"},
          LCSC="C2856805", MPN="FPC-05F-24PH20", Note="Footprint is a Hirose FH12 stand-in; pin-1 side to confirm at G3")
    c.add("microscout:ME6211Cxx", "U6", "ME6211C28", "Package_TO_SOT_SMD:SOT-23-5",
          {"VIN": "+3V3", "CE": "+3V3", "VSS": "GND", "VOUT": "+2V8", "NC": None}, LCSC="C53099", MPN="ME6211C28M5G-N")
    c.add("microscout:ME6211Cxx", "U7", "ME6211C12", "Package_TO_SOT_SMD:SOT-23-5",
          {"VIN": "+3V3", "CE": "+3V3", "VSS": "GND", "VOUT": "+1V2", "NC": None}, LCSC="C236672", MPN="ME6211C12M5G-N")
    c.C("C60", "1u", "+3V3", "GND")
    c.C("C61", "1u", "+3V3", "GND")
    c.C("C62", "10u", "+2V8", "GND", pkg="0603")
    c.C("C63", "100n", "+2V8", "GND")
    c.C("C64", "10u", "+1V2", "GND", pkg="0603")
    c.C("C65", "100n", "+1V2", "GND")

    c.block("Status LEDs - 4x WS2812B-2020 on 5 V; SN74AHCT1G125 shifts 3.3 V data to 5 V (WS2812B VIH = 0.65 VDD)",
            ["Data from GPIO45 via SPI3 MOSI (D-042). 100 nF per LED (agent choice; the LED datasheet says none is needed)."])
    c.add("74xGxx:74AHCT1G125", "U21", "SN74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5",
          {"1": "GND", "2": "LED_DIN_3V3", "3": "GND", "4": "LED_D0", "5": "+5V"}, LCSC="C7484", MPN="SN74AHCT1G125DBVR")
    c.C("C66", "100n", "+5V", "GND")
    chain = ["LED_D0", "LED_D1", "LED_D2", "LED_D3", None]
    for i in range(4):
        c.add("LED:WS2812B-2020", f"LED{i + 1}", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
              {"DIN": chain[i], "DOUT": chain[i + 1], "VDD": "+5V", "VSS": "GND"}, LCSC="C965555", MPN="WS2812B-2020")
        c.C(f"C{67 + i}", "100n", "+5V", "GND")

    c.block("Buzzer - magnetic MLT-5020 driven by AO3400A from 5 V (rated voltage UNCONFIRMED; G2 check)",
            ["GPIO46 is a strapping pin that must be low at boot: 100 k gate pull-down keeps it low and the FET off."])
    c.add("Transistor_FET:AO3400A", "Q3", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
          {"G": "BUZZER", "S": "GND", "D": "BUZZER_DRV"}, LCSC="C20917", MPN="AO3400A")
    c.R("R60", "100k", "BUZZER", "GND")
    c.add("Device:Buzzer", "BZ1", "MLT-5020", "microscout:Buzzer_MLT-5020_TBD",
          {"+": "+5V", "-": "BUZZER_DRV"}, LCSC="C94598", MPN="MLT-5020")
    c.D("D1", "1N5819WS", "BUZZER_DRV", "+5V", LCSC="C191023", MPN="1N5819WS")

    c.block("ExpressLRS receiver pads (CRSF, 420 kbaud) - BetaFPV ELRS Lite or similar, powered from 5 V",
            ["Receiver TX -> GPIO41 (CRSF_RX); receiver RX <- GPIO42 (CRSF_TX)."])
    c.add("Connector_Generic:Conn_01x04", "J4", "ELRS RX", "Connector_PinHeader_1.27mm:PinHeader_1x04_P1.27mm_Vertical",
          {"1": "+5V", "2": "GND", "3": "CRSF_RX", "4": "CRSF_TX"}, Note="Solder pads; footprint set at G3")
    return p


if __name__ == "__main__":
    proj = build()
    proj.write()
    print(f"wrote {OUT.relative_to(REPO)} ({len(proj.parts)} parts incl. flags, {len(proj.sheets)} sheets)")
