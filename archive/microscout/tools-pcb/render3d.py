# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""3D renders of the routed boards: top, bottom and angled PNGs.

Pipeline: kicad-cli exports a STEP of the board with the KiCad 7 3D models (paths made absolute in a
temporary copy) -> CadQuery converts it to glTF, adding grey envelope boxes for footprints that have no
3D model (heights from HEIGHTS below, ESTIMATES) -> three.js renders it headless in Chromium.

Run with the project venv (CadQuery + Playwright):
    python tools/pcb/render3d.py hardware/drone-pcb/microscout-fc.kicad_pcb review/G3/fc
Env: KICAD_3D=/path/to/kicad/3dmodels (default: the copy extracted from the kicad-packages3d .deb)
"""
import asyncio
import functools
import http.server
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading

REPO = pathlib.Path(__file__).resolve().parents[2]
MODELS = pathlib.Path(os.environ.get("KICAD_3D", "/home/claude/tools-ext/3d/usr/share/kicad/3dmodels"))
CHROMIUM = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium")
# Envelope heights (mm) for footprints without a 3D model - ESTIMATES from typical datasheet heights.
HEIGHTS = {"QFN": 0.9, "VQFN": 0.9, "WSON": 0.75, "LGA": 0.9, "HLGA": 0.8, "PowerPAK": 1.0, "KMR2": 1.9, "JST_SH": 2.95,
           "USB_C": 3.2, "FNR252012": 1.2, "WS2812B": 0.85, "Buzzer": 2.5, "VL53L5CX": 1.5, "Pad": 0.05, "Pigtail": 0.05,
           "SolderWire": 0.05, "TestPoint": 0.02}


LIST_MISSING = r"""
import sys, json, os, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
out = {}
for fp in b.GetFootprints():
    if any(os.path.exists(m.m_Filename) for m in fp.Models()):
        continue
    name = str(fp.GetFPID().GetLibItemName())
    if name in out:
        continue
    pos, rot, flip = fp.GetPosition(), fp.GetOrientationDegrees(), fp.IsFlipped()
    if flip: fp.Flip(pos, False)
    fp.SetOrientationDegrees(0)
    bb = None
    for lay in (pcbnew.F_Fab, pcbnew.F_CrtYd):
        for g in fp.GraphicalItems():
            if g.GetLayer() == lay:
                gb = g.GetBoundingBox()
                if bb is None:
                    bb = pcbnew.BOX2I(gb.GetPosition(), gb.GetSize())     # own copy (Merge returns a reference)
                else:
                    bb.Merge(gb)
        if bb is not None:
            break
    if bb is None:
        bb = fp.GetBoundingBox(False, False)
    out[name] = dict(w=pcbnew.ToMM(bb.GetWidth()), h=pcbnew.ToMM(bb.GetHeight()),
                     ox=pcbnew.ToMM(bb.GetCenter().x - fp.GetPosition().x), oy=pcbnew.ToMM(bb.GetCenter().y - fp.GetPosition().y))
    fp.SetOrientationDegrees(rot)
    if flip: fp.Flip(pos, False)
print(json.dumps(out))
"""

ADD_MODELS = r"""
import sys, json, os, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); env = json.loads(open(sys.argv[2]).read())
for fp in b.GetFootprints():
    name = str(fp.GetFPID().GetLibItemName())
    if name in env and not any(os.path.exists(m.m_Filename) for m in fp.Models()):
        fp.Models().clear()
        m = pcbnew.FP_3DMODEL(); m.m_Filename = env[name]["step"]; m.m_Show = True
        fp.Models().push_back(m)
