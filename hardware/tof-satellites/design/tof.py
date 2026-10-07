# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""MicroScout ToF satellite boards: side (VL53L1X, x3: left/right/rear) and front (VL53L5CX).

Run: python3 hardware/tof-satellites/design/tof.py
Licence of this hardware description: CERN-OHL-S-2.0.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "sch"))
from schgen import Project  # noqa: E402

LIB = {"microscout": str(REPO / "hardware" / "libraries" / "microscout.kicad_sym")}


def side():
    p = Project("microscout-tof-side", REPO / "hardware" / "tof-satellites" / "side", "MicroScout ToF side satellite", "G2-draft-1", LIB)
    s = p.sheet("tof", "VL53L1X satellite")
    s.block("VL53L1X (ST datasheet Fig. 3: 4.7 uF + 100 nF at AVDDVCSEL; XSHUT/GPIO1 pull-ups 10 k)",
            ["XSHUT has a 10 k pull-DOWN here instead of the datasheet's pull-up: the sensor stays in reset until firmware",
             "releases it, which the boot-time re-addressing needs (all VL53L1X start at 0x29). GPIO1 interrupt not used.",
             "I2C pull-ups are on the FC board only. 3 boards fitted: left, right, rear."])
    s.add("Sensor_Distance:VL53L1CXV0FY1", "U1", "VL53L1X", "Sensor_Distance:ST_VL53L1x",
          {"AVDDVCSEL": "+3V3", "AVSSVCSEL": "GND", "GND": "GND", "XSHUT": "XSHUT", "GPIO1": None, "DNC": None,
           "SDA": "SDA", "SCL": "SCL", "AVDD": "+3V3"}, LCSC="C190004", MPN="VL53L1CXV0FY/1", Manufacturer="STMicroelectronics")
    s.C("C1", "4.7u", "+3V3", "GND")
    s.C("C2", "100n", "+3V3", "GND")
    s.R("R1", "10k", "XSHUT", "GND")
    s.add("Connector_Generic:Conn_01x05", "J1", "to FC", "Connector_PinHeader_1.27mm:PinHeader_1x05_P1.27mm_Vertical",
          {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "XSHUT"}, Note="Solder pads; mirrors FC J11-J13")
    s.add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", {"1": "GND"})
    s.add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", "", {"1": "+3V3"})
    return p


def front():
    p = Project("microscout-tof-front", REPO / "hardware" / "tof-satellites" / "front", "MicroScout ToF front satellite", "G2-draft-1", LIB)
    s = p.sheet("tof", "VL53L5CX satellite")
    s.block("VL53L5CX 8x8 multizone (ST DS13754 Rev 13: Table 3 pull-ups, Fig. 5 capacitors, Table 12 supplies)",
            ["AVDD = IOVDD = 3.3 V (allowed combination). 4.7 uF + 100 nF on each supply (assignment to pins UNCONFIRMED).",
             "INT 47 k up, I2C_RST 47 k down (datasheet). LPn 47 k pull-DOWN (datasheet: up) so I2C stays off until firmware",
             "re-addresses it. C2 (RSVD6) 47 k up per the datasheet note - pin function UNCONFIRMED. RSVD pins to GND."])
    s.add("microscout:VL53L5CX", "U1", "VL53L5CX", "microscout:ST_VL53L5CX_LGA16_TBD",
          {"AVDD": "+3V3", "IOVDD": "+3V3", "SDA": "SDA", "SCL": "SCL", "INT": "INT_N", "LPn": "LPN",
           "I2C_RST": "I2C_RST", "RSVD6": "RSVD6", "RSVD5_DNC": None, "RSVD": "GND", "GND": "GND", "THERMALPAD": "GND"},
          LCSC="C3178303", MPN="VL53L5CXV0GC/1", Manufacturer="STMicroelectronics")
    s.C("C1", "4.7u", "+3V3", "GND")
    s.C("C2", "100n", "+3V3", "GND")
    s.C("C3", "4.7u", "+3V3", "GND")
    s.C("C4", "100n", "+3V3", "GND")
    s.R("R1", "47k", "+3V3", "INT_N")
    s.R("R2", "47k", "LPN", "GND")
    s.R("R3", "47k", "I2C_RST", "GND")
    s.R("R4", "47k", "+3V3", "RSVD6")
    s.add("Connector_Generic:Conn_01x06", "J1", "to FC", "Connector_PinHeader_1.27mm:PinHeader_1x06_P1.27mm_Vertical",
          {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "LPN", "6": "INT_N"}, Note="Solder pads; mirrors FC J14")
    s.add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", {"1": "GND"})
    s.add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", "", {"1": "+3V3"})
    return p


def build():
    return [side(), front()]


if __name__ == "__main__":
    for proj in build():
        proj.write()
        print(f"wrote {proj.outdir.relative_to(REPO)} ({len(proj.parts)} parts)")
