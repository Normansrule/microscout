# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (simulation only)
# SPDX-License-Identifier: MIT
"""Record the Flight Lab (docs/lab) into the GIFs and stills used by the README.

The lab is driven frame by frame through window.lab.tick() so the recordings do not depend on
how fast this machine renders. three.js is served from tools/viz/render3d/node_modules (same
version as the lab's import map) so no network access is needed.

    python tools/viz/lab_capture.py            # all clips -> docs/figures/lab/
    python tools/viz/lab_capture.py race       # one clip

Needs: playwright (Python) with a Chromium, ffmpeg.
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

from playwright.async_api import async_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
THREE = REPO / "tools/viz/render3d/node_modules/three"
OUT = DOCS / "figures/lab"
CHROMIUM = "/opt/pw-browsers/chromium"     # set to None to use Playwright's own browser
FPS = 15


def serve() -> int:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


async def route(r):
    url = r.request.url
    if "cdn.jsdelivr.net/npm/three@" in url:
        p = THREE / url.split("/three@", 1)[1].split("/", 1)[1]
        return await (r.fulfill(path=str(p), content_type="application/javascript") if p.exists() else r.fulfill(status=404))
    if "fonts.googleapis" in url or "fonts.gstatic" in url:
        return await r.abort()
    return await r.continue_()


def to_gif(frames: pathlib.Path, out: pathlib.Path, width: int, fps: int = FPS, colors: int = 128, dither: str = "bayer:bayer_scale=4"):
    """Two-pass palette GIF; keeps the files small enough for a README."""
    pal = frames / "palette.png"
    src = ["-framerate", str(fps), "-i", str(frames / "f%04d.png")]
    scale = f"fps={fps},scale={width}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-vf", f"{scale},palettegen=max_colors={colors}:stats_mode=diff", str(pal)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-i", str(pal), "-lavfi",
                    f"{scale}[x];[x][1:v]paletteuse=dither={dither}:diff_mode=rectangle", "-loop", "0", str(out)], check=True)
    print(f"  {out.relative_to(REPO)}  {out.stat().st_size / 1e6:.2f} MB")


class Rec:
    def __init__(self, page, name, selector="#view"):
        self.page, self.name, self.sel = page, name, selector
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix=f"lab-{name}-"))
        self.n = 0

    async def shot(self, still: str | None = None):
        el = await self.page.query_selector(self.sel)
        p = self.dir / f"f{self.n:04d}.png"
        await el.screenshot(path=str(p))
        self.n += 1
        if still:
            shutil.copy(p, OUT / still)

    async def tick(self, sim_dt: float, n: int = 1):
        await self.page.evaluate("([dt, n]) => { for (let i = 0; i < n; i++) lab.tick(dt, (window._now = (window._now || 1e6) + dt * 1000)); }", [sim_dt, n])

    def gif(self, width: int, **kw):
        to_gif(self.dir, OUT / f"{self.name}.gif", width, **kw)
        shutil.rmtree(self.dir)


async def open_lab(browser, port, query, size, scheme="light"):
    ctx = await browser.new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=scheme, device_scale_factor=1)
    await ctx.route("**/*", route)
    page = await ctx.new_page()
    page.on("pageerror", lambda e: print("  page error:", e))
    await page.goto(f"http://127.0.0.1:{port}/lab/{query}")
    await page.wait_for_function("window.lab !== undefined", timeout=30000)
    await page.evaluate("lab.state.manual = true")
    return ctx, page


async def clip_race(browser, port):
    """All four controllers on the gate course, seen from above one corner."""
    ctx, page = await open_lab(browser, port, "?embed&course=gates", (960, 540))
    await page.evaluate("""() => { lab.race(); lab.view.camMode = 'orbit';
      lab.view.camera.position.set(-6.2, 5.2, 5.6); lab.view.controls.target.set(0.6, 0.4, 0); lab.view.controls.update(); }""")
    rec = Rec(page, "lab-race")
    for i in range(int(16.5 * FPS / 1.5)):
        await rec.tick(1.5 / FPS / 4, 4)
        await rec.shot("lab-race.png" if i == 70 else None)
        if i > 20 and await page.evaluate("lab.state.sims.every(s => s.status !== 'flying')"):
            break
    for _ in range(FPS):
        await rec.tick(1 / FPS); await rec.shot()
    rec.gif(800)
    await ctx.close()


async def clip_forest(browser, port):
    """MPC threading the pillar forest with its ToF rays and sampled plans showing."""
    ctx, page = await open_lab(browser, port, "?embed&course=forest&tab=auto", (960, 540))
    await page.evaluate("() => { lab.setCourse('forest', 4); lab.state.ctrlKind = 'mpc'; lab.flyAuto(); lab.setCam('chase'); }")
    rec = Rec(page, "lab-forest-mpc")
    fps = 12
    await rec.tick(1 / 60, 30)
    for i in range(int(7 * fps)):
        await rec.tick(1 / fps / 4, 4)
        await rec.shot("lab-forest-mpc.png" if i == 32 else None)
        if await page.evaluate("lab.state.sims[0].status !== 'flying'"):
            break
    rec.gif(640, fps=fps, colors=80, dither="none")
    await ctx.close()


async def clip_pilot(browser, port):
    """Free flight in beginner mode: take off, slide right, fly through the first gate, back flip, carry on."""
    ctx, page = await open_lab(browser, port, "?embed&course=gates", (960, 540))
    rec = Rec(page, "lab-pilot")
    await page.evaluate("() => { lab.setMode('beginner'); lab.input.handlers.press('t'); }")
    fps = 12
    script = [(1.8, []), (0.75, ["d"]), (0.4, []), (2.2, ["w"]), (0.4, []), (0.0, ["flip"]), (1.6, []), (1.3, ["w"]), (0.8, [])]
    i = 0
    for dur, keys in script:
        if keys == ["flip"]:
            await page.evaluate("lab.doFlip()"); continue
        for k in keys: await page.keyboard.down(k)
        for _ in range(max(1, round(dur * fps))):
            await rec.tick(1 / fps / 4, 4); await rec.shot("lab-pilot.png" if i == 66 else None); i += 1
        for k in keys: await page.keyboard.up(k)
    rec.gif(640, fps=fps, colors=96, dither="none")
    await ctx.close()


async def clip_train(browser, port):
    """The whole app while CEM trains from random weights: population ghosts in the view, learning curve in the rail."""
    ctx, page = await open_lab(browser, port, "?course=gates", (1280, 760))
    await page.evaluate("""() => { document.querySelector('.stamp').style.display = 'block';
      lab.selectTab('train');
      const init = document.querySelector('#initSel'); init.value = 'random'; init.dispatchEvent(new Event('change'));
      const pop = document.querySelector('#popR'); pop.value = 32; pop.dispatchEvent(new Event('input'));
      document.querySelector('.rail').scrollTop = 1e4;
      lab.setCam('orbit'); lab.view.camera.position.set(-6.5, 6.2, 5.8); lab.view.controls.target.set(0.4, 0.4, 0); }""")
    rec = Rec(page, "lab-train", selector="main.lab")
    # Two training iterations per frame, then the frame is drawn: the clip shows the first ~240 iterations
    # regardless of how slow the screenshots are.
    for i in range(120):
        await page.evaluate("""() => new Promise((done) => { const n = lab.state.train.hist.length;
          lab.startTraining(2); const w = () => lab.state.train.hist.length >= n + 2 ? done() : setTimeout(w, 20); w(); })""")
        await rec.tick(1 / 30, 6)
        await rec.shot("lab-train.png" if i == 110 else None)
    await page.evaluate("lab.stopTraining()")
    rec.gif(820, fps=10, colors=96, dither="none")
    await ctx.close()


async def still_ui(browser, port, scheme):
    ctx, page = await open_lab(browser, port, "?course=forest&tab=auto", (1360, 820), scheme)
    await page.evaluate("() => { lab.setCourse('forest', 4); document.querySelector('#ctrlList input[value=mpc]').click(); lab.flyAuto(); lab.setCam('chase'); }")
    for _ in range(40):
        await page.evaluate("for (let i = 0; i < 4; i++) lab.tick(1/60)")
    await page.screenshot(path=str(OUT / f"lab-ui-{scheme}.png"))
    print(f"  docs/figures/lab/lab-ui-{scheme}.png")
    await ctx.close()


async def still_editor(browser, port):
    """The course editor with a custom layout, sensor-only MPC flying it in the top view."""
    ctx, page = await open_lab(browser, port, "?course=custom", (1360, 820))
    await page.evaluate("""() => { lab.selectTab('auto'); document.querySelector('#ctrlList input[value=smpc]').click();
      document.querySelector('#edToggle').click(); lab.flyAuto(); lab.setCam('top');
      for (let i = 0; i < 240; i++) lab.tick(1/30, (window._now = (window._now || 1e6) + 33)); }""")
    await page.screenshot(path=str(OUT / "lab-editor.png"))
    print("  docs/figures/lab/lab-editor.png")
    await ctx.close()


CLIPS = {"race": clip_race, "forest": clip_forest, "pilot": clip_pilot, "train": clip_train}


async def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    port = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROMIUM if CHROMIUM and pathlib.Path(CHROMIUM).exists() else None,
                                    args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        for n in names:
            print(n)
            if n == "editor":
                await still_editor(b, port)
            elif n == "ui":
                await still_ui(b, port, "light"); await still_ui(b, port, "dark")
            else:
                await CLIPS[n](b, port)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or [*CLIPS, "ui", "editor"]))
