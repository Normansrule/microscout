#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Static G1 figures (light + dark SVG) generated from the G1 data.

Inputs (single sources of truth):
  review/G1/calc/budgets.py      weight, thrust, power, flight-time model
  bom/drone-bom-g2.csv           prices
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
        ("Battery 2S", "Battery 2S 550 mAh"), ("Battery 1S", "Battery 1S 660 mAh"), ("Motors", "Motors 4× EX1103"),
        ("Props", "Props 4× 2-inch"), ("Ducted frame", "Ducted frame (PA11)"), ("Canopy", "Canopy + strap (TPU)"),
        ("Flight-controller PCB", "FC PCB (bare)"), ("FC components", "FC parts + ESP32"), ("ESC PCB", "ESC PCB (bare)"),
        ("ESC components", "ESC parts"), ("Camera", "Camera + FPC"), ("Side/rear ToF", "Side/rear ToF boards"),
        ("ELRS", "ELRS receiver"), ("XT30", "XT30 lead + wires"), ("Soft-mount", "Grommets + screws"),
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
    title_block(fig, t, f"Takeoff weight: {tot:.1f} g nominal ({lo_t:.0f}–{hi_t:.0f} g range) against a ~85 g limit (raised from 80 g, D-044)",
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
    ax.set_xlim(0, max(v.rng()[1] for _, v in rows) * 1.18)
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
    ax2.axvline(85, color=t["warn"], linewidth=1.5)
    ax2.text(85.8, 0.32, "~85 g limit", color=t["ink2"], fontsize=8.5, va="center")
    ax2.text(tot / 2, 0, f"{tot:.1f} g", color="#ffffff", fontsize=9, va="center", ha="center", fontweight="bold")
    ax2.set_xlim(0, 110)
    ax2.set_yticks([0], ["Total takeoff weight"], fontsize=9)
    ax2.set_xlabel("grams")
    stamp(fig, t, "source: review/G1/budgets.md §1")
    return save_svg(fig, "weight-budget", theme)


def fig_thrust(theme):
    t = THEMES[theme]
    tot, lo_t, hi_t = B.weight_totals()
    W = np.linspace(60, 110, 200)
    tws = [4 * tm / tot for tm, _ in B.THRUST_SCENARIOS]
    fig = new_fig(t, 9.6, 5.6)
    title_block(fig, t, f"Thrust-to-weight {min(tws):.1f}–{max(tws):.1f} at the nominal {tot:.0f} g – enough for flips",
                "T/W = 4 × thrust per motor ÷ weight. 122 g = EX1103 vendor table (open prop, 7.4 V); 85 and 100 g are assumed derates.")
    ax = fig.add_axes([0.08, 0.15, 0.62, 0.62])
    style_axes(ax, t, "y")
    ax.axvspan(lo_t, hi_t, color=t["grid"], alpha=0.55, linewidth=0)
    ax.text(lo_t + 0.6, 7.85, "estimated weight range", ha="left", va="top", fontsize=8.5, color=t["ink2"])
    ax.axvline(tot, color=t["ink2"], linewidth=1)
    ax.text(tot + 0.6, 2.1, f"nominal {tot:.1f} g", fontsize=8.5, color=t["ink2"])
    ax.axvline(85, color=t["warn"], linewidth=1.3)
    ax.text(85.6, 2.4, "~85 g limit", fontsize=8.5, color=t["ink2"])
    ax.axhline(4.0, color=t["muted"], linewidth=1, linestyle=(0, (4, 3)))
    ax.text(60.5, 4.05, "T/W = 4 agility target (R-20)", fontsize=8, color=t["ink2"], va="bottom")
    handles = []
    for i, (tm, tag) in enumerate(B.THRUST_SCENARIOS):
        c = t["series"][i]
        ax.plot(W, 4 * tm / W, color=c, linewidth=2, solid_capstyle="round")
        tw = 4 * tm / tot
        ax.plot([tot], [tw], "o", ms=7, color=c, mec=t["surface"], mew=2)
        ax.text(tot - 1.2, tw, f"{tw:.2f}", fontsize=8.5, color=t["ink"], ha="right", va="center",
                bbox=dict(facecolor=t["surface"], edgecolor="none", pad=1.2))
        label = f"{tm} g/motor – " + ("vendor table" if tag.startswith("SOURCED") else ("−30 % ducts + sag" if tm == 85 else "sag to ~7 V"))
        ax.text(110.8, 4 * tm / 110, label, fontsize=8.5, color=t["ink2"], va="center")
        handles.append(Line2D([], [], color=c, lw=2, label=label))
    ax.set_xlim(60, 110)
    ax.set_ylim(2.0, 8.0)
    ax.set_xlabel("takeoff weight (g)")
    ax.set_ylabel("thrust-to-weight ratio")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.075, 0.86), frameon=False, fontsize=8.5,
               labelcolor=t["ink2"], ncol=3)
    stamp(fig, t, "source: review/G1/budgets.md §2")
    return save_svg(fig, "thrust-to-weight", theme)

