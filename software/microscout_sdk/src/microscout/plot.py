# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Quick-look plots of a telemetry log (needs matplotlib)."""


def plot_log(log, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = [s.t for s in log]
    fig, ax = plt.subplots(4, 1, figsize=(9, 8), sharex=True)
    ax[0].plot(t, [s.height for s in log], color="#2a78d6", lw=1.6)
    ax[0].set_ylabel("height (m)")
    for i, (lab, c) in enumerate(zip(("roll", "pitch", "yaw"), ("#2a78d6", "#eb6834", "#1baf7a"))):
        ax[1].plot(t, [s.rates_dps[i] for s in log], color=c, lw=1.2, label=lab)
    ax[1].set_ylabel("rate (deg/s)")
    ax[1].legend(frameon=False, ncol=3, fontsize=8)
    for i, c in enumerate(("#2a78d6", "#eb6834", "#1baf7a", "#eda100")):
        ax[2].plot(t, [s.motors[i] for s in log], color=c, lw=1, label=f"M{i+1}")
    ax[2].set_ylabel("motor cmd")
    ax[2].legend(frameon=False, ncol=4, fontsize=8)
    ax[3].plot(t, [s.battery_a for s in log], color="#2a78d6", lw=1.2)
    ax[3].set_ylabel("battery (A)")
    ax[3].set_xlabel("time (s)")
    for a in ax:
        a.grid(color="#e1e0d9", lw=0.8)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.suptitle("MicroScout simulator log (estimated parameters, not a measurement)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
