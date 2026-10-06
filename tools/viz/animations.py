#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1
# SPDX-License-Identifier: MIT
"""Animated GIFs that explain the G1 architecture.

  drone-concept.gif       top view: spinning props, guard rings, sensor fields of view
  tof-addressing.gif      boot-time I2C re-addressing of the five ToF sensors
  power-on-sequence.gif   what happens between pressing the button and "ready"

These are ILLUSTRATIONS of the draft design, not renders or simulations of real
hardware. Values that come from a source are labelled in the frames; everything
else is marked illustrative. Run: python3 tools/viz/animations.py
"""
import math

import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle, Wedge
from PIL import Image

from theme import ANIM_DIR, REPO, THEMES, load_budgets, new_fig, read_csv_rows

B = load_budgets()
T = THEMES["light"]
W_PX, H_PX = 960, 540


def frame_of(fig):
    fig.canvas.draw()
    img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    return img


def save_gif(frames, durations_ms, name):
    ANIM_DIR.mkdir(parents=True, exist_ok=True)
    pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    out = ANIM_DIR / f"{name}.gif"
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations_ms, loop=0, optimize=True, disposal=1)
    return out


def header(fig, title, subtitle):
    fig.text(0.03, 0.955, title, color=T["ink"], fontsize=14, fontweight="bold", va="top")
    fig.text(0.03, 0.895, subtitle, color=T["ink2"], fontsize=9, va="top")


def footer(fig, text):
    fig.text(0.03, 0.02, "MicroScout · G1 · DRAFT – UNVERIFIED · " + text, color=T["muted"], fontsize=7.5, va="bottom")


