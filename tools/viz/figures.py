#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Static G1 figures (light + dark SVG) generated from the G1 data.

Inputs (single sources of truth):
  review/G1/calc/budgets.py      weight, thrust, power, flight-time model
  bom/drone-bom-g1.csv           prices
  review/G1/pin-allocation.csv   GPIO allocation
Outputs: docs/figures/<name>-light.svg and <name>-dark.svg

Run: python3 tools/viz/figures.py
Every figure is an illustration of DRAFT estimates - nothing here is measured.
"""
import math

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, Patch, Rectangle

from theme import REPO, THEMES, load_budgets, new_fig, read_csv_rows, save_svg, stamp, style_axes, title_block

B = load_budgets()


# --------------------------------------------------------------------------
def short_weight_label(name):
    keys = [
        ("Battery 1S", "Battery 1S 660 mAh"), ("Motors", "Motors 4× 8520"), ("Props", "Props 4× 55 mm"),
        ("PCB bare", "PCB (bare 1.0 mm FR-4)"), ("Electronic components", "Electronic parts + ESP32"),
        ("Camera", "Camera + FPC"), ("ELRS", "ELRS receiver"), ("Canopy", "Canopy shell"),
        ("Prop guards", "Prop guards (4 rings)"), ("Guard struts", "Guard struts"), ("Landing feet", "Landing feet"),
        ("Motor holders", "Motor holders"), ("Battery cradle", "Battery cradle"), ("Battery leads", "Leads, strap, fasteners"),
    ]
    for k, v in keys:
        if name.startswith(k):
            return v
    return name[:28]


def fig_weight(theme):
    t = THEMES[theme]
    items = B.weight_table()
    tot, lo_t, hi_t = B.weight_totals()
    rows = sorted(items, key=lambda kv: kv[1].value)
    fig = new_fig(t, 9.6, 7.0)
    title_block(fig, t, f"Takeoff weight: {tot:.1f} g nominal ({lo_t:.0f}–{hi_t:.0f} g range) against an 80 g limit",
                "Bars are the nominal value per item; thin lines span the low–high range. Colour shows where the number came from.")
    ax = fig.add_axes([0.27, 0.27, 0.66, 0.56])
    style_axes(ax, t, "x")
    y = np.arange(len(rows))
    for i, (name, v) in enumerate(rows):
        lo, hi = v.rng()
        c = t["series"][0] if v.kind == "SOURCED" else t["series"][1]
        ax.barh(i, v.value, height=0.56, color=c, linewidth=0)
        ax.plot([lo, hi], [i, i], color=t["ink2"], linewidth=1.2, solid_capstyle="round")
        ax.text(hi + 0.4, i, f"{v.value:.1f} g", va="center", fontsize=8.5, color=t["ink2"])
    ax.set_yticks(y, [short_weight_label(n) for n, _ in rows], fontsize=9)
    ax.set_xlim(0, 25)
    ax.set_xlabel("grams")
    ax.legend(handles=[Patch(color=t["series"][0], label="datasheet / vendor value"),
                       Patch(color=t["series"][1], label="engineering estimate"),
                       Line2D([], [], color=t["ink2"], lw=1.2, label="low–high range")],
              loc="lower right", frameon=False, fontsize=8.5, labelcolor=t["ink2"])
    # total strip
    ax2 = fig.add_axes([0.27, 0.11, 0.66, 0.07])
    style_axes(ax2, t, "x")
    ax2.barh(0, tot, height=0.5, color=t["series"][0], linewidth=0)
    ax2.plot([lo_t, hi_t], [0, 0], color=t["ink2"], linewidth=1.4)
    ax2.axvline(80, color=t["warn"], linewidth=1.5)
    ax2.text(80.8, 0.32, "80 g limit", color=t["ink2"], fontsize=8.5, va="center")
    ax2.text(tot / 2, 0, f"{tot:.1f} g", color="#ffffff", fontsize=9, va="center", ha="center", fontweight="bold")
    ax2.set_xlim(0, 100)
    ax2.set_yticks([0], ["Total takeoff weight"], fontsize=9)
    ax2.set_xlabel("grams")
    stamp(fig, t, "source: review/G1/budgets.md §1")
    return save_svg(fig, "weight-budget", theme)


def fig_thrust(theme):
    t = THEMES[theme]
    tot, lo_t, hi_t = B.weight_totals()
    W = np.linspace(50, 100, 200)
    fig = new_fig(t, 9.6, 5.6)
    title_block(fig, t, "Thrust-to-weight falls below 2 across most of the estimated weight range",
                "T/W = 4 × thrust per motor ÷ takeoff weight. No 55 mm-prop thrust data was found; 33–36 gf is secondhand data for 60 mm props.")
    ax = fig.add_axes([0.08, 0.15, 0.66, 0.62])
    style_axes(ax, t, "y")
    ax.axvspan(lo_t, hi_t, color=t["grid"], alpha=0.55, linewidth=0)
    ax.text(lo_t + 0.6, 3.14, "estimated weight range", ha="left", va="top", fontsize=8.5, color=t["ink2"])
    ax.axvline(tot, color=t["ink2"], linewidth=1)
    ax.text(tot + 0.6, 1.08, f"nominal {tot:.1f} g", fontsize=8.5, color=t["ink2"])
    ax.axvline(80, color=t["warn"], linewidth=1.3)
    ax.text(80.6, 1.08, "80 g limit", fontsize=8.5, color=t["ink2"])
    ax.axhline(2.0, color=t["muted"], linewidth=1, linestyle=(0, (4, 3)))
    ax.text(50.5, 2.04, "T/W = 2 rule of thumb (assumption)", fontsize=8, color=t["ink2"], va="bottom")
    handles = []
    for i, (tm, tag) in enumerate(B.THRUST_SCENARIOS):
        c = t["series"][i]
        ax.plot(W, 4 * tm / W, color=c, linewidth=2, solid_capstyle="round")
        tw = 4 * tm / tot
        ax.plot([tot], [tw], "o", ms=7, color=c, mec=t["surface"], mew=2)
        ax.text(tot - 1.2, tw, f"{tw:.2f}", fontsize=8.5, color=t["ink"], ha="right", va="center",
                bbox=dict(facecolor=t["surface"], edgecolor="none", pad=1.2))
        label = f"{tm} gf/motor – {'assumed for 55 mm' if tag == 'ASSUMPTION' else 'S19, 60 mm props'}"
        ax.text(100.8, 4 * tm / 100, label, fontsize=8.5, color=t["ink2"], va="center")
        handles.append(Line2D([], [], color=c, lw=2, label=label))
    ax.set_xlim(50, 100)
    ax.set_ylim(1.0, 3.2)
    ax.set_xlabel("takeoff weight (g)")
    ax.set_ylabel("thrust-to-weight ratio")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.075, 0.86), frameon=False, fontsize=8.5,
               labelcolor=t["ink2"], ncol=3)
    stamp(fig, t, "source: review/G1/budgets.md §2")
    return save_svg(fig, "thrust-to-weight", theme)


def fig_flight(theme):
    t = THEMES[theme]
    tot, lo_t, hi_t = B.weight_totals()
    W = np.linspace(50, 100, 200)
    fig = new_fig(t, 9.6, 5.4)
    elec = B.electronics_battery_current_a()
    title_block(fig, t, f"Estimated hover time: {B.flight_time_min(tot, 4):.1f}–{B.flight_time_min(tot, 5):.1f} min at the nominal weight",
                f"660 mAh × {B.HV_DERATE.value:.0%} HV derate × {B.USABLE_FRAC.value:.0%} usable ÷ (motors W/η/3.7 V + {elec:.2f} A electronics). η = 4–5 g/W from a generic 8520 test.")
    ax = fig.add_axes([0.08, 0.15, 0.68, 0.62])
    style_axes(ax, t, "y")
    ax.axvspan(lo_t, hi_t, color=t["grid"], alpha=0.55, linewidth=0)
    ax.axvline(80, color=t["warn"], linewidth=1.3)
    ax.text(80.6, 0.4, "80 g limit", fontsize=8.5, color=t["ink2"])
    ax.text(lo_t + 0.6, 8.85, "estimated weight range", ha="left", va="top", fontsize=8.5, color=t["ink2"])
    handles = []
    for i, eta in enumerate(B.ETA_GW):
        c = t["series"][i]
        ft = [B.flight_time_min(w, eta) for w in W]
        ax.plot(W, ft, color=c, linewidth=2)
        v = B.flight_time_min(tot, eta)
        ax.plot([tot], [v], "o", ms=7, color=c, mec=t["surface"], mew=2)
        ax.text(tot - 1.2, v, f"{v:.1f} min", fontsize=8.5, color=t["ink"], ha="right", va="center",
                bbox=dict(facecolor=t["surface"], edgecolor="none", pad=1.2))
        lab = f"η = {eta:.0f} g/W"
        ax.text(100.8, B.flight_time_min(100, eta), lab, fontsize=8.5, color=t["ink2"], va="center")
        handles.append(Line2D([], [], color=c, lw=2, label=lab))
    ax.set_xlim(50, 100)
    ax.set_ylim(0, 9)
    ax.set_xlabel("takeoff weight (g)")
    ax.set_ylabel("hover time (min)")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.075, 0.86), frameon=False, fontsize=8.5,
               labelcolor=t["ink2"], ncol=2)
    stamp(fig, t, "source: review/G1/budgets.md §3c")
    return save_svg(fig, "flight-time", theme)


def short_load(name):
    for k, v in [("ESP32", "ESP32-S3 module"), ("BMI270", "BMI270 IMU"), ("BMP390", "BMP390 baro"),
                 ("QMC5883P", "QMC5883P mag"), ("4x VL53L1X", "4× VL53L1X ToF"), ("VL53L5CX", "VL53L5CX 8×8 ToF"),
                 ("PMW3901", "PMW3901 flow"), ("INA226", "INA226"), ("OV2640", "OV2640 camera"), ("Buzzer", "Buzzer"),
                 ("4x WS2812", "4× WS2812B LEDs"), ("ELRS", "ELRS receiver")]:
        if name.startswith(k):
            return v
    return name[:20]


def fig_power(theme):
    t = THEMES[theme]
    fig = new_fig(t, 9.6, 6.6)
    pk33, av33 = B.rail_totals(B.RAIL33)
    pk5, av5 = B.rail_totals(B.RAIL5)
    title_block(fig, t, f"Electronics load: 3.3 V rail {av33:.0f} mA average / {pk33:.0f} mA peak; 5 V rail {av5:.0f} / {pk5:.0f} mA",
                "Each row runs from average to peak (one dot = constant load). ESP32 average, ELRS and LED figures are placeholders until G6.")
    panels = [("3.3 V rail (TPS63802, rated 2 A)", B.RAIL33, [0.2, 0.33, 0.73, 0.47]),
              ("5 V rail (TPS61023)", B.RAIL5, [0.2, 0.11, 0.73, 0.12])]
    for title, rail, rect in panels:
        ax = fig.add_axes(rect)
        style_axes(ax, t, "x")
        rows = sorted(rail, key=lambda r: r[1])
        for i, (n, p, a, k, s) in enumerate(rows):
            ax.plot([a, p], [i, i], color=t["axis"], linewidth=2, solid_capstyle="round")
            ax.plot([a], [i], "o", ms=8, color=t["series"][0], mec=t["surface"], mew=2)
            ax.plot([p], [i], "o", ms=8, color=t["series"][1], mec=t["surface"], mew=2)
            ax.text(p + 8, i, f"{p:.0f}" if p >= 10 else f"{p:.1f}", va="center", fontsize=8, color=t["ink2"])
        ax.set_yticks(range(len(rows)), [short_load(r[0]) for r in rows], fontsize=9)
        ax.set_xlim(-5, 420)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_title(title, loc="left", fontsize=10, color=t["ink"], pad=4)
    ax.set_xlabel("current (mA)")
    fig.legend(handles=[Line2D([], [], marker="o", ls="", ms=8, color=t["series"][0], mec=t["surface"], label="average"),
                        Line2D([], [], marker="o", ls="", ms=8, color=t["series"][1], mec=t["surface"], label="peak (value shown)")],
               loc="upper right", bbox_to_anchor=(0.95, 0.88), frameon=False, fontsize=8.5, labelcolor=t["ink2"], ncol=2)
    stamp(fig, t, "source: review/G1/budgets.md §3a–3b")
    return save_svg(fig, "power-budget", theme)


def fig_cost(theme):
    t = THEMES[theme]
    rows = []
    for r in read_csv_rows(REPO / "bom" / "drone-bom-g1.csv"):
        if r["status"] in ("SELECTED", "CONDITIONAL") and r["unit_usd"]:
            name = f"{r['ref']}  {r['mpn']}" + (f" ×{r['qty']}" if int(r["qty"]) > 1 else "")
            rows.append((name, float(r["unit_usd"]) * int(r["qty"]), r["ref"]))
    rows.sort(key=lambda x: x[1])
    total = sum(x[1] for x in rows)
    small = [x for x in rows if x[1] < 1.0]
    big = [x for x in rows if x[1] >= 1.0]
    rows = [(f"{len(small)} lines under $1 each", sum(x[1] for x in small), "")] + big
    fig = new_fig(t, 9.6, 6.6)
    title_block(fig, t, f"Priced parts already total \\${total:.2f} per drone against a ~\\$75 target",
                "LCSC prices seen 2026-10-04 at the break covering 5 drones. Not yet priced: PCB, assembly, passives, battery, camera, props, barometer (out of stock).")
    ax = fig.add_axes([0.3, 0.12, 0.62, 0.7])
    style_axes(ax, t, "x")
    for i, (n, v, ref) in enumerate(rows):
        ax.barh(i, v, height=0.58, color=t["series"][0] if ref else t["neutral"], linewidth=0)
        ax.text(v + 0.25, i, f"\\${v:.2f}", va="center", fontsize=8.5, color=t["ink2"])
    ax.set_yticks(range(len(rows)), [n for n, _, _ in rows], fontsize=8.5)
    ax.set_xlabel("US\\$ per drone")
    ax.set_xlim(0, max(v for _, v, _ in rows) * 1.18)
    stamp(fig, t, "source: bom/drone-bom-g1.csv")
    return save_svg(fig, "cost-breakdown", theme)


def fig_props(theme):
    t = THEMES[theme]
    D = B.MOTOR_TO_MOTOR_MM.value
    s = D / math.sqrt(2)
    fig = new_fig(t, 9.6, 5.6)
    title_block(fig, t, f"Why 55 mm props: at {D:.0f} mm, 65 mm props leave no room for guards",
                "Top view to scale. Adjacent motor spacing s = D/√2; tip gap = s − prop diameter. Guard ring = 3 mm clearance + 1 mm wall (estimate).")
    for j, prop in enumerate((55, 65)):
        ax = fig.add_axes([0.04 + j * 0.48, 0.1, 0.44, 0.7])
        ax.set_facecolor(t["surface"])
        ax.set_aspect("equal")
        ax.axis("off")
        lim = s / 2 + prop / 2 + 9
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.add_patch(Rectangle((-20, -20), 40, 40, facecolor=t["grid"], edgecolor=t["axis"], lw=1))
        ax.plot([-s / 2, s / 2], [-s / 2, s / 2], color=t["axis"], lw=6, solid_capstyle="round", zorder=1)
        ax.plot([-s / 2, s / 2], [s / 2, -s / 2], color=t["axis"], lw=6, solid_capstyle="round", zorder=1)
        guard_r = prop / 2 + 3 + 1
        gap = s - prop
        guard_gap = s - 2 * guard_r
        for (x, y) in [(-s / 2, s / 2), (s / 2, s / 2), (s / 2, -s / 2), (-s / 2, -s / 2)]:
            ax.add_patch(Circle((x, y), prop / 2, facecolor=t["series"][0], alpha=0.16, edgecolor=t["series"][0], lw=1.5))
            ax.add_patch(Circle((x, y), guard_r, facecolor="none", edgecolor=t["warn"] if guard_gap < 0 else t["ink2"], lw=1.2))
            ax.add_patch(Circle((x, y), 4.25, facecolor=t["ink2"], edgecolor="none"))
        # gap annotation between top two props
        x0, x1 = -s / 2 + prop / 2, s / 2 - prop / 2
        ax.annotate("", xy=(x1, s / 2), xytext=(x0, s / 2),
                    arrowprops=dict(arrowstyle="<->", color=t["ink"], lw=1, shrinkA=0, shrinkB=0))
        ax.text(0, s / 2 + 4, f"tip gap {gap:.1f} mm", ha="center", fontsize=9, color=t["ink"])
        verdict = (f"guards clear each other by {guard_gap:.1f} mm" if guard_gap >= 0
                   else f"guards overlap by {-guard_gap:.1f} mm")
        ax.text(0, -lim + 2, f"{prop} mm props · {verdict}", ha="center", fontsize=10,
                color=t["ink"], fontweight="bold")
        ax.text(0, 0, "40 mm\nbody", ha="center", va="center", fontsize=8, color=t["ink2"])
    stamp(fig, t, "source: review/G1/budgets.md §4e, D-019")
    return save_svg(fig, "prop-clearance", theme)


# --------------------------------------------------------------------------
PIN_GROUPS = [  # (label, predicate on net) - slot order fixed
    ("Camera DVP", lambda n: n.startswith("CAM_")),
    ("SPI sensors", lambda n: n.startswith(("SPI_", "IMU_", "FLOW_"))),
    ("I²C bus", lambda n: n.startswith("I2C_")),
    ("Motor gates", lambda n: n.startswith("MOT")),
    ("USB / UART / ELRS", lambda n: n.startswith(("USB_", "U0", "CRSF_"))),
    ("Control & status", lambda n: True),
]
STRAPPING = {0, 3, 45, 46}


def pin_table():
    rows = {int(r["module_pin"]): r for r in read_csv_rows(REPO / "review" / "G1" / "pin-allocation.csv")}
    pins = {}
    for p in range(1, 41):
        if p in (1, 40):
            pins[p] = ("GND", "GND", None, False)
        elif p == 2:
            pins[p] = ("3V3", "3V3", None, False)
        elif p == 3:
            pins[p] = ("EN", "EN (reset)", None, False)
        else:
            r = rows[p]
            g = int(r["gpio"])
            net = r["net"]
            gi = next(i for i, (_, f) in enumerate(PIN_GROUPS) if f(net))
            pins[p] = (f"IO{g}", net, gi, g in STRAPPING)
    return pins


def fig_pinout(theme):
    t = THEMES[theme]
    pins = pin_table()
    fig = new_fig(t, 10.5, 9.0)
    title_block(fig, t, "ESP32-S3-WROOM-1-N8R2: all 36 GPIOs are assigned",
                "Schematic top view in module pin order (1–14 left, 15–26 bottom, 27–40 right), not to scale. ◆ marks a strapping pin.\nCheck every pin against the datasheet of the modules you buy.")
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.8])
    ax.set_facecolor(t["surface"])
    ax.axis("off")
    W, H = 18.0, 25.5
    ax.set_xlim(-17, W + 17)
    ax.set_ylim(-6.5, H + 1.5)
    ax.set_aspect("equal")
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle="round,pad=0,rounding_size=0.6",
                                facecolor=t["page"], edgecolor=t["axis"], lw=1.5))
    ax.add_patch(Rectangle((0.4, H - 6.0), W - 0.8, 5.6, facecolor="none", edgecolor=t["muted"], lw=1, hatch="///"))
    ax.text(W / 2, H - 3.2, "PCB antenna\nkeep at board edge", ha="center", va="center", fontsize=8.5, color=t["ink2"],
            bbox=dict(facecolor=t["page"], edgecolor="none", pad=1.5))
    ax.add_patch(Rectangle((W / 2 - 2.5, 7.5), 5, 5, facecolor=t["neutral"], edgecolor="none", alpha=0.6))
    ax.text(W / 2, 10, "41 EPAD\nGND", ha="center", va="center", fontsize=7.5, color=t["ink"])
    pitch = 1.27

    def colour(gi):
        return t["neutral"] if gi is None else t["series"][gi]

    def label(p):
        name, net, gi, strap = pins[p]
        return (f"{p:>2}  {name} · {net}" + ("  ◆" if strap else "")), colour(gi)

    left_y0 = H - 7.6
    for k, p in enumerate(range(1, 15)):           # left side, top -> bottom
        y = left_y0 - k * pitch
        text, c = label(p)
        ax.add_patch(Rectangle((-1.1, y - 0.42), 1.5, 0.84, facecolor=c, edgecolor="none"))
        ax.text(-1.5, y, text, ha="right", va="center", fontsize=8.2, color=t["ink"], family="DejaVu Sans Mono")
    for k, p in enumerate(range(15, 27)):          # bottom, left -> right
        x = 2.0 + k * pitch
        _, net, gi, strap = pins[p]
        c = colour(gi)
        ax.add_patch(Rectangle((x - 0.42, -1.1), 0.84, 1.5, facecolor=c, edgecolor="none"))
        ax.text(x, -1.5, f"{p} {pins[p][0]} · {net}" + (" ◆" if strap else ""), ha="right", va="top",
                rotation=60, rotation_mode="anchor", fontsize=7.6, color=t["ink"], family="DejaVu Sans Mono")
    for k, p in enumerate(range(27, 41)):          # right side, bottom -> top
        y = left_y0 - 13 * pitch + k * pitch
        text, c = label(p)
        ax.add_patch(Rectangle((W - 0.4, y - 0.42), 1.5, 0.84, facecolor=c, edgecolor="none"))
        ax.text(W + 1.5, y, text, ha="left", va="center", fontsize=8.2, color=t["ink"], family="DejaVu Sans Mono")
    handles = [Patch(color=t["series"][i], label=g) for i, (g, _) in enumerate(PIN_GROUPS)]
    handles.append(Patch(color=t["neutral"], label="Power / reset"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), frameon=False, fontsize=8.5,
              labelcolor=t["ink2"], ncol=1)
    stamp(fig, t, "source: review/G1/pin-allocation.csv")
    return save_svg(fig, "esp32-pinout", theme)


ALL = [fig_weight, fig_thrust, fig_flight, fig_power, fig_cost, fig_props, fig_pinout]

if __name__ == "__main__":
    for f in ALL:
        for th in ("light", "dark"):
            out = f(th)
            print("wrote", out.relative_to(REPO))
