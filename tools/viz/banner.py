# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""README banner and gate-roadmap images (light + dark), drawn with Pillow.

  python3 tools/viz/banner.py      (needs docs/figures/renders/hero-cutout.png from render.py --banner)

The numbers on the banner are read from review/G1/calc/budgets.py so they stay in sync.
Licence: MIT.
"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "docs" / "figures"
sys.path.insert(0, str(REPO / "review" / "G1" / "calc"))
import budgets as B  # noqa: E402

FONT_DIR = pathlib.Path("/usr/share/fonts/opentype/inter")

THEMES = {
    "light": dict(bg0=(247, 248, 250), bg1=(229, 235, 243), ink=(11, 11, 11), ink2=(72, 76, 84), muted=(137, 140, 146),
                  accent=(42, 120, 214), chip=(255, 255, 255), chip_line=(214, 219, 226), ok=(0, 131, 0), warn=(176, 112, 0),
                  warn_bg=(253, 242, 214), ok_bg=(224, 243, 224), todo=(150, 154, 160), line=(200, 205, 212), card=(255, 255, 255)),
    "dark": dict(bg0=(14, 17, 22), bg1=(27, 33, 43), ink=(240, 242, 245), ink2=(184, 190, 199), muted=(130, 136, 146),
                 accent=(98, 158, 236), chip=(33, 39, 50), chip_line=(56, 64, 78), ok=(84, 196, 110), warn=(240, 180, 60),
                 warn_bg=(60, 46, 16), ok_bg=(22, 52, 30), todo=(110, 116, 126), line=(60, 68, 82), card=(24, 29, 37)),
}

GATES = [  # (gate, title, state, note)
    ("G1", "Architecture & parts", "done", "approved 2026-10-07"),
    ("G2", "Schematics", "review", "awaiting review"),
    ("G3", "PCB layout", "todo", ""),
    ("G4", "Fab outputs", "todo", ""),
    ("G5", "Mechanical", "todo", "concept CAD exists"),
    ("G6", "Firmware & bench", "todo", "SDK + simulator exist"),
    ("G7", "First flight", "todo", ""),
    ("G8", "Release", "todo", ""),
]


def f(weight, size):
    name = {"bold": "Inter-Bold.otf", "semi": "Inter-SemiBold.otf", "med": "Inter-Medium.otf", "reg": "Inter-Regular.otf",
            "disp": "InterDisplay-Bold.otf"}[weight]
    p = FONT_DIR / name
    if not p.exists():
        p = pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if weight in ("bold", "semi", "disp") else
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(str(p), size)


def gradient(w, h, c0, c1):
    img = Image.new("RGB", (w, h), c0)
    px = img.load()
    for x in range(w):
        t = x / (w - 1)
        col = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
        for y in range(h):
            px[x, y] = col
    return img


