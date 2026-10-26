#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wisp Phase 0 parts lists and gram-by-gram weight budgets.

Writes review/P0/parts.md and review/P0/parts/*.csv from the tables below, so every total is computed, never
typed. Sources and the date each figure was seen are in review/P0/research/. Run: python3 review/P0/calc/budget.py

Basis codes: CLAIM (maker or shop figure), DERIVED (computed from claims), ESTIMATE (assumption, stated),
UNCONFIRMED (not verified). Prices in USD as seen on 2026-10-26; stock as shown that day.
"""
import csv
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
P0 = HERE.parent

# 14 CFR 48.15(b): no registration for a recreational aircraft that "weighs 0.55 pounds or less on takeoff,
# including everything that is on board or otherwise attached". 0.55 lb x 453.59237 g/lb = 249.48 g.
LIMIT_G = 0.55 * 453.59237
TARGET_MARGIN_G = 5.0      # ESTIMATE: room for scale error, glue, wire and a heavier batch of parts

# (part, qty, mass each g, basis, price each USD or None, supplier, stock, note)
NANO = [
    ("Crazyflie 2.1+ airframe: board, frame, 4 coreless motors, props (no battery)", 1, 21.9, "DERIVED", None, "Bitcraze / RobotShop US", "RobotShop: in stock, 9 units", "29 g takeoff minus the 7.1 g battery, assuming the 29 g includes the battery (UNCONFIRMED); motor and frame split not published"),
    ("250 mAh 1S LiPo (stock battery)", 1, 7.1, "CLAIM", None, "Bitcraze", "no label", "in the kit"),
    ("Flow deck v2 (optical flow + ToF height)", 1, 1.6, "CLAIM", None, "Bitcraze", "no label", "in the STEM ranging bundle"),
    ("Multi-ranger deck (5 ToF: front, back, left, right, up)", 1, 2.3, "CLAIM", None, "Bitcraze", "no label", "in the STEM ranging bundle"),
    ("Crazyradio 2.0 (ground)", 1, 0.0, "CLAIM", None, "Bitcraze", "no label", "ground side, not flown"),
    ("STEM ranging bundle 2.1+ (the four lines above)", 1, 0.0, "CLAIM", 410.00, "Bitcraze store", "no label", "contents inferred from the list price, UNCONFIRMED"),
    ("AI deck 1.1 (GAP8 + camera), optional", 1, 4.4, "CLAIM", 240.00, "Bitcraze", "OUT OF STOCK (RobotShop US $308.02, 2 left)", "onboard tracking toolchain unavailable since the chip maker's 2025 liquidation"),
    ("Long pin headers (two decks on top)", 1, 0.5, "ESTIMATE", 2.00, "Bitcraze", "no label", ""),
    ("Spare 250 mAh batteries", 2, 0.0, "CLAIM", 6.50, "Bitcraze", "no label", "not flown at once"),
]

# Wisp Follow, vlog build: 3 inch ducted, 4S, everything on board
FOLLOW = [
    ("GEPRC CineLog30 V3 frame (ducts, canopy, lens mount)", 1, 78.0, "CLAIM", 71.99, "Pyrodrone", "SOLD OUT", "only sub-250-capable ducted frame found; 3.5 inch ducted frames are 114-214 g"),
    ("GEPRC SPEEDX2 1404 3850KV motor", 4, 10.5, "ESTIMATE", None, "GetFPV", "unclear", "10.5 g is the 3000/4600KV figure; 3850KV mass UNCONFIRMED"),
    ("HQProp DT76mm x3 V2 ducted prop", 4, 1.75, "ESTIMATE", None, "GetFPV / RDQ", "not checked", "mass UNCONFIRMED; weigh a set"),
    ("GNB 4S 550 mAh 90C LiPo, XT30", 1, 57.0, "CLAIM", 18.99, "Pyrodrone", "in stock", "+/-2 g; buy 3 packs"),
    ("DJI O4 Air Unit with lens mount (video link + 4K60 recorder)", 1, 9.2, "CLAIM", None, "DJI dealers", "US stock UNCONFIRMED", "DJI equipment is on the FCC Covered List; existing models stay legal to sell, availability uncertain"),
    ("MicoAir H743 v2 AIO 35A (flight controller + 4-in-1 ESC)", 1, 10.0, "CLAIM", 87.99, "Pyrodrone", "in stock", "ArduPilot target for this AIO UNCONFIRMED (MicoAir743v2 hwdef describes the 30x30 board)"),
    ("Flywoo GOKU GM10 Nano V3 GPS (M10) + QMC5883L compass", 1, 2.6, "CLAIM", 20.99, "Flywoo", "contradictory page", "RDQ $25.49"),
    ("MicoAir MTF-01 optical flow + 8 m ToF (downward)", 1, 4.5, "CLAIM", 32.99, "Pyrodrone", "in stock", "FLOW_TYPE=5, RNGFND1_TYPE=10"),
    ("Benewake TFS20-L lidar, forward (I2C, 15 m)", 1, 2.0, "CLAIM", 53.84, "RobotShop", "not shown", "RNGFND2_TYPE=46 is in ArduCopter 4.7.2 source"),
    ("RadioMaster RP1 V2 ExpressLRS receiver (MAVLink mode)", 1, 2.2, "CLAIM", 18.99, "RadioMaster", "listed available", "includes antenna"),
    ("Raspberry Pi Zero 2 W (companion, vision)", 1, 10.0, "CLAIM", 19.05, "Adafruit", "OUT OF STOCK (SparkFun too)", "alternative with an NPU: Radxa ZERO 3W, mass UNCONFIRMED"),
    ("Raspberry Pi Camera Module 3 Wide (tracking camera)", 1, 4.0, "CLAIM", 35.00, "Raspberry Pi resellers", "in stock (EU reseller)", "4 g per Raspberry Pi docs; ribbon cable extra"),
    ("Camera ribbon cable, short", 1, 1.0, "ESTIMATE", 3.00, "", "", ""),
    ("5 V regulator for the Pi, 9 V for the O4", 2, 1.0, "ESTIMATE", 4.00, "", "", "the AIO's own regulators may cover one; UNCONFIRMED"),
    ("Wire, connectors, solder, heat-shrink", 1, 5.0, "ESTIMATE", None, "", "", ""),
    ("Screws, battery strap, XT30 pigtail, antenna holder", 1, 5.0, "ESTIMATE", None, "", "", ""),
]
FOLLOW_SIDES = [
    ("Benewake TFS20-L lidar, left and right", 2, 2.0, "CLAIM", 53.84, "RobotShop", "not shown", "only if the I2C address can be changed and kept, UNCONFIRMED"),
]

# Wisp Follow Fast: 3.5 inch open frame, 6S, no Pi (vision stays on the vlog build), removable guards
FAST = [
    ("GEPRC Smart 35 frame (3.5 inch open)", 1, 47.9, "CLAIM", None, "FPVFaster AU (AU$89.99)", "SOLD OUT", "BetaFPV X-Knight 35 (43.2 g, $25.99) also sold out"),
    ("T-Motor Pacer P1604 2850KV motor", 4, 11.6, "CLAIM", 22.00, "rcdrone.top / GetFPV", "sold out / unclear", "618.8 g thrust each on 6S with GF3520-3 (maker table)"),
    ("Gemfan 3520-3 prop", 4, 2.25, "ESTIMATE", None, "", "not checked", "mass UNCONFIRMED"),
    ("GNB 6S 550 mAh 90C LiPo, XT30", 1, 85.0, "CLAIM", 14.99, "RaceDayQuads", "PRE-ORDER", "49.5 A continuous vs about 63 A at full throttle: sag"),
    ("DJI O4 Air Unit with lens mount", 1, 9.2, "CLAIM", None, "DJI dealers", "US stock UNCONFIRMED", "on a 9-10 V regulator"),
    ("Flight controller + 4-in-1 ESC for a 20x20 or 26.5 mm stack", 1, 12.0, "ESTIMATE", None, "", "", "the 25.5 mm AIO does not fit this frame's 26.5/20 mm mounts; e.g. NxtPX4v2 (6.5 g, $71.99) + a 20x20 ESC"),
    ("GM10 Nano V3 GPS + compass", 1, 2.6, "CLAIM", 20.99, "Flywoo", "contradictory page", ""),
    ("MTF-01 optical flow + ToF", 1, 4.5, "CLAIM", 32.99, "Pyrodrone", "in stock", ""),
    ("TFS20-L lidar, forward", 1, 2.0, "CLAIM", 53.84, "RobotShop", "not shown", ""),
    ("RP1 V2 ELRS receiver", 1, 2.2, "CLAIM", 18.99, "RadioMaster", "listed available", ""),
    ("9 V regulator for the O4", 1, 1.0, "ESTIMATE", 4.00, "", "", ""),
    ("Wire, connectors, screws, strap, pigtail", 1, 8.0, "ESTIMATE", None, "", "", ""),
]
FAST_GUARDS = [("Removable prop guards, 3.5 inch", 4, 6.3, "ESTIMATE", None, "", "", "GEPRC 3 inch guard is 6.3 g each (CLAIM); 3.5 inch mass UNCONFIRMED")]


def total(rows):
    return sum(q * m for _, q, m, *_ in rows)


def cost(rows):
    return sum(q * p for _, q, _, _, p, *_ in rows if p is not None)


def unpriced(rows):
    return [r[0] for r in rows if r[4] is None and r[2] > 0]


def table(rows):
    out = ["| Part | Qty | Mass each (g) | Mass (g) | Basis | Price each | Supplier | Stock 2026-10-26 | Note |", "|---|---:|---:|---:|---|---:|---|---|---|"]
    for name, q, m, basis, p, sup, stock, note in rows:
        out.append(f"| {name} | {q} | {m:g} | {q * m:.1f} | {basis} | {'$%.2f' % p if p is not None else '–'} | {sup} | {stock} | {note} |")
    return "\n".join(out)


def verdict(mass):
    margin = LIMIT_G - mass
    ok = margin >= TARGET_MARGIN_G
    sign = f"+{margin:.1f}" if margin >= 0 else f"−{-margin:.1f}"
    return (f"**{mass:.1f} g**, so 249.48 − {mass:.1f} = **{sign} g** to the registration line"
            f" ({'meets' if ok else 'MISSES'} the {TARGET_MARGIN_G:.0f} g margin target)")


def write_csv(name, rows):
    d = P0 / "parts"; d.mkdir(exist_ok=True)
    with open(d / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate"])
        w.writerow(["part", "qty", "mass_each_g", "mass_g", "basis", "price_each_usd", "supplier", "stock_2026_10_26", "note"])
        for name_, q, m, basis, p, sup, stock, note in rows:
            w.writerow([name_, q, m, round(q * m, 2), basis, "" if p is None else p, sup, stock, note])


def main():
    nano_flight = [r for r in NANO if "optional" not in r[0]]
    m_nano, m_nano_ai = total(nano_flight), total(NANO)
    m_follow, m_follow_sides = total(FOLLOW), total(FOLLOW + FOLLOW_SIDES)
    m_fast, m_fast_g = total(FAST), total(FAST + FAST_GUARDS)
    md = f"""> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate

# Wisp parts lists and weight budgets (Phase 0)

Generated by `review/P0/calc/budget.py`; every total below is computed from the rows. Nothing has been bought or
weighed. **Do not order anything before the Phase 0 gate is approved.**

**The registration line.** 14 CFR 48.15(b) exempts a recreational aircraft that "weighs 0.55 pounds or less on
takeoff, including everything that is on board or otherwise attached". 0.55 lb × 453.59237 g/lb = **{LIMIT_G:.2f} g**,
not 250 g. A build must weigh under 249.48 g, ready to fly, on a scale, every time anything changes. The budgets
keep a {TARGET_MARGIN_G:.0f} g margin (ESTIMATE) for scale error and parts that weigh more than listed.

**Basis.** CLAIM = maker or shop figure; DERIVED = computed from claims; ESTIMATE = assumption; UNCONFIRMED = not
verified. Sources with dates are in `research/`.

**Abbreviations.** AIO = all-in-one (flight controller and ESC on one board); ELRS = ExpressLRS radio link;
ESC = electronic speed controller; FCC = Federal Communications Commission; LiPo = lithium-polymer battery;
NPU = neural processing unit; ToF = time-of-flight distance sensor.

## Wisp Nano: Crazyflie 2.1+ with Flow and Multi-ranger decks

{table(NANO)}

- Takeoff mass without the AI deck: {verdict(m_nano).split(',')[0]}; with it: **{m_nano_ai:.1f} g**.
- Payload against Bitcraze's 15 g limit: {m_nano_ai - 29.0:.1f} g with the AI deck, {m_nano - 29.0:.1f} g without
  (takeoff mass minus the 29 g stock takeoff mass).
- Cost: **${cost([r for r in NANO if 'optional' not in r[0]]):.2f}** without the AI deck, **${cost(NANO):.2f}** with it
  (Bitcraze prices; shipping and tax extra).
- The Crazyflie 2.1 Brushless (34 g bare, about 43 g with the Flow and Multi-ranger decks; 40 g payload, 10 min;
  $640 STEM ranging bundle, about $666 with spare batteries) is the alternative: more margin, but over the 30-40 g
  target once fitted, and "re-stocking soon" at RobotShop US.

## Wisp Follow: 3 inch ducted, 4S, ArduPilot, companion computer on board

{table(FOLLOW + FOLLOW_SIDES)}

- Without the side lidars: {verdict(m_follow)}.
- With the side lidars: {verdict(m_follow_sides)}.
- Cost of the priced parts: **${cost(FOLLOW):.2f}** (+${cost(FOLLOW_SIDES):.2f} for the side lidars). Not priced:
  {", ".join(unpriced(FOLLOW))}.
- The margin rests on estimates for the motors, props, regulators and wiring. Weigh the frame, motors, props and
  battery first (they are 75 % of the mass) and recompute before buying the electronics.
- Lighter swaps if it comes out heavy: MicoAir MTF-02P flow sensor (1.8 g instead of 4.5 g, sold out today); drop
  the O4 and record from the companion camera (−9.2 g, much worse footage); or a 4S 450 mAh pack (mass not checked).

## Wisp Follow Fast: 3.5 inch open frame, 6S, removable guards, no companion computer

{table(FAST + FAST_GUARDS)}

- Without guards: {verdict(m_fast)}.
- With guards: {verdict(m_fast_g)}.
- With guards and a 6S 450 mAh pack instead (about 70 g, ESTIMATE: GNB does not list its mass): {verdict(m_fast_g - 85.0 + 70.0)}.
  Guards near people therefore mean the smaller pack, and shorter flights.
- Cost of the priced parts: **${cost(FAST):.2f}**. Not priced: {", ".join(unpriced(FAST))}.
- There is no room for the companion computer: vision follow stays on the vlog build. GPS follow (the phone as the
  target) works on both.

## Ground side and tools (both Follow builds)

| Item | Price | Note |
|---|---:|---|
| RadioMaster Ranger Nano ELRS transmitter with WiFi MAVLink backpack | $39.99 | Needs a handset with a Nano module bay (e.g. RadioMaster Pocket, price UNCONFIRMED) |
| Balance charger for 4S/6S LiPo, LiPo-safe bag | UNCONFIRMED | |
| Scale reading 0.01 g up to 300 g | UNCONFIRMED | The registration line is checked by weighing, not by this sheet |
| Phone with the Wisp app | owned | GPS target for follow-me |
"""
    (P0 / "parts.md").write_text(md)
    write_csv("wisp-nano.csv", NANO)
    write_csv("wisp-follow.csv", FOLLOW + FOLLOW_SIDES)
    write_csv("wisp-follow-fast.csv", FAST + FAST_GUARDS)
    print(f"Nano {m_nano:.1f} g ({m_nano_ai:.1f} with AI deck); Follow {m_follow:.1f} g ({m_follow_sides:.1f} with sides); "
          f"Fast {m_fast:.1f} g ({m_fast_g:.1f} with guards); limit {LIMIT_G:.2f} g")


if __name__ == "__main__":
    main()