# ==========================================================================
# 1. Drone concept, top view
def drone_concept():
    D = B.MOTOR_TO_MOTOR_MM.value
    s = D / math.sqrt(2)
    prop_r = B.PROP_MM.value / 2
    guard_r = prop_r + 3 + 1
    motors = [(-s / 2, s / 2, +1), (s / 2, s / 2, -1), (s / 2, -s / 2, +1), (-s / 2, -s / 2, -1)]  # +1 = CCW
    # FoV: VL53L5CX 63 deg diagonal square -> horizontal = 2 atan(tan(31.5)/sqrt2)
    fwd_half = math.degrees(math.atan(math.tan(math.radians(31.5)) / math.sqrt(2)))
    side_half = 27 / 2
    n = 40
    frames = []
    for k in range(n):
        ph = k / n
        fig = new_fig(T, W_PX / 100, H_PX / 100)
        header(fig, "MicroScout concept – top view (illustrative)",
               f"{D:.0f} mm motor-to-motor · {B.PROP_MM.value:.0f} mm props in guard rings · sensor fields of view (ranges not to scale)")
        ax = fig.add_axes([0.0, 0.07, 0.62, 0.8])
        ax.set_facecolor(T["surface"])
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-120, 120)
        ax.set_ylim(-95, 120)
        sc = T["series"]
        # FoV wedges (draw first)
        L = 95
        ax.add_patch(Wedge((0, 26), L, 90 - fwd_half, 90 + fwd_half, facecolor=sc[0], alpha=0.10, edgecolor=sc[0], lw=1))
        # 8 zones sweeping (8x8 grid seen edge-on as 8 columns)
        zi = int(ph * 16) % 8
        a0 = 90 - fwd_half + zi * (2 * fwd_half / 8)
        ax.add_patch(Wedge((0, 26), L, a0, a0 + 2 * fwd_half / 8, facecolor=sc[0], alpha=0.30, lw=0))
        for (cx, cy, ang, col) in [(-24, 0, 180, sc[1]), (24, 0, 0, sc[1]), (0, -26, 270, sc[1])]:
            ax.add_patch(Wedge((cx, cy), 70, ang - side_half, ang + side_half, facecolor=col, alpha=0.10, edgecolor=col, lw=1))
            r = 10 + 60 * ((ph * 2) % 1.0)
            ax.add_patch(Wedge((cx, cy), r, ang - side_half, ang + side_half, width=2.2, facecolor=col, alpha=0.55, lw=0))
        # arms + body + canopy
        for (x, y, _) in motors:
            ax.plot([0, x], [0, y], color=T["axis"], lw=9, solid_capstyle="round", zorder=2)
        ax.add_patch(FancyBboxPatch((-25, -32), 50, 64, boxstyle="round,pad=0,rounding_size=12",
                                    facecolor=T["page"], edgecolor=T["ink2"], lw=1.4, zorder=3))
        ax.add_patch(Rectangle((-9, -29), 18, 58, facecolor=T["grid"], edgecolor="none", zorder=3, alpha=0.9))
        ax.text(0, -20, "battery\n(under board)", ha="center", va="center", fontsize=6.5, color=T["ink2"], zorder=4)
        ax.add_patch(Rectangle((-5, 25), 10, 5, facecolor=T["ink2"], zorder=4))
        ax.text(0, 36, "camera + 8×8 ToF", ha="center", fontsize=7, color=T["ink"], zorder=6,
                bbox=dict(facecolor=T["surface"], edgecolor="none", pad=1))
        ax.add_patch(Circle((0, 0), 6, facecolor="none", edgecolor=sc[2], lw=1.6, ls=(0, (2, 2)), zorder=5))
        ax.text(0, 8, "down: ToF + flow", ha="center", fontsize=6.5, color=T["ink"], zorder=6)
        ax.annotate("", xy=(0, 112), xytext=(0, 100), arrowprops=dict(arrowstyle="-|>", color=T["ink2"], lw=1.2))
        ax.text(5, 106, "front", fontsize=8, color=T["ink2"], va="center")
        # LEDs blink (status illustration)
        led_on = (k // 5) % 2 == 0
        for (x, y, _) in motors:
            ax.add_patch(Circle((x * 0.66, y * 0.66), 2.2, facecolor=sc[2] if led_on else T["grid"], edgecolor="none", zorder=4))
        # props
        for (x, y, d) in motors:
            ax.add_patch(Circle((x, y), guard_r, facecolor="none", edgecolor=T["ink2"], lw=1.6, zorder=5))
            ax.add_patch(Circle((x, y), prop_r, facecolor=sc[0], alpha=0.07, edgecolor="none", zorder=5))
            th = d * 2 * math.pi * ph * 3 + (0.6 if d > 0 else 0)
            for bl in (0, math.pi):
                a = th + bl
                ax.plot([x, x + prop_r * math.cos(a)], [y, y + prop_r * math.sin(a)], color=T["ink"], lw=2.4,
                        solid_capstyle="round", zorder=6, alpha=0.85)
            ax.add_patch(Circle((x, y), 4.25, facecolor=T["ink2"], zorder=7))
            arr = "↺" if d > 0 else "↻"
            ax.text(x + (14 if x > 0 else -14), y + (prop_r + 8) * (1 if y > 0 else -1), f"{arr} {'CCW' if d > 0 else 'CW'}",
                    ha="center", fontsize=7.5, color=T["ink2"], zorder=8)
        # side panel legend / facts
        tx = 0.64
        lines = [
            ("Forward 8×8 multizone ToF (VL53L5CX)", f"63° diagonal FoV ≈ {2*fwd_half:.0f}° across · up to 4 m", sc[0]),
            ("Left / right / rear ToF (VL53L1X ×3)", "27° FoV each · up to 4 m", sc[1]),
            ("Downward ToF + optical flow", "VL53L1X + PMW3901 (flow lens source open)", sc[2]),
            ("Guard rings", f"{B.PROP_MM.value:.0f} mm props, 3 mm clearance + 1 mm wall (estimate)", T["ink2"]),
        ]
        y0 = 0.78
        for ttl, sub, col in lines:
            fig.patches.append(Rectangle((tx, y0 - 0.006), 0.012, 0.032, transform=fig.transFigure, facecolor=col, edgecolor="none"))
            fig.text(tx + 0.022, y0 + 0.022, ttl, fontsize=9, color=T["ink"], va="top")
            fig.text(tx + 0.022, y0 - 0.016, sub, fontsize=8, color=T["ink2"], va="top")
            y0 -= 0.12
        fig.text(tx, y0 - 0.0, "Spin directions and motor numbering are\nplaceholders until the G2 schematic.", fontsize=8,
                 color=T["ink2"], va="top")
        footer(fig, "concept sketch, not a render: no CAD exists yet. FoV figures: ST datasheet values via Pololu/SparkFun product pages.")
        frames.append(frame_of(fig))
        import matplotlib.pyplot as plt
        plt.close(fig)
    return save_gif(frames, [70] * len(frames), "drone-concept")


# ==========================================================================
# 2. ToF re-addressing at boot
TOF = [("U15", "down", "VL53L1X", "XSHUT", "P0", "0x31"),
       ("U16", "left", "VL53L1X", "XSHUT", "P1", "0x32"),
       ("U17", "right", "VL53L1X", "XSHUT", "P2", "0x33"),
       ("U18", "rear", "VL53L1X", "XSHUT", "P3", "0x34"),
       ("U19", "forward", "VL53L5CX", "LPn", "P4", "0x35")]


def tof_frame(state, released, msg, packet=None, highlight=None):
    """state[i] in {'reset','default','new'}; released[i] bool (expander pin high)."""
    import matplotlib.pyplot as plt
    fig = new_fig(T, W_PX / 100, H_PX / 100)
    header(fig, "Boot: giving five ToF sensors unique I²C addresses",
           "All VL53L1X / VL53L5CX power up at 0x29. Pull-downs hold them in reset; firmware wakes one at a time and moves it.")
    ax = fig.add_axes([0.02, 0.17, 0.96, 0.68])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    sc = T["series"]
    # MCU
    ax.add_patch(FancyBboxPatch((2, 30), 14, 20, boxstyle="round,pad=0,rounding_size=1.5", facecolor=T["page"], edgecolor=T["ink2"], lw=1.3))
    ax.text(9, 40, "ESP32-S3\nI²C master\nGPIO39/40", ha="center", va="center", fontsize=8.5, color=T["ink"])
    # bus
    ax.plot([16, 98], [44, 44], color=sc[2], lw=3)
    ax.text(57, 46.5, "I²C bus · 400 kHz", ha="center", fontsize=8.5, color=T["ink2"])
    # expander
    ax.add_patch(FancyBboxPatch((2, 4), 14, 20, boxstyle="round,pad=0,rounding_size=1.5", facecolor=T["page"], edgecolor=T["ink2"], lw=1.3))
    ax.text(9, 20.5, "U10 TCA6408A\n0x20", ha="center", va="center", fontsize=8, color=T["ink"])
    ax.plot([9, 9], [24, 30], color=T["axis"], lw=1.5)
    ax.text(10, 27, "I²C", fontsize=7, color=T["muted"])
    for i, (ref, where, part, pin, ep, new) in enumerate(TOF):
        x = 22 + i * 15.5
        st = state[i]
        face = {"reset": T["grid"], "default": "#fdf0c2", "new": "#d9e8fa"}[st]
        edge = {"reset": T["axis"], "default": sc[3], "new": sc[0]}[st]
        lw = 2.2 if highlight == i else 1.3
        ax.plot([x + 6, x + 6], [44, 38], color=sc[2] if st != "reset" else T["axis"], lw=2)
        ax.add_patch(FancyBboxPatch((x, 22), 12, 16, boxstyle="round,pad=0,rounding_size=1.2", facecolor=face, edgecolor=edge, lw=lw))
        ax.text(x + 6, 35.2, f"{ref} {where}", ha="center", fontsize=8, color=T["ink"], fontweight="bold")
        ax.text(x + 6, 32.0, part, ha="center", fontsize=7.5, color=T["ink2"])
        addr = {"reset": "in reset", "default": "0x29", "new": new}[st]
        ax.text(x + 6, 26.0, addr, ha="center", fontsize=11 if st != "reset" else 8.5, color=T["ink"],
                fontweight="bold" if st != "reset" else "normal")
        # expander line to XSHUT/LPn
        col = sc[0] if released[i] else T["axis"]
        ax.plot([x + 6, x + 6], [8, 22], color=col, lw=1.6)
        ax.text(x + 6.8, 13.5, f"{pin}\n{ep} = {'1' if released[i] else '0'}", fontsize=7, color=T["ink2"], va="center")
    ax.plot([16, 22 + 4 * 15.5 + 6], [8, 8], color=T["axis"], lw=0.8)
    ax.text(18, 5.5, "pull-down on every XSHUT / LPn line", fontsize=7, color=T["muted"])
    if packet is not None:
        ax.add_patch(Circle((packet, 44), 1.4, facecolor=sc[1], edgecolor=T["surface"], lw=1.5, zorder=5))
    fig.text(0.03, 0.115, msg, fontsize=10.5, color=T["ink"], va="top")
    footer(fig, "sequence from the ST datasheets' XSHUT/LPn method and the G1 expander map; timing illustrative.")
    img = frame_of(fig)
    plt.close(fig)
    return img


def tof_addressing():
    n = len(TOF)
    state = ["reset"] * n
    released = [False] * n
    frames, dur = [], []

    def add(msg, hold, packet=None, hl=None):
        frames.append(tof_frame(list(state), list(released), msg, packet, hl))
        dur.append(hold)

    add("1  Power-up: the TCA6408A pins start as high-impedance inputs, so the pull-downs hold every sensor in reset.", 2200)
    for i, (ref, where, part, pin, ep, new) in enumerate(TOF):
        released[i] = True
        state[i] = "default"
        add(f"{2 + 2 * i}  Firmware sets U10 {ep} high → {ref} ({where}) wakes up at the shared default address 0x29.", 1500, hl=i)
        for pk in np.linspace(17, 22 + i * 15.5 + 6, 6):
            add(f"{3 + 2 * i}  Write to 0x29: “your new address is {new}”.", 90, packet=pk, hl=i)
        state[i] = "new"
        extra = " Then ~84 kB firmware is uploaded over I²C (~1.9 s at 400 kHz, calc)." if part == "VL53L5CX" else ""
        add(f"{3 + 2 * i}  {ref} now answers at {new}; 0x29 is free for the next sensor.{extra}", 1500 if not extra else 2600, hl=i)
    add("Done: 0x31–0x35 are unique. 0x30 is skipped on purpose – it belongs to the OV2640 camera's SCCB port.", 3500)
    return save_gif(frames, dur, "tof-addressing")


# ==========================================================================
# 3. Power-on sequence
EVENTS = [  # (key, label, x position on the non-linear axis 0..100)
    ("press", "0", 4), ("deb", "32 ms", 14), ("rst", "+~10 ms (EN RC)", 24), ("kill0", "400 ms", 44), ("kill1", "650 ms", 54),
    ("fw", "", 64), ("up", "", 78), ("ready", "≈ 3 s", 94),
]


def power_frame(cursor, captions):
    import matplotlib.pyplot as plt
    fig = new_fig(T, W_PX / 100, H_PX / 100)
    header(fig, "Power-on: from button press to “ready to arm”",
           "Order of events in the draft design. Time axis is NOT linear; only the labelled times come from datasheets or calculation.")
    ax = fig.add_axes([0.22, 0.2, 0.75, 0.64])
    ax.set_xlim(0, 100)
    sc = T["series"]
    rows = ["Power button", "LTC2954 EN", "3.3 V / 5 V rails", "Motor rail (Q2)", "Motor gates", "ESP32 reset → run",
            "KILL ignored", "Expanders, cam rails", "ToF addressing + 8×8 FW", "Arming allowed"]
    n = len(rows)
    ax.set_ylim(-0.8, n - 0.2)
    ax.axis("off")
    for i, r in enumerate(rows):
        ax.text(-1.5, n - 1 - i, r, ha="right", va="center", fontsize=8.8, color=T["ink2"], clip_on=False)
        ax.plot([0, 100], [n - 1 - i - 0.35, n - 1 - i - 0.35], color=T["grid"], lw=0.8)

    def y(i):
        return n - 1 - i

    def digital(i, segs, color):
        # segs: list of (x0, x1, level 0/1)
        for x0, x1, lv in segs:
            if x0 >= cursor:
                continue
            x1c = min(x1, cursor)
            yy = y(i) + (0.25 if lv else -0.15)
            ax.plot([x0, x1c], [yy, yy], color=color if lv else T["muted"], lw=2.2, solid_capstyle="butt")
            if lv and x0 > 0.5:
                ax.plot([x0, x0], [y(i) - 0.15, y(i) + 0.25], color=color, lw=2.2)

    digital(0, [(0, 4, 1), (4, 18, 0), (18, 100, 1)], sc[0])            # button active-low press
    digital(1, [(0, 14, 0), (14, 100, 1)], sc[0])
    # rails ramp
    if cursor > 14:
        xs = np.linspace(14, min(cursor, 100), 50)
        ys = y(2) - 0.15 + 0.4 * np.clip((xs - 14) / 5, 0, 1)
        ax.plot(xs, ys, color=sc[1], lw=2.2)
    ax.plot([0, min(cursor, 14)], [y(2) - 0.15] * 2, color=T["muted"], lw=2.2)
    digital(3, [(0, 14, 0), (14, 100, 1)], sc[1])
    digital(4, [(0, 100, 0)], sc[3])                                        # stays low
    digital(5, [(0, 24, 0), (24, 100, 1)], sc[0])
    if cursor > 44:
        ax.add_patch(Rectangle((44, y(6) - 0.3), min(cursor, 54) - 44, 0.6, facecolor=sc[4], alpha=0.35, edgecolor="none"))
    if cursor > 14:
        ax.add_patch(Rectangle((14, y(6) - 0.3), min(cursor, 54) - 14, 0.6, facecolor=sc[4], alpha=0.15, edgecolor="none"))
    for i, (x0, x1, lab) in [(7, (30, 62, "init")), (8, (62, 92, "addressing + ~1.9 s upload"))]:
        if cursor > x0:
            ax.add_patch(Rectangle((x0, y(i) - 0.28), min(cursor, x1) - x0, 0.56, facecolor=sc[2], alpha=0.35, edgecolor="none"))
            ax.text(x0 + 1, y(i), lab, fontsize=7.5, color=T["ink"], va="center")
    digital(9, [(0, 94, 0), (94, 100, 1)], sc[5])
    # time ticks
    for key, lab, x in EVENTS:
        if lab and x <= cursor + 0.1:
            ax.plot([x, x], [-0.55, n - 0.4], color=T["axis"], lw=0.8, zorder=0)
            ax.text(x, -0.75, lab, ha="center", va="top", fontsize=8, color=T["ink2"])
    ax.plot([cursor, cursor], [-0.55, n - 0.4], color=T["warn"], lw=1.2)
    cap = captions[-1] if captions else ""
    fig.text(0.03, 0.11, cap, fontsize=10, color=T["ink"], va="top")
    footer(fig, "debounce 32 ms typ and KILL blanking 400–650 ms: LTC2954 datasheet · upload time: calc (budgets §4f) · rest illustrative.")
    img = frame_of(fig)
    plt.close(fig)
    return img


def power_sequence():
    script = [
        (4, "Press: the LTC2954 sees the button go low and starts its 32 ms debounce (datasheet typ)."),
        (14, "EN goes high: the 3.3 V and 5 V regulators start, and Q3 switches on the motor-rail P-FET Q2."),
        (20, "Motor gates stay LOW the whole time: 100 kΩ pull-downs hold them off while the ESP32 boots."),
        (24, "ESP32 EN releases after its RC delay; it samples straps: GPIO0 = 1, GPIO45 = 0, GPIO46 = 0 → normal boot."),
        (44, "For 400–650 ms after turn-on the LTC2954 ignores KILL (datasheet), so a fault can't power-cycle it instantly."),
        (62, "Firmware brings up the I²C expanders, then the camera rails via CAM_PWR_EN."),
        (78, "ToF sensors are woken one at a time and re-addressed; the 8×8 sensor's firmware upload is ~1.9 s at 400 kHz."),
        (94, "Self-checks pass → arming allowed, unless USB power is present (PGOOD low blocks arming, DR-02)."),
        (100, "Planned behaviour of the draft design – confirmed only by the props-off bench test at Gate G6."),
    ]
    frames, dur, caps = [], [], []
    cur = 0.0
    for x, cap in script:
        steps = max(2, int((x - cur) / 2.5))
        for c in np.linspace(cur, x, steps)[1:]:
            frames.append(power_frame(c, caps))
            dur.append(60)
        caps.append(cap)
        frames.append(power_frame(x, caps))
        dur.append(2600)
        cur = x
    return save_gif(frames, dur, "power-on-sequence")


if __name__ == "__main__":
    for f in (drone_concept, tof_addressing, power_sequence):
        out = f()
        print("wrote", out.relative_to(REPO), f"{out.stat().st_size/1e6:.2f} MB")
