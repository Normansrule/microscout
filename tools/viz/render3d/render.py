#!/usr/bin/env python3
# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G5 (concept renders)
# SPDX-License-Identifier: MIT
"""Headless renders of the concept model with three.js in Chromium.

Needs: `npm install` in this folder (three.js), Python playwright, a Chromium
(set CHROMIUM=/path if Playwright's own browser is not installed).
Outputs PNG stills, a turntable GIF and a simulated-flip GIF in docs/figures/renders/.
Run from the repo root: python3 tools/viz/render3d/render.py
"""
import asyncio
import functools
import http.server
import io
import json
import os
import pathlib
import sys
import threading

from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "figures" / "renders"
STAMP = "MicroScout rev B · CONCEPT RENDER · frame/canopy = parametric CAD, other parts = simplified envelopes · DRAFT – UNVERIFIED"


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def annotate(img, title=None, sub=None, stamp=STAMP):
    d = ImageDraw.Draw(img)
    W, H = img.size
    if title:
        d.text((int(W * 0.03), int(H * 0.04)), title, fill=(11, 11, 11), font=font(int(H * 0.042)))
    if sub:
        d.text((int(W * 0.03), int(H * 0.04) + int(H * 0.058)), sub, fill=(82, 81, 78), font=font(int(H * 0.024)))
    d.text((int(W * 0.03), H - int(H * 0.045)), stamp, fill=(137, 135, 129), font=font(int(H * 0.019)))
    return img


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}/tools/viz/render3d/render.html"
    exe = os.environ.get("CHROMIUM")
    async with async_playwright() as p:
        kw = dict(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        if exe:
            kw["executable_path"] = exe
        b = await p.chromium.launch(**kw)

        async def page(w, h, bg="#eef0f2"):
            pg = await b.new_page(viewport={"width": w, "height": h})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await pg.goto(f"{base}?w={w}&h={h}&bg={bg.replace('#', '%23')}")
            await pg.wait_for_function("window.ready === true", timeout=120000)
            if errs:
                print("page errors:", errs)
            return pg

        async def shot(pg, opts):
            await pg.evaluate("o => window.renderView(o)", opts)
            png = await (await pg.query_selector("#c")).screenshot()
            return Image.open(io.BytesIO(png)).convert("RGB")

        only_flip = "--flip-only" in sys.argv
        pg = await page(1600, 1000)
        stills = [] if only_flip else [
            ("hero", dict(view="hero", dist=330, prop=0.4), "MicroScout rev B – concept", "95 mm ducted 2S brushless micro drone · one-piece PA11 frame · TPU canopy"),
            ("exploded", dict(view="hero", dist=380, explode=1.0, prop=0.4), "Exploded view", "canopy · flight controller (ESP32-S3) · 4-in-1 ESC · frame · sensor pod · battery on top"),
            ("front", dict(view="low", dist=300, prop=0.4), "Camera + 8×8 ToF face forward", "ducts double as bumpers; boards sit inside the ducts' footprint, never in the load path"),
            ("top", dict(view="top", dist=330, prop=0.4), "Top view", "board corners notched around the duct inlets"),
            ("under", dict(view="under", dist=320, prop=0.4), "Underside", "down-facing ToF + optical-flow pod in the tray window"),
        ]
        for name, opts, t, s in stills:
            img = annotate(await shot(pg, opts), t, s)
            img.save(OUT / f"{name}.png", optimize=True)
            img.resize((800, 500), Image.LANCZOS).save(OUT / f"{name}-small.png", optimize=True)
            print("wrote", (OUT / f"{name}.png").relative_to(REPO))

        # turntable
        pg2 = await page(800, 500)
        frames = []
        import math
        for k in range(0 if only_flip else 48):
            a = 2 * math.pi * k / 48
            cam = [330 * math.cos(a) * 0.79, 175, 330 * math.sin(a) * 0.79]
            img = await shot(pg2, dict(camPos=cam, camLook=[0, 18, 0], prop=k * 0.9))
            frames.append(annotate(img, None, None, "MicroScout rev B · concept turntable · not a render of a finished design · DRAFT"))
        if frames:
            save_gif(frames, OUT / "turntable.gif", 70)
            print("wrote turntable.gif")

        # simulated back flip, rendered from the simulator's pose log
        traj = REPO / "docs" / "data" / "sim_flip.json"
        if traj.exists():
            data = json.loads(traj.read_text())["samples"]
            frames = []
            for i, s in enumerate(data):
                X, Y, Z = s["p"][0] * 1000, -s["p"][2] * 1000 + 15, s["p"][1] * 1000
                img = await shot(pg2, dict(camPos=[X + 140, Y + 90, Z + 520], camLook=[X, Y, Z], pose=dict(p=s["p"], q=s["q"]), prop=i * 1.3))
                d = ImageDraw.Draw(img)
                d.text((24, 20), "Simulated back flip (estimated parameters)", fill=(11, 11, 11), font=font(22))
                d.text((24, 50), f"t = {s['t']:+.2f} s   height = {-s['p'][2]:.2f} m   (shown 2.5x slower)", fill=(82, 81, 78), font=font(16))
                frames.append(annotate(img, None, None, "MicroScout SDK simulator → concept model · not real flight data · DRAFT – UNVERIFIED"))
            save_gif(frames, OUT / "sim-backflip.gif", 50)
            print("wrote sim-backflip.gif")
        await b.close()
    srv.shutdown()


def save_gif(frames, path, ms):
    pal = [f.quantize(colors=160, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=True, disposal=1)


if __name__ == "__main__":
    asyncio.run(main())
