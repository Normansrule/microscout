#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Cross-check review/G1/pin-allocation.csv against ESP32-S3-WROOM-1 module facts.

Facts encoded below come from the Espressif ESP32-S3-WROOM-1/1U datasheet v1.8
(https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf),
Table 1-1 (variants), Table 3-1 (pin definitions), Tables 4-1..4-4 (strapping).
The human must re-check this table against the datasheet revision of the exact
modules purchased. This script only proves the CSV is self-consistent with the
facts typed in here; it does not prove those facts.

Usage: python3 review/G1/calc/check_pins.py [--module N8R2|N16R8]
Exit code 0 = no errors (warnings may still need human review).
"""
import csv
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
CSV = HERE.parent / "pin-allocation.csv"

# Table 3-1: GPIO -> module pin number (GPIO43/44 appear as TXD0/RXD0).
MODULE_PIN = {
    4: 4, 5: 5, 6: 6, 7: 7, 15: 8, 16: 9, 17: 10, 18: 11, 8: 12, 19: 13,
    20: 14, 3: 15, 46: 16, 9: 17, 10: 18, 11: 19, 12: 20, 13: 21, 14: 22,
    21: 23, 47: 24, 48: 25, 45: 26, 0: 27, 35: 28, 36: 29, 37: 30, 38: 31,
    39: 32, 40: 33, 41: 34, 42: 35, 44: 36, 43: 37, 2: 38, 1: 39,
}
OCTAL_PSRAM_RESERVED = {35, 36, 37}          # R8 / R16V variants only
STRAPPING = {
    0: "must be 1 for SPI boot (weak pull-up)",
    3: "JTAG source select when eFuse enables it; no internal pull",
    45: "VDD_SPI select: must be 0 for 3.3 V flash modules (weak pull-down)",
    46: "must be 0 for joint download with GPIO0=0; ROM log routing (weak pull-down)",
}
FIXED = {19: "USB_D-", 20: "USB_D+", 43: "U0TXD", 44: "U0RXD"}
JTAG_DEFAULT = {39: "MTCK", 40: "MTDO", 41: "MTDI", 42: "MTMS"}
ADC1 = set(range(1, 11))                      # ADC1_CH0..CH9 = GPIO1..10
MOTOR_PREFIX = "MOT"


def load_rows():
    lines = [l for l in CSV.read_text().splitlines() if l and not l.startswith("#")]
    return list(csv.DictReader(lines))


def main():
    module = "N8R2"
    if "--module" in sys.argv:
        module = sys.argv[sys.argv.index("--module") + 1].upper()
    octal = module.endswith(("R8", "R16VA"))
    rows = load_rows()
    errors, warns, info = [], [], []

    seen_gpio, seen_net = {}, {}
    for r in rows:
        g = int(r["gpio"])
        net = r["net"].strip()
        if g in seen_gpio:
            errors.append(f"GPIO{g} assigned twice ({seen_gpio[g]} and {net})")
        seen_gpio[g] = net
        if net in seen_net:
            errors.append(f"net {net} on two GPIOs ({seen_net[net]} and {g})")
        seen_net[net] = g
        if g not in MODULE_PIN:
            errors.append(f"GPIO{g} ({net}) is not brought out on WROOM-1")
            continue
        if int(r["module_pin"]) != MODULE_PIN[g]:
            errors.append(f"GPIO{g}: CSV module pin {r['module_pin']} != datasheet pin {MODULE_PIN[g]}")
        if octal and g in OCTAL_PSRAM_RESERVED:
            errors.append(f"GPIO{g} ({net}) is used by octal PSRAM on {module}")
        if g in FIXED:
            expected_prefix = "USB_" if g in (19, 20) else "U0"
            if not net.startswith(expected_prefix):
                errors.append(f"GPIO{g} is fixed {FIXED[g]} but carries {net}")
        if g in STRAPPING:
            note = r["boot_or_conflict_notes"].lower()
            if "strapping" not in note:
                errors.append(f"GPIO{g} is a strapping pin but its notes don't say so")
            pull = r["external_pull"].lower()
            if g == 0 and "pull-up" not in pull:
                errors.append("GPIO0 needs an external pull-up for SPI boot")
            if g in (45, 46) and ("pull-up" in pull or "pull-down" not in pull or pull.startswith("none")):
                errors.append(f"GPIO{g} must be held low at boot: needs an external pull-down and no pull-up (has: {r['external_pull']})")
            warns.append(f"GPIO{g} ({net}) strapping: {STRAPPING[g]}. Pull: {r['external_pull']}")
        if g in JTAG_DEFAULT:
            warns.append(f"GPIO{g} ({net}) is default JTAG {JTAG_DEFAULT[g]}; confirm pad state during reset before relying on it")
        if net.startswith(MOTOR_PREFIX):
            if g in STRAPPING or g in JTAG_DEFAULT or g in OCTAL_PSRAM_RESERVED:
                errors.append(f"motor gate {net} on boot-sensitive GPIO{g}")
            if "pull-down" not in r["external_pull"].lower():
                errors.append(f"motor gate {net} has no pull-down")
        if "analog" in r["direction"].lower() and g not in ADC1:
            errors.append(f"{net} on GPIO{g} is analog but not an ADC1 pin")

    free = sorted(set(MODULE_PIN) - set(seen_gpio) - (OCTAL_PSRAM_RESERVED if octal else set()))
    total = len(MODULE_PIN) - (len(OCTAL_PSRAM_RESERVED) if octal else 0)
    info.append(f"module variant checked: {module} ({'octal' if octal else 'quad/no'} PSRAM)")
    info.append(f"GPIOs brought out and usable: {total}; assigned: {len(seen_gpio)}; spare: {len(free)} {free}")

    out = []
    out.append("STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1")
    out.append(f"Pin check report for {CSV.name}")
    out += ["INFO  " + s for s in info]
    out += ["ERROR " + s for s in errors]
    out += ["WARN  " + s for s in warns]
    out.append(f"RESULT: {len(errors)} error(s), {len(warns)} warning(s) for human review")
    text = "\n".join(out)
    print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