def pill(d, x, y, text, font, fg, bg, line=None, padx=18, pady=10, r=None):
    tw = d.textlength(text, font=font)
    asc, desc = font.getmetrics()
    h = asc + desc + 2 * pady
    w = tw + 2 * padx
    d.rounded_rectangle((x, y, x + w, y + h), radius=r or h // 2, fill=bg, outline=line, width=2 if line else 0)
    d.text((x + padx, y + pady), text, font=font, fill=fg)
    return w, h


def banner(theme):
    t = THEMES[theme]
    W, H = 1600, 520
    img = gradient(W, H, t["bg0"], t["bg1"])
    d = ImageDraw.Draw(img)
    # subtle accent bar
    d.rectangle((0, 0, W, 6), fill=t["accent"])
    tot, lo, hi = B.weight_totals()
    tw_lo = 4 * B.THRUST_SCENARIOS[0][0] / tot
    tw_hi = 4 * B.THRUST_SCENARIOS[-1][0] / tot
    x0 = 72
    d.text((x0, 64), "OPEN-SOURCE MICRO DRONE", font=f("semi", 22), fill=t["accent"])
    d.text((x0 - 4, 96), "MicroScout", font=f("disp", 104), fill=t["ink"])
    d.text((x0, 222), "A palm-sized ESP32-S3 brushless camera drone,", font=f("med", 31), fill=t["ink2"])
    d.text((x0, 262), "designed to flip, survive crashes, and be easy", font=f("med", 31), fill=t["ink2"])
    d.text((x0, 302), "to fly and to program.", font=f("med", 31), fill=t["ink2"])
    chips = ["95 mm", "2S brushless", f"~{tot:.1f} g est.", f"T/W {tw_lo:.1f}–{tw_hi:.1f} est.", "Python SDK"]
    x, y = x0, 362
    for c in chips:
        w, h = pill(d, x, y, c, f("semi", 20), t["ink"], t["chip"], t["chip_line"], padx=14, pady=8)
        x += w + 10
    pill(d, x0, 428, "Gate G2 · schematics drafted · nothing built or flown yet", f("semi", 20), t["warn"], t["warn_bg"], padx=16, pady=8)
    # drone cut-out with a soft shadow
    cut = Image.open(REPO / "docs" / "figures" / "renders" / "hero-cutout.png").convert("RGBA")
    scale = 390 / cut.height
    cut = cut.resize((int(cut.width * scale), int(cut.height * scale)), Image.LANCZOS)
    cx, cy = W - cut.width - 48, (H - cut.height) // 2 + 6
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((cx + 60, cy + 40, cx + cut.width - 40, cy + cut.height + 10), fill=t["accent"] + (60 if theme == "dark" else 38,))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    img.alpha_composite(cut, (cx, cy))
    d = ImageDraw.Draw(img)
    d.text((W - 600, H - 34), "Concept render · draft · CERN-OHL-S / GPL-3.0 / MIT / CC-BY-SA", font=f("reg", 17), fill=t["muted"])
    img.convert("RGB").save(OUT / f"banner-{theme}.png", optimize=True)


def roadmap(theme):
    t = THEMES[theme]
    W, H = 1600, 250
    img = Image.new("RGB", (W, H), t["card"])
    d = ImageDraw.Draw(img)
    n = len(GATES)
    left, right = 150, W - 150
    y = 112
    step = (right - left) / (n - 1)
    done_x = left + step * [g[2] for g in GATES].index("review")
    d.line((left, y, right, y), fill=t["line"], width=6)
    d.line((left, y, done_x, y), fill=t["ok"], width=6)
    for i, (g, title, state, note) in enumerate(GATES):
        x = left + step * i
        r = 30
        if state == "done":
            d.ellipse((x - r, y - r, x + r, y + r), fill=t["ok"])
            d.line((x - 13, y + 1, x - 4, y + 11), fill=(255, 255, 255), width=6)
            d.line((x - 4, y + 11, x + 14, y - 10), fill=(255, 255, 255), width=6)
        elif state == "review":
            d.ellipse((x - r - 10, y - r - 10, x + r + 10, y + r + 10), fill=t["warn_bg"])
            d.ellipse((x - r, y - r, x + r, y + r), fill=t["warn"])
            d.text((x, y), g, font=f("bold", 22), fill=(255, 255, 255), anchor="mm")
        else:
            d.ellipse((x - r, y - r, x + r, y + r), fill=t["card"], outline=t["todo"], width=4)
            d.text((x, y), g, font=f("bold", 22), fill=t["todo"], anchor="mm")
        col = t["ink"] if state != "todo" else t["ink2"]
        d.text((x, y + 56), title, font=f("semi", 21), fill=col, anchor="mm")
        if note:
            ncol = {"done": t["ok"], "review": t["warn"]}.get(state, t["muted"])
            d.text((x, y + 88), note, font=f("med", 18), fill=ncol, anchor="mm")
    d.text((60, 26), "Gate roadmap - the owner reviews and approves each gate before the next starts", font=f("semi", 22), fill=t["ink2"])
    img.save(OUT / f"roadmap-{theme}.png", optimize=True)


def social():
    """1280x640 image for GitHub's social preview (Settings -> General -> Social preview)."""
    ban = Image.open(OUT / "banner-light.png").resize((1280, 416), Image.LANCZOS)
    road = Image.open(OUT / "roadmap-light.png").resize((1280, 200), Image.LANCZOS)
    img = Image.new("RGB", (1280, 640), THEMES["light"]["card"])
    img.paste(ban, (0, 0))
    img.paste(road, (0, 428))
    img.save(OUT / "social-preview.png", optimize=True)


def main():
    for th in THEMES:
        banner(th)
        roadmap(th)
    social()
    print("wrote docs/figures/banner-{light,dark}.png, roadmap-{light,dark}.png and social-preview.png")


if __name__ == "__main__":
    main()