def fig_flight(theme):
    t = THEMES[theme]
    tot, lo_t, hi_t = B.weight_totals()
    W = np.linspace(60, 110, 200)
    fig = new_fig(t, 9.6, 5.4)
    elec = B.electronics_battery_current_a()
    title_block(fig, t, f"Estimated hover time: {B.flight_time_min(tot, min(B.ETA_GW)):.1f}–{B.flight_time_min(tot, max(B.ETA_GW)):.1f} min at the nominal weight",
                f"{B.CAP_MAH.value:.0f} mAh × {B.HV_DERATE.value:.0%} × {B.USABLE_FRAC.value:.0%} usable ÷ (W/η/{B.V_NOM.value} V + {elec:.2f} A electronics). η = 2.5–3.5 g/W (estimate). Hover only – acro drains it 2–3× faster.")
    ax = fig.add_axes([0.08, 0.15, 0.68, 0.62])
    style_axes(ax, t, "y")
    ax.axvspan(lo_t, hi_t, color=t["grid"], alpha=0.55, linewidth=0)
    ax.axvline(80, color=t["warn"], linewidth=1.3)
    ax.text(80.6, 0.4, "80 g target", fontsize=8.5, color=t["ink2"])
    ax.text(lo_t + 0.6, 9.85, "estimated weight range", ha="left", va="top", fontsize=8.5, color=t["ink2"])
    handles = []
    for i, eta in enumerate(B.ETA_GW):
        c = t["series"][i]
        ft = [B.flight_time_min(w, eta) for w in W]
        ax.plot(W, ft, color=c, linewidth=2)
        v = B.flight_time_min(tot, eta)
        ax.plot([tot], [v], "o", ms=7, color=c, mec=t["surface"], mew=2)
        ax.text(tot - 1.2, v, f"{v:.1f} min", fontsize=8.5, color=t["ink"], ha="right", va="center",
                bbox=dict(facecolor=t["surface"], edgecolor="none", pad=1.2))
        lab = f"η = {eta} g/W"
        ax.text(110.8, B.flight_time_min(110, eta), lab, fontsize=8.5, color=t["ink2"], va="center")
        handles.append(Line2D([], [], color=c, lw=2, label=lab))
    ax.set_xlim(60, 110)
    ax.set_ylim(0, 10)
    ax.set_xlabel("takeoff weight (g)")
    ax.set_ylabel("hover time (min)")
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.075, 0.86), frameon=False, fontsize=8.5,
               labelcolor=t["ink2"], ncol=2)
    stamp(fig, t, "source: review/G1/budgets.md §3c")
    return save_svg(fig, "flight-time", theme)


