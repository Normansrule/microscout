# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""Build hardware/libraries/microscout.kicad_sym: symbols missing from the KiCad 7 library.

Every pin table below is copied from the manufacturer datasheet named in the symbol's
Datasheet field (read 2026-10-07; see review/G2/sources.md). Pins of the same name on the
same side are stacked (extra pins hidden), as KiCad's own library does.
Licence: MIT (software/LICENSE).
"""
import copy
import pathlib

from sexpr import Sym, dump, find, find_all, parse

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "hardware" / "libraries" / "microscout.kicad_sym"
P = 2.54

# (symbol name, reference prefix, description, datasheet, default footprint, pins)
# pin = (number, name, electrical type, side L/R/T/B)
SYMBOLS = [
    ("ME6211Cxx", "U", "Microne ME6211 500 mA LDO, SOT-23-5 (fixed output; value gives voltage)",
     "https://datasheet.lcsc.com/datasheet/pdf/d15331d096a848ac81a26b001a32d4e3.pdf", "Package_TO_SOT_SMD:SOT-23-5",
     [("1", "VIN", "power_in", "L"), ("3", "CE", "input", "L"), ("2", "VSS", "power_in", "B"),
      ("5", "VOUT", "power_out", "R"), ("4", "NC", "no_connect", "R")]),
    ("TCA6408A_RGT", "U", "TI TCA6408A 8-bit I2C GPIO expander, VQFN-16 (RGT)",
     "https://www.ti.com/lit/ds/symlink/tca6408a.pdf", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm",
     [("15", "VCCI", "power_in", "T"), ("14", "VCCP", "power_in", "T"),
      ("13", "SDA", "bidirectional", "L"), ("12", "SCL", "input", "L"), ("11", "~{INT}", "open_collector", "L"),
      ("1", "~{RESET}", "input", "L"), ("16", "ADDR", "input", "L"),
      ("2", "P0", "bidirectional", "R"), ("3", "P1", "bidirectional", "R"), ("4", "P2", "bidirectional", "R"),
      ("5", "P3", "bidirectional", "R"), ("7", "P4", "bidirectional", "R"), ("8", "P5", "bidirectional", "R"),
      ("9", "P6", "bidirectional", "R"), ("10", "P7", "bidirectional", "R"),
      ("6", "GND", "power_in", "B"), ("17", "EP", "passive", "B")]),
    ("VL53L5CX", "U", "ST VL53L5CX 8x8 multizone ToF, optical LGA-16",
     "https://www.st.com/resource/en/datasheet/vl53l5cx.pdf", "microscout:ST_VL53L5CX_LGA16_TBD",
     [("B1", "AVDD", "power_in", "T"), ("B7", "AVDD", "power_in", "T"), ("A4", "IOVDD", "power_in", "T"),
      ("C3", "SDA", "bidirectional", "L"), ("C4", "SCL", "input", "L"), ("A3", "INT", "open_collector", "L"),
      ("A5", "LPn", "input", "L"), ("A1", "I2C_RST", "input", "L"),
      ("C2", "RSVD6", "passive", "R"), ("C5", "RSVD5_DNC", "no_connect", "R"),
      ("A2", "RSVD", "passive", "R"), ("A6", "RSVD", "passive", "R"), ("A7", "RSVD", "passive", "R"), ("C6", "RSVD", "passive", "R"),
      ("C1", "GND", "power_in", "B"), ("C7", "GND", "power_in", "B"), ("B4", "THERMALPAD", "passive", "B")]),
    ("ICM-42688-P", "U", "TDK InvenSense ICM-42688-P 6-axis IMU, LGA-14 2.5x3",
     "https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ds-000347-icm-42688-p-v1.6.pdf",
     "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
     [("8", "VDD", "power_in", "T"), ("5", "VDDIO", "power_in", "T"),
      ("12", "AP_CS", "input", "L"), ("13", "AP_SCLK", "input", "L"), ("14", "AP_SDI", "input", "L"),
      ("1", "AP_SDO", "output", "L"),
      ("4", "INT1", "output", "R"), ("9", "INT2/FSYNC", "input", "R"),
      ("2", "RESV", "passive", "R"), ("3", "RESV", "passive", "R"), ("10", "RESV", "passive", "R"), ("11", "RESV", "passive", "R"),
      ("6", "GND", "power_in", "B"), ("7", "RESV_GND", "passive", "B")]),
    ("BMP388", "U", "Bosch BMP388/BMP390 barometer (same pinout), LGA-10 2x2",
     "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf",
     "Package_LGA:ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y",
     [("10", "VDD", "power_in", "T"), ("1", "VDDIO", "power_in", "T"),
      ("4", "SDI", "bidirectional", "L"), ("2", "SCK", "input", "L"), ("6", "CSB", "input", "L"), ("5", "SDO", "passive", "L"),
      ("7", "INT", "output", "R"),
      ("3", "VSS", "power_in", "B"), ("8", "VSS", "power_in", "B"), ("9", "VSS", "power_in", "B")]),
    ("QMC5883P", "U", "QST QMC5883P 3-axis magnetometer, LGA-16 3x3",
     "https://cdn-shop.adafruit.com/product-files/6388/C2847467.pdf", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y",
     [("2", "VDD", "power_in", "T"),
      ("16", "SDA", "bidirectional", "L"), ("1", "SCK", "input", "L"),
      ("10", "C1", "passive", "R")]
     + [(str(n), "NC", "no_connect", "R") for n in (3, 4, 5, 6, 7, 8, 12, 13, 14, 15)]
     + [("9", "GND", "power_in", "B"), ("11", "GND", "power_in", "B")]),
    ("LTC2954-1", "U", "Analog Devices LTC2954-1 pushbutton on/off controller (EN active high), TSOT-23-8",
     "https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf", "Package_TO_SOT_SMD:TSOT-23-8",
     [("1", "VIN", "power_in", "T"),
      ("2", "~{PB}", "input", "L"), ("8", "~{KILL}", "input", "L"), ("3", "ONT", "passive", "L"), ("7", "PDT", "passive", "L"),
      ("6", "EN", "open_collector", "R"), ("5", "~{INT}", "open_collector", "R"),
      ("4", "GND", "power_in", "B")]),
    ("TLV6700DDC", "U", "TI TLV6700 dual window comparator/supervisor, open-drain, SOT-23-6 (DDC)",
     "https://www.ti.com/lit/ds/symlink/tlv6700.pdf", "Package_TO_SOT_SMD:TSOT-23-6",
     [("5", "VDD", "power_in", "T"),
      ("3", "INA+", "input", "L"), ("4", "INB-", "input", "L"),
      ("1", "OUTA", "open_collector", "R"), ("6", "OUTB", "open_collector", "R"),
      ("2", "GND", "power_in", "B")]),
    ("TPS22810DBV", "U", "TI TPS22810 2.7-18 V 2 A load switch, SOT-23-6 (DBV)",
     "https://www.ti.com/lit/ds/symlink/tps22810.pdf", "Package_TO_SOT_SMD:SOT-23-6",
     [("1", "VIN", "power_in", "L"), ("3", "EN/UVLO", "input", "L"), ("4", "CT", "passive", "L"),
      ("6", "VOUT", "power_out", "R"), ("5", "QOD", "passive", "R"),
      ("2", "GND", "power_in", "B")]),
    ("FD6288Q", "U", "Fortior FD6288Q three-phase half-bridge gate driver, QFN-24 4x4 (outputs in phase with inputs)",
     "https://shop.mev-elektronik.com/wp-content/uploads/FD6288.pdf", "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
     [("4", "VCC", "power_in", "T"),
      ("22", "HIN1", "input", "L"), ("23", "HIN2", "input", "L"), ("24", "HIN3", "input", "L"),
      ("1", "LIN1", "input", "L"), ("2", "LIN2", "input", "L"), ("3", "LIN3", "input", "L"),
      ("20", "VB1", "passive", "R"), ("19", "HO1", "output", "R"), ("18", "VS1", "passive", "R"),
      ("17", "VB2", "passive", "R"), ("16", "HO2", "output", "R"), ("15", "VS2", "passive", "R"),
      ("14", "VB3", "passive", "R"), ("13", "HO3", "output", "R"), ("12", "VS3", "passive", "R"),
      ("11", "LO1", "output", "R"), ("10", "LO2", "output", "R"), ("9", "LO3", "output", "R"),
      ("6", "COM", "power_in", "B"), ("25", "EP", "passive", "B")]
     + [(str(n), "NC", "no_connect", "B") for n in (5, 7, 8, 21)]),
    ("AT32F421G8U7", "U", "Artery AT32F421G8U7 Cortex-M4 MCU, QFN-28 4x4 (PA11/PA12 not bonded)",
     "https://www.arterytek.com/ (datasheet DS_AT32F421 V2.02)", "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.6x2.6mm",
     [("17", "VDD", "power_in", "T"), ("5", "VDDA", "power_in", "T"),
      ("4", "NRST", "input", "L"), ("1", "BOOT0", "input", "L"), ("2", "PF0", "bidirectional", "L"), ("3", "PF1", "bidirectional", "L"),
      ("6", "PA0", "bidirectional", "L"), ("7", "PA1", "bidirectional", "L"), ("8", "PA2", "bidirectional", "L"),
      ("9", "PA3", "bidirectional", "L"), ("10", "PA4", "bidirectional", "L"), ("11", "PA5", "bidirectional", "L"),
      ("12", "PA6", "bidirectional", "L"), ("13", "PA7", "bidirectional", "L"),
      ("18", "PA8", "bidirectional", "R"), ("19", "PA9", "bidirectional", "R"), ("20", "PA10", "bidirectional", "R"),
      ("21", "PA13/SWDIO", "bidirectional", "R"), ("22", "PA14/SWCLK", "bidirectional", "R"), ("23", "PA15", "bidirectional", "R"),
      ("14", "PB0", "bidirectional", "R"), ("15", "PB1", "bidirectional", "R"), ("24", "PB3", "bidirectional", "R"),
      ("25", "PB4", "bidirectional", "R"), ("26", "PB5", "bidirectional", "R"), ("27", "PB6", "bidirectional", "R"),
      ("28", "PB7", "bidirectional", "R"),
      ("16", "VSS", "power_in", "B"), ("29", "EP_VSS", "passive", "B")]),
    ("BQ25887_RGE", "U", "TI BQ25887 2S boost charger with cell balancing, VQFN-24 (RGE) incl. exposed pad",
     "https://www.ti.com/lit/ds/symlink/bq25887.pdf", "Package_DFN_QFN:Texas_RGE0024H_VQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
     [("23", "VBUS", "power_in", "L"), ("21", "PMID", "power_out", "L"), ("22", "PMID", "power_out", "L"),
      ("24", "PSEL", "input", "L"), ("3", "CD", "input", "L"), ("8", "ILIM", "input", "L"), ("7", "TS", "input", "L"),
      ("4", "SDA", "bidirectional", "L"), ("5", "SCL", "input", "L"),
      ("17", "SW", "power_out", "R"), ("18", "SW", "power_out", "R"), ("12", "BTST", "passive", "R"), ("11", "REGN", "power_out", "R"),
      ("15", "SNS", "passive", "R"), ("16", "SNS", "passive", "R"), ("13", "BAT", "power_out", "R"), ("14", "BAT", "power_out", "R"),
      ("9", "MID", "input", "R"), ("10", "CBSET", "passive", "R"),
      ("1", "~{PG}", "open_collector", "R"), ("2", "STAT", "open_collector", "R"), ("6", "~{INT}", "open_collector", "R"),
      ("19", "GND", "power_in", "B"), ("20", "GND", "power_in", "B"), ("25", "EP", "passive", "B")]),
    ("MT3608", "U", "Aerosemi MT3608 1.2 MHz 2 A boost converter, SOT-23-6 (VREF 0.6 V)",
     "https://www.lcsc.com/datasheet/C84817.pdf", "Package_TO_SOT_SMD:SOT-23-6",
     [("5", "IN", "power_in", "L"), ("4", "EN", "input", "L"), ("1", "SW", "output", "R"), ("3", "FB", "input", "R"),
      ("6", "NC", "no_connect", "R"), ("2", "GND", "power_in", "B")]),
    ("NMOS_PDFN3333", "Q", "N-channel MOSFET, PDFN3333-8 / PowerPAK 1212-8 pinout (1-3 S, 4 G, 5-8 + pad D)",
     "https://datasheet.lcsc.com/datasheet/pdf/bd8b126d6ff95c77de6f200dd9f0ad95.pdf?productCode=C7471100",
     "Package_SO:Vishay_PowerPAK_1212-8_Single",
     [("4", "G", "input", "L"), ("5", "D", "passive", "T"),
      ("1", "S", "passive", "B"), ("2", "S", "passive", "B"), ("3", "S", "passive", "B")]),
    ("FlowDeck_Link", "J", "Wire pads to a Bitcraze Flow deck v2 (PMW3901 + VL53L1x)",
     "https://www.bitcraze.io/products/flow-deck-v2/", "microscout:Pads_1x08_TBD",
     [("1", "VCC", "passive", "L"), ("2", "GND", "passive", "L"), ("3", "SCK", "passive", "L"), ("4", "MISO", "passive", "L"),
      ("5", "MOSI", "passive", "L"), ("6", "CS_IO3", "passive", "L"), ("7", "SDA", "passive", "L"), ("8", "SCL", "passive", "L")]),
]

POWER_NETS = ["VBAT", "VLOGIC", "VDRV", "+3V3_ESC"]


def efont(hide=False):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), 1.27, 1.27]]]
    if hide:
        e.append(Sym("hide"))
    return e


def lprop(name, value, x=0.0, y=0.0, hide=False):
    return [Sym("property"), name, value, [Sym("at"), x, y, 0], efont(hide)]


def build_symbol(name, refp, desc, ds, fp, pinspec):
    sides = {"L": [], "R": [], "T": [], "B": []}
    for num, pname, ptype, side in pinspec:
        grp = sides[side]
        for g in grp:
            if g[0] == pname and pname not in ("NC",):
                g[1].append((num, ptype))
                break
        else:
            grp.append([pname, [(num, ptype)]])
    def nchars(lst):
        return max((len(g[0].replace("~{", "").replace("}", "")) for g in lst), default=0)
    width = max(10.16, (nchars(sides["L"]) + nchars(sides["R"])) * 1.0 + 5.08,
                max(len(sides["T"]), len(sides["B"])) * P + P)
    half_w = max(5.08, ((width / 2) // P + 1) * P)
    rows = max(len(sides["L"]), len(sides["R"]), 1)
    half_h = max(5.08, ((rows * P) / 2 // P + 1) * P)
    if sides["T"]:
        half_h += P
    if sides["B"]:
        half_h += P
    pins = []

    def add(pname, group, x, y, ang):
        first = True
        for num, ptype in group:
            node = [Sym("pin"), Sym(ptype if first else ("passive" if ptype not in ("no_connect",) else ptype)),
                    Sym("line"), [Sym("at"), round(x, 4), round(y, 4), ang], [Sym("length"), P]]
            if not first:
                node.append(Sym("hide"))
            node += [[Sym("name"), pname, efont()], [Sym("number"), num, efont()]]
            pins.append(node)
            first = False

    top_y = half_h - (P if sides["T"] else 0) - P
    for i, (pname, grp) in enumerate(sides["L"]):
        add(pname, grp, -half_w - P, top_y - i * P, 0)
    for i, (pname, grp) in enumerate(sides["R"]):
        add(pname, grp, half_w + P, top_y - i * P, 180)
    for i, (pname, grp) in enumerate(sides["T"]):
        x = (i - (len(sides["T"]) - 1) / 2) * P * 2
        add(pname, grp, round(x / P) * P, half_h + P, 270)
    for i, (pname, grp) in enumerate(sides["B"]):
        x = (i - (len(sides["B"]) - 1) / 2) * P * 2
        add(pname, grp, round(x / P) * P, -half_h - P, 90)
    body = [Sym("symbol"), f"{name}_0_1",
            [Sym("rectangle"), [Sym("start"), -half_w, half_h], [Sym("end"), half_w, -half_h],
             [Sym("stroke"), [Sym("width"), 0.254], [Sym("type"), Sym("default")]], [Sym("fill"), [Sym("type"), Sym("background")]]]]
    return [Sym("symbol"), name, [Sym("pin_names"), [Sym("offset"), 1.016]], [Sym("in_bom"), Sym("yes")], [Sym("on_board"), Sym("yes")],
            lprop("Reference", refp, -half_w, half_h + 1.27), lprop("Value", name, -half_w, -half_h - 1.27),
            lprop("Footprint", fp, 0, 0, True), lprop("Datasheet", ds, 0, 0, True),
            lprop("ki_description", desc, 0, 0, True),
            body, [Sym("symbol"), f"{name}_1_1"] + pins]


def power_symbol(net):
    vend = REPO / "hardware" / "libraries" / "kicad7-symbols" / "power.kicad_sym"
    tree = parse((vend if vend.exists() else pathlib.Path("/usr/share/kicad/symbols/power.kicad_sym")).read_text())[0]
    base = next(e for e in find_all(tree, "symbol") if e[1] == "+3V3")
    s = copy.deepcopy(base)
    s[1] = net
    for e in s:
        if isinstance(e, list) and e and e[0] == "property":
            if e[1] == "Value":
                e[2] = net
            if e[1] == "ki_description":
                e[2] = f'Power symbol creates a global label with name "{net}"'
        if isinstance(e, list) and e and e[0] == "symbol":
            e[1] = e[1].replace("+3V3", net, 1)
            for pn in find_all(e, "pin"):
                find(pn, "name")[1] = net
    return s


def main():
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), Sym("20220914")], [Sym("generator"), Sym("microscout_customsyms")]]
    for net in POWER_NETS:
        lib.append(power_symbol(net))
    for spec in SYMBOLS:
        lib.append(build_symbol(*spec))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(dump(lib) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}: {len(POWER_NETS)} power + {len(SYMBOLS)} part symbols")


if __name__ == "__main__":
    main()