pcbnew.SaveBoard(sys.argv[1], b)
"""


def envelopes(pcb_tmp, work):
    """Envelope-box STEP models for footprints without a 3D model (heights: HEIGHTS, ESTIMATES)."""
    import cadquery as cq
    r = subprocess.run(["/usr/bin/python3", "-c", LIST_MISSING, str(pcb_tmp)], capture_output=True, text=True, check=True)
    env = json.loads(r.stdout.strip().splitlines()[-1])
    for name, d in env.items():
        h = next((v for k, v in HEIGHTS.items() if k in name), 1.0)
        box = cq.Workplane("XY").box(max(d["w"] * 0.9, 0.3), max(d["h"] * 0.9, 0.3), h, centered=(True, True, False))
        box = box.translate((d["ox"], -d["oy"], 0))
        f = work / f"env_{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.step"
        cq.exporters.export(box, str(f))
        d["step"], d["height"] = str(f), h
    jf = work / "env.json"
    jf.write_text(json.dumps(env))
    subprocess.run(["/usr/bin/python3", "-c", ADD_MODELS, str(pcb_tmp), str(jf)], check=True, capture_output=True)
    return env


def step_to_glb(step, glb):
    """STEP (with KiCad's colours) -> binary glTF through OpenCASCADE's XCAF reader/writer."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Message import Message_ProgressRange
    from OCP.RWGltf import RWGltf_CafWriter
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
    from OCP.TColStd import TColStd_IndexedDataMapOfStringString
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    rd = STEPCAFControl_Reader(); rd.SetColorMode(True); rd.SetNameMode(True)
    if rd.ReadFile(str(step)) != IFSelect_RetDone:
        raise RuntimeError("STEP read failed")
    rd.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = TDF_LabelSequence(); st.GetFreeShapes(labels)
    for i in range(1, labels.Length() + 1):
        BRepMesh_IncrementalMesh(st.GetShape_s(labels.Value(i)), 0.02, False, 0.3, True)
    w = RWGltf_CafWriter(TCollection_AsciiString(str(glb)), True)
    w.Perform(doc, TColStd_IndexedDataMapOfStringString(), Message_ProgressRange())


PAGE = """<!doctype html><html><body style="margin:0;background:#0f1418"><script type="importmap">
{"imports":{"three":"/tools/viz/render3d/node_modules/three/build/three.module.js","three/addons/":"/tools/viz/render3d/node_modules/three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from "three"; import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";
const q = new URLSearchParams(location.search);
const r = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true}); r.setSize(1400, 1000); r.setPixelRatio(1);
r.outputColorSpace = THREE.SRGBColorSpace; document.body.appendChild(r.domElement);
const s = new THREE.Scene(); s.background = new THREE.Color(q.get("bg") || "#eef1f3");
s.add(new THREE.HemisphereLight(0xffffff, 0x445566, 2.2)); const d = new THREE.DirectionalLight(0xffffff, 2.0); d.position.set(30, -40, 80); s.add(d);
const d2 = new THREE.DirectionalLight(0xffffff, 1.0); d2.position.set(-30, 40, -80); s.add(d2);
const ld = new GLTFLoader();
const load = (u) => new Promise((ok) => u ? ld.load(u, (g) => ok(g.scene), undefined, () => ok(null)) : ok(null));
Promise.all([load(q.get("m")), load(q.get("e"))]).then(([board, env]) => {
  const o = new THREE.Group(); if (board) o.add(board); if (env) o.add(env); s.add(o);
  const box = new THREE.Box3().setFromObject(o), c = box.getCenter(new THREE.Vector3()), sz = box.getSize(new THREE.Vector3());
  const R = Math.max(sz.x, sz.y, sz.z);
  const cam = new THREE.PerspectiveCamera(28, 1.4, R / 100, R * 20); cam.up.set(0, 0, 1);
  const v = q.get("v");
  const dir = v === "top" ? [0, -0.0001, 1] : v === "bottom" ? [0, 0.0001, -1] : [-0.9, -1.25, 1.1];
  const n = new THREE.Vector3(...dir).normalize();
  cam.position.copy(c).addScaledVector(n, R * 2.45); if (v === "bottom") cam.up.set(0, 1, 0); if (v === "top") cam.up.set(0, 1, 0);
  cam.lookAt(c); r.render(s, cam); window.done = true;
});
</script></body></html>"""


async def shoot(glb_rel, out_dir, stem):
    from playwright.async_api import async_playwright
    (REPO / "tools/pcb/_render.html").write_text(PAGE)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROMIUM if os.path.exists(CHROMIUM) else None,
                                    args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1400, "height": 1000})
        for v in ("top", "bottom", "angle"):
            await pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/tools/pcb/_render.html?m=/{glb_rel}&v={v}")
            await pg.wait_for_function("window.done === true", timeout=120000)
            await pg.screenshot(path=str(out_dir / f"{stem}-3d-{v}.png"))
        await b.close()
    srv.shutdown()
    (REPO / "tools/pcb/_render.html").unlink()


def main(pcb, out_dir):
    pcb, out_dir = REPO / pcb, pathlib.Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp())
    tmp = work / pcb.name
    txt = re.sub(r"\$\{KICAD[67]_3DMODEL_DIR\}", str(MODELS), pcb.read_text()).replace('.wrl"', '.step"')
    tmp.write_text(txt)
    for f in pcb.parent.glob("*.kicad_pro"):
        (work / f.name).write_text(f.read_text())
    env = envelopes(tmp, work)
    step = work / (pcb.stem + ".step")
    subprocess.run(["kicad-cli", "pcb", "export", "step", "-f", "-o", str(step), str(tmp)], check=True, capture_output=True)
    glb = REPO / "tools/pcb" / (pcb.stem + "_render.glb")
    step_to_glb(step, glb)
    asyncio.run(shoot(glb.relative_to(REPO), out_dir, pcb.stem))
    glb.unlink(missing_ok=True)
    print(f"{pcb.stem}: 3D renders in {out_dir} ({len(env)} footprint types drawn as envelope boxes: {', '.join(sorted(env))})")
    return env


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