def short_load(name):
    for k, v in [("ESP32", "ESP32-S3 module"), ("BMI270", "BMI270 IMU"), ("BMP390", "BMP390 baro"),
                 ("QMC5883P", "QMC5883P mag"), ("4x VL53L1X", "4× VL53L1X ToF"), ("VL53L5CX", "VL53L5CX 8×8 ToF"),
                 ("PMW3901", "PMW3901 flow"), ("INA226", "INA226"), ("OV2640", "OV2640 camera"), ("Buzzer", "Buzzer"), ("4x AT32F421", "4× ESC MCUs"), ("ICM-42688-P", "ICM-42688-P IMU"),
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
    panels = [("3.3 V rail (TPS62162 buck, rated 1 A)", B.RAIL33, [0.2, 0.33, 0.73, 0.47]),
              ("5 V rail (TPS62133 buck)", B.RAIL5, [0.2, 0.11, 0.73, 0.12])]
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
    for r in read_csv_rows(REPO / "bom" / "drone-bom-g2.csv"):
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
    stamp(fig, t, "source: bom/drone-bom-g2.csv")
    return save_svg(fig, "cost-breakdown", theme)


def fig_ducts(theme):
    t = THEMES[theme]
    D = B.MOTOR_TO_MOTOR_MM.value
    a = D / math.sqrt(2) / 2
    r_in = B.PROP_MM.value / 2 + B.DUCT_CLEAR_MM
    r_out = r_in + B.DUCT_WALL_MM
    fig = new_fig(t, 9.6, 6.4)
    title_block(fig, t, f"Ducts at {D:.0f} mm: 2-inch props, {B.DUCT_CLEAR_MM:.0f} mm tip clearance, boards inside the frame",
                f"Top view to scale; {D:.0f} mm is the diagonal motor-to-motor distance. The FC board above the ducts is notched around each inlet (D-030).")
    ax = fig.add_axes([0.02, 0.07, 0.62, 0.78])
    ax.set_facecolor(t["surface"])
    ax.set_aspect("equal")
    ax.axis("off")
    lim = a + r_out + 6
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    # FC board (notched) drawn as a square with inlet circles masked
    ax.add_patch(Rectangle((-20, -20), 40, 40, facecolor=t["series"][2], alpha=0.30, edgecolor=t["series"][2], lw=1.2, zorder=1))
    ax.add_patch(Rectangle((-14.5, -14.5), 29, 29, facecolor="none", edgecolor=t["series"][4], lw=1.4, ls=(0, (3, 2)), zorder=3))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * a, sy * a
            ax.add_patch(Circle((x, y), r_in + 2.6, facecolor=t["surface"], edgecolor="none", zorder=2))
            ax.add_patch(Circle((x, y), r_out, facecolor="none", edgecolor=t["ink"], lw=2.2, zorder=4))
            ax.add_patch(Circle((x, y), B.PROP_MM.value / 2, facecolor=t["series"][0], alpha=0.14, edgecolor=t["series"][0], lw=1, zorder=4))
            ax.add_patch(Circle((x, y), 7.0, facecolor=t["ink2"], edgecolor="none", zorder=5))
    gap = 2 * a - 2 * r_out
    ax.annotate("", xy=(a - r_out, a), xytext=(-a + r_out, a), arrowprops=dict(arrowstyle="<->", color=t["ink"], lw=1, shrinkA=0, shrinkB=0), zorder=6)
    ax.text(0, a + 3, f"{gap:.1f} mm between ducts", ha="center", fontsize=8.5, color=t["ink"], zorder=6)
    ax.text(lim - 2, -lim + 2, f"overall ≈ {2 * (a + r_out + 2):.0f} mm", ha="right", fontsize=8.5, color=t["ink2"])
    tx = 0.66
    for i, (lab, sub, c, style) in enumerate([
        ("Duct wall (PA11)", f"inner Ø{2*r_in:.0f} mm, wall {B.DUCT_WALL_MM} mm, height {B.DUCT_H_MM:.0f} mm", t["ink"], "line"),
        ("2-inch prop disc", f"Ø{B.PROP_MM.value:.0f} mm, tip clearance {B.DUCT_CLEAR_MM:.0f} mm", t["series"][0], "fill"),
        ("Flight-controller board", "40 mm, corners notched around the inlets", t["series"][2], "fill"),
        ("4-in-1 ESC board", "29 mm, between the ducts below", t["series"][4], "dash"),
    ]):
        y = 0.74 - i * 0.12
        if style == "line":
            fig.lines.append(Line2D([tx, tx + 0.025], [y + 0.01, y + 0.01], transform=fig.transFigure, color=c, lw=2.2))
        elif style == "dash":
            fig.lines.append(Line2D([tx, tx + 0.025], [y + 0.01, y + 0.01], transform=fig.transFigure, color=c, lw=1.6, ls=(0, (3, 2))))
        else:
            fig.patches.append(Rectangle((tx, y), 0.025, 0.022, transform=fig.transFigure, facecolor=c, alpha=0.4, edgecolor=c))
        fig.text(tx + 0.035, y + 0.022, lab, fontsize=9, color=t["ink"], va="top")
        fig.text(tx + 0.035, y - 0.012, sub, fontsize=8, color=t["ink2"], va="top")
    stamp(fig, t, "source: budgets.py §4e, mechanical/concept")
    return save_svg(fig, "duct-layout", theme)


def _sim_flip():
    import sys as _s
    _s.path.insert(0, str(REPO / "software" / "microscout_sdk" / "src"))
    import microscout
    d = microscout.connect("sim")
    d.takeoff(1.5)
    d.hover(0.3)
    t0 = d.telemetry.t
    d.flip("back")
    d.hover(0.5)
    return [s for s in d.log if s.t >= t0 - 0.2], t0


def fig_flip(theme):
    t = THEMES[theme]
    log, t0 = _sim_flip()
    tt = np.array([s.t - t0 for s in log])
    rate = np.array([s.rates_dps[1] for s in log])
    ang = np.concatenate([[0.0], np.cumsum(rate[1:] * np.diff(tt))])
    h = np.array([s.height for s in log])
    fig = new_fig(t, 9.6, 6.2)
    dur = tt[[i for i, s in enumerate(log) if s.status == "flip complete"][0]] if any(s.status == "flip complete" for s in log) else tt[-1]
    title_block(fig, t, f"Simulated back flip: 360° in about {dur:.1f} s without losing height",
                "MicroScout SDK simulator with the rev B estimated parameters (30 ms motor lag, 85 g/motor). Not flight data – real tuning happens at G7.")
    axs = []
    for k, (lab, y, c) in enumerate([("rotation (deg)", ang, t["series"][0]), ("pitch rate (deg/s)", rate, t["series"][1]), ("height (m)", h, t["series"][2])]):
        ax = fig.add_axes([0.1, 0.62 - k * 0.235, 0.84, 0.19])
        style_axes(ax, t, "y")
        ax.plot(tt, y, color=c, lw=2)
        ax.set_ylabel(lab, fontsize=8.5)
        ax.set_xlim(tt[0], tt[-1])
        if k < 2:
            ax.tick_params(labelbottom=False)
        axs.append(ax)
    axs[0].axhline(360, color=t["muted"], lw=1, ls=(0, (4, 3)))
    axs[0].text(tt[0] + 0.01, 368, "360°", fontsize=8, color=t["ink2"])
    axs[1].axhline(1000, color=t["muted"], lw=1, ls=(0, (4, 3)))
    axs[1].text(tt[0] + 0.01, 1040, "1000 °/s setpoint", fontsize=8, color=t["ink2"])
    axs[2].set_xlabel("time from the flip command (s)")
    axs[2].set_ylim(0, max(h) * 1.15)
    stamp(fig, t, "source: software/microscout_sdk (simulation)")
    return save_svg(fig, "sim-flip", theme)

# --------------------------------------------------------------------------
PIN_GROUPS = [  # (label, predicate on net) - slot order fixed
    ("Camera DVP", lambda n: n.startswith("CAM_")),
    ("SPI sensors", lambda n: n.startswith(("SPI_", "IMU_", "FLOW_"))),
    ("I²C bus", lambda n: n.startswith("I2C_")),
    ("ESC DShot", lambda n: n.startswith("MOT")),
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
            gi = None if net == "SPARE" else next(i for i, (_, f) in enumerate(PIN_GROUPS) if f(net))
            pins[p] = (f"IO{g}", net, gi, g in STRAPPING)
    return pins


def fig_pinout(theme):
    t = THEMES[theme]
    pins = pin_table()
    fig = new_fig(t, 10.5, 9.0)
    title_block(fig, t, "ESP32-S3-WROOM-1-N8R2: 35 of 36 GPIOs assigned, GPIO1 spare (rev B)",
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


ALL = [fig_weight, fig_thrust, fig_flight, fig_power, fig_cost, fig_ducts, fig_flip, fig_pinout]

if __name__ == "__main__":
    for f in ALL:
        for th in ("light", "dark"):
            out = f(th)
            print("wrote", out.relative_to(REPO))
