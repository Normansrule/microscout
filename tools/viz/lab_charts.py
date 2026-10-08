# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
# SPDX-License-Identifier: MIT
"""Charts for the Flight Lab section of the README.

    node docs/lab/test/compare.mjs 20        # writes docs/data/lab_controllers.json
    python tools/viz/lab_charts.py           # writes docs/figures/lab-{controllers,learning}-{light,dark}.svg

Both charts come from the lab's simulator (estimated parameters), not from a drone.
"""
import json

from theme import REPO, THEMES, new_fig, save_svg, stamp, style_axes, title_block

LAB = REPO / "docs" / "lab"
CTRL = [("pid", "PID cascade"), ("lqr", "LQR"), ("mpc", "MPC, given the map"), ("smpc", "MPC, sensors only"), ("learned", "Learned policy (CEM)")]
SIM = "Flight Lab simulation, estimated parameters"


def fig_controllers(theme):
    import matplotlib.patches as mp
    t = THEMES[theme]
    d = json.loads((REPO / "docs/data/lab_controllers.json").read_text())
    clean, bumped, failed = t["series"][2], t["series"][3], t["warn"]
    fig = new_fig(t, 9.2, 5.0)
    title_block(fig, t, "Which autopilot gets through?",
                f"Left: {d['layouts']} random pillar-forest layouts, same for every controller. Right: mean time of the finished runs on each course.")
    ax = fig.add_axes([0.2, 0.27, 0.33, 0.5])
    style_axes(ax, t, grid_axis="x")
    for i, (k, name) in enumerate(CTRL):
        r = d["results"]["forest"][k]
        y = len(CTRL) - 1 - i
        c, b = r["clean"], r["finished"] - r["clean"]
        ax.barh(y, c, color=clean, height=0.62)
        ax.barh(y, b, left=c, color=bumped, height=0.62)
        ax.barh(y, 1 - r["finished"], left=c + b, color=failed, height=0.62, alpha=0.85)
        ax.text(1.03, y, f"{r['finished'] * 100:.0f} %", va="center", ha="left", color=t["ink"], fontsize=9.5, fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.5, 1]); ax.set_xticklabels(["0", "50 %", "100 %"])
    ax.set_yticks(range(len(CTRL))); ax.set_yticklabels([n for _, n in reversed(CTRL)])
    ax.set_title("Pillar forest: share of runs", loc="left", color=t["ink"], fontsize=11)
    x = 0.2
    for col, txt in [(clean, "no contact"), (bumped, "touched something"), (failed, "crashed or timed out")]:
        fig.patches.append(mp.Rectangle((x, 0.118), 0.012, 0.024, transform=fig.transFigure, color=col))
        fig.text(x + 0.018, 0.13, txt, color=t["ink2"], fontsize=9, va="center")
        x += 0.03 + 0.0066 * len(txt) + 0.012

    ax2 = fig.add_axes([0.64, 0.27, 0.32, 0.5])
    style_axes(ax2, t, grid_axis="x")
    marks = [("gates", "Gate slalom", "o", t["series"][0]), ("forest", "Pillar forest", "s", t["series"][6]), ("window", "Window wall", "D", t["series"][1])]
    for i, (k, _) in enumerate(CTRL):
        y = len(CTRL) - 1 - i
        for course, _, m, col in marks:
            mt = d["results"][course][k]["meanTime"]
            if mt:
                ax2.plot(mt, y, marker=m, color=col, markersize=7, linestyle="none")
    ax2.set_yticks(range(len(CTRL))); ax2.set_yticklabels([])
    ax2.set_xlim(0, 20); ax2.set_ylim(-0.5, len(CTRL) - 0.5); ax.set_ylim(-0.5, len(CTRL) - 0.5)
    ax2.set_xlabel("seconds (lower is faster)", fontsize=9)
    ax2.set_title("Time to finish", loc="left", color=t["ink"], fontsize=11)
    x = 0.64
    for course, label, m, col in marks:
        fig.lines.append(__import__("matplotlib").lines.Line2D([x + 0.006], [0.13], marker=m, color=col, markersize=6, transform=fig.transFigure))
        fig.text(x + 0.016, 0.13, label, color=t["ink2"], fontsize=9, va="center")
        x += 0.03 + 0.0062 * len(label) + 0.005
    stamp(fig, t, SIM)
    return save_svg(fig, "lab-controllers", theme)


ALGS = [("cem", "CEM"), ("es", "OpenAI-ES"), ("ars", "ARS"), ("reinforce", "REINFORCE")]


def smooth(v, n=8):
    out = []
    for i in range(len(v)):
        w = v[max(0, i - n + 1): i + 1]
        out.append(sum(w) / len(w))
    return out


def fig_learning(theme):
    t = THEMES[theme]
    d = json.loads((REPO / "docs/data/lab_learning.json").read_text())
    fig = new_fig(t, 9.2, 4.3)
    title_block(fig, t, "Learning to fly through a window from scratch",
                f"Random starting weights, a new layout every iteration, {d['seeds']} training runs per algorithm. Line = score on 2 fixed test layouts, smoothed over 8 iterations.")
    for ci, (k, label) in enumerate(ALGS):
        runs = d["runs"][k]
        ax = fig.add_axes([0.065 + ci * 0.235, 0.33, 0.2, 0.42])
        style_axes(ax, t, grid_axis="y")
        col = t["series"][[0, 1, 2, 6][ci]]
        for r in runs:
            ax.plot(range(1, len(r["val"]) + 1), smooth(r["val"]), color=col, linewidth=1.3, alpha=0.9)
        ax.set_ylim(-25, 135)
        if ci == 0:
            ax.set_ylabel("return", fontsize=9)
        else:
            ax.set_yticklabels([])
        ax.set_xlabel("iteration", fontsize=9)
        ax.set_title(label, loc="left", color=t["ink"], fontsize=11)
        last = sum(sum(r["success"][-20:]) / 20 for r in runs) / len(runs)
        ax.text(0, -0.33, f"last 20 iterations: {last * 100:.0f} %\nof test flights finished", transform=ax.transAxes, color=t["ink2"], fontsize=8.8, va="top", linespacing=1.3)
    stamp(fig, t, SIM)
    return save_svg(fig, "lab-learning", theme)


if __name__ == "__main__":
    for th in ("light", "dark"):
        print(fig_controllers(th).relative_to(REPO))
        print(fig_learning(th).relative_to(REPO))
