// STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
// SPDX-License-Identifier: MIT
// Pilot input: keyboard, gamepad (standard mapping, Mode 2) and on-screen touch sticks.

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export class PilotInput {
  constructor(touchRoot = null) {
    this.keys = new Set();
    this.acroThrottle = 0.35;
    this.touch = { lx: 0, ly: 0, rx: 0, ry: 0, active: false };
    this.handlers = {};
    addEventListener("keydown", (e) => {
      if (e.target.closest && e.target.closest("input, select, textarea")) return;
      const k = e.key.toLowerCase();
      const nav = [" ", "enter", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(k);
      if (nav && e.target.closest && e.target.closest("button, a, [role=tab]")) return;    // let buttons and tabs work from the keyboard
      if (nav) e.preventDefault();
      if (!this.keys.has(k)) this.handlers.press?.(k);
      this.keys.add(k);
    });
    addEventListener("keyup", (e) => this.keys.delete(e.key.toLowerCase()));
    addEventListener("blur", () => this.keys.clear());
    if (touchRoot) this.bindTouch(touchRoot);
    this.prevButtons = [];
  }

  bindTouch(root) {
    for (const side of ["l", "r"]) {
      const pad = root.querySelector(`[data-stick="${side}"]`);
      if (!pad) continue;
      const knob = pad.querySelector(".knob");
      let id = null;
      const set = (e) => {
        const r = pad.getBoundingClientRect();
        const x = clamp(((e.clientX - r.left) / r.width) * 2 - 1, -1, 1), y = clamp(((e.clientY - r.top) / r.height) * 2 - 1, -1, 1);
        this.touch[side + "x"] = x; this.touch[side + "y"] = -y; this.touch.active = true;
        knob.style.transform = `translate(${x * 34}px, ${y * 34}px)`;
      };
      pad.addEventListener("pointerdown", (e) => { id = e.pointerId; pad.setPointerCapture(id); set(e); });
      pad.addEventListener("pointermove", (e) => { if (e.pointerId === id) set(e); });
      const end = () => { id = null; this.touch[side + "x"] = 0; if (side === "r") this.touch.ry = 0; else this.touch.ly = this.touch.ly; knob.style.transform = ""; };
      pad.addEventListener("pointerup", end); pad.addEventListener("pointercancel", end);
    }
  }

  /** Returns sticks {roll, pitch, yaw, throttle (0..1)} for the given flight mode. */
  read(mode, dt) {
    const k = this.keys;
    let roll = (k.has("d") || k.has("arrowright") ? 1 : 0) - (k.has("a") || k.has("arrowleft") ? 1 : 0);
    let pitch = (k.has("w") || k.has("arrowup") ? 1 : 0) - (k.has("s") || k.has("arrowdown") ? 1 : 0);
    let yaw = (k.has("e") ? 1 : 0) - (k.has("q") ? 1 : 0);
    let up = (k.has(" ") || k.has("r") ? 1 : 0) - (k.has("shift") || k.has("f") ? 1 : 0);
    const gp = navigator.getGamepads ? [...navigator.getGamepads()].find((g) => g && g.connected) : null;
    this.gamepad = !!gp;
    let thrAxis = null;
    if (gp) {
      const dz = (v) => (Math.abs(v) < 0.08 ? 0 : v);
      yaw += dz(gp.axes[0] || 0); thrAxis = -dz(gp.axes[1] || 0);
      roll += dz(gp.axes[2] || 0); pitch += -dz(gp.axes[3] || 0);
      const b = gp.buttons.map((x) => x.pressed);
      const edge = (i) => b[i] && !this.prevButtons[i];
      if (edge(0)) this.handlers.press?.("t");
      if (edge(1)) this.handlers.press?.("l");
      if (edge(2)) this.handlers.press?.("x-flip");
      if (edge(3)) this.handlers.press?.("m");
      this.prevButtons = b;
    }
    if (this.touch.active) { yaw += this.touch.lx; roll += this.touch.rx; pitch += this.touch.ry; thrAxis = (thrAxis ?? 0) + this.touch.ly; }
    roll = clamp(roll, -1, 1); pitch = clamp(pitch, -1, 1); yaw = clamp(yaw, -1, 1);
    let throttle;
    if (mode === "acro") {
      if (thrAxis != null) this.acroThrottle = clamp(0.5 + thrAxis * 0.5, 0, 1);
      else this.acroThrottle = clamp(this.acroThrottle + up * 0.6 * dt, 0, 1);
      throttle = this.acroThrottle;
    } else throttle = clamp(0.5 + (thrAxis ?? up) * 0.5, 0, 1);
    return { roll, pitch, yaw, throttle };
  }
}
