# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Layout pipeline shared by every MicroScout board (KiCad 7 pcbnew + Freerouting).

    board = Layout("tof-side", netlist, out_pcb, layers=2, thickness=0.8)
    board.outline(poly); board.rules(...); board.place(...); board.zone(...)
    board.autoroute(); board.fill(); board.drc(); board.save()

Routing: the board is exported as a Specctra DSN, routed by Freerouting (headless, Java) and the
session file is imported back. Every net Freerouting routed is listed for the G3 review.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

import pcbnew

from common import MM, V, mm, build_from_netlist, add_outline, add_npth, courtyard, REPO

FREEROUTING = pathlib.Path(os.environ.get("FREEROUTING_JAR", "/home/claude/tools-ext/fr.jar"))

# JLCPCB published capabilities (seen 2026; re-check at G4): 0.09 mm track/space on 1 oz outer layers,
# 0.3 mm minimum mechanical via drill at the standard price. The rules below stay above those.
JLC = dict(track=0.1, clearance=0.1, via_d=0.45, via_drill=0.25, min_drill=0.2, edge=0.25, hole_to_hole=0.25)
# min_drill 0.2 mm: only the ESP32 module footprint's own thermal vias use it. Whether JLCPCB's standard 4-layer price covers 0.2 mm holes is UNCONFIRMED (check at G4).


class Layout:
    def __init__(self, name, netlist, out_pcb, layers=4, thickness=1.0, fp_override=None, org=(150.0, 100.0)):
        self.name = name
        self.org = org          # board centre on the KiCad page; every coordinate below is relative to it
        self.out = pathlib.Path(out_pcb)
        self.board = pcbnew.BOARD()
        self.board.SetCopperLayerCount(layers)
        self.layers = layers
        self.ds = self.board.GetDesignSettings()
        self.ds.SetBoardThickness(MM(thickness))
        self.fps, self.comps, self.nets = build_from_netlist(self.board, netlist, fp_override)
        self.classes = {}
        self.log = []
        self.routed_nets = []

    # -------------------------------------------------------------- rules
    def rules(self, classes, default=None):
        """classes: {name: dict(track, clearance, via_d, via_drill, nets=[regex...])}."""
        ds = self.ds
        ds.m_MinClearance = MM(JLC["clearance"])
        ds.m_TrackMinWidth = MM(JLC["track"])
        ds.m_ViasMinSize = MM(JLC["via_d"])
        ds.m_MinThroughDrill = MM(JLC["min_drill"])
        ds.m_CopperEdgeClearance = MM(JLC["edge"])
        ds.m_HoleToHoleMin = MM(JLC["hole_to_hole"])
        ds.m_HoleClearance = MM(0.2)
        d = default or dict(track=0.127, clearance=0.127, via_d=0.5, via_drill=0.3)
        self.default_rule = d
        dc = ds.m_NetSettings.m_DefaultNetClass
        dc.SetTrackWidth(MM(d["track"])); dc.SetClearance(MM(d["clearance"]))
        dc.SetViaDiameter(MM(d["via_d"])); dc.SetViaDrill(MM(d["via_drill"]))
        ns = ds.m_NetSettings.m_NetClasses
        for cname, c in classes.items():
            nc = pcbnew.NETCLASS(cname)
            nc.SetTrackWidth(MM(c["track"])); nc.SetClearance(MM(c["clearance"]))
            nc.SetViaDiameter(MM(c.get("via_d", d["via_d"]))); nc.SetViaDrill(MM(c.get("via_drill", d["via_drill"])))
            if "dp_width" in c:
                nc.SetDiffPairWidth(MM(c["dp_width"])); nc.SetDiffPairGap(MM(c["dp_gap"]))
            ns[cname] = nc
            self.classes[cname] = (nc, [re.compile(p) for p in c["nets"]], c)
        for net in self.board.GetNetInfo().NetsByName().values():
            n = net.GetNetname()
            for cname, (nc, pats, _) in self.classes.items():
                if any(p.fullmatch(n) for p in pats):
                    net.SetNetClass(nc)
                    break

    # -------------------------------------------------------------- geometry
    def P(self, poly):
        from shapely.affinity import translate
        return translate(poly, self.org[0], self.org[1])

    def outline(self, poly, holes=()):
        self.local = poly
        self.poly = self.P(poly)
        add_outline(self.board, self.poly)
        for i, (x, y, d) in enumerate(holes):
            add_npth(self.board, x + self.org[0], y + self.org[1], d, ref=f"H{i + 1}")
        # Freerouting does not know KiCad's copper-to-edge rule: _patch_dsn shrinks its routing boundary instead.
        cu = pcbnew.LSET.AllCuMask(self.layers)
        for (x, y, d) in holes:                       # and keep copper off the mounting holes and grommets
            from shapely.geometry import Point
            self.keepout(cu, Point(x, y).buffer(d / 2 + 0.6, 24), tracks=True, vias=True, pads=False, pours=True, name="mounting hole")

    def place(self, ref, x, y, rot=0.0, back=False):
        fp = self.fps[ref]
        if back and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), False)
        if not back and fp.IsFlipped():
            fp.Flip(fp.GetPosition(), False)
        fp.SetPosition(V(x + self.org[0], y + self.org[1]))
        fp.SetOrientationDegrees(rot)
        return fp

    def zone(self, net, layer, poly, clearance=0.2, min_width=0.15, priority=0, thermal_gap=0.25, spoke=0.3, solid=False, name=None, late=False):
        """late=True: added only after autorouting (a pour, not a routing plane)."""
        if late:
            self.late_zones = getattr(self, 'late_zones', []) + [dict(net=net, layer=layer, poly=poly, clearance=clearance, min_width=min_width, priority=priority, thermal_gap=thermal_gap, spoke=spoke, solid=solid, name=name)]
            return None
        z = pcbnew.ZONE(self.board)
        z.SetLayer(layer)
        if net:
            z.SetNetCode(self.board.GetNetInfo().GetNetItem(net).GetNetCode())
        ol = z.Outline()
        ol.NewOutline()
        for x, y in list(self.P(poly).exterior.coords)[:-1]:
            ol.Append(MM(x), MM(y))
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(min_width))
        z.SetThermalReliefGap(MM(thermal_gap))
        z.SetThermalReliefSpokeWidth(MM(spoke))
        z.SetAssignedPriority(priority)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        if name:
            z.SetZoneName(name)
        self.board.Add(z)
        return z

    def keepout(self, layer_set, poly, tracks=True, vias=True, pads=False, pours=True, name="keepout"):
        z = pcbnew.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetLayerSet(layer_set)
        z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowPads(pads)
        z.SetDoNotAllowCopperPour(pours); z.SetDoNotAllowFootprints(False)
        ol = z.Outline(); ol.NewOutline()
        pp = self.P(poly)
        for x, y in list(pp.exterior.coords)[:-1]:
            ol.Append(MM(x), MM(y))
        for k, ring in enumerate(pp.interiors):
            ol.NewHole()
            for x, y in list(ring.coords)[:-1]:
                ol.Append(MM(x), MM(y), -1, k)
        z.SetZoneName(name)
        self.board.Add(z)
        return z

    def track(self, net, pts, width, layer=pcbnew.F_Cu):
        code = self.board.GetNetInfo().GetNetItem(net).GetNetCode()
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
            t = pcbnew.PCB_TRACK(self.board)
            ox, oy = self.org
            t.SetStart(V(x1 + ox, y1 + oy)); t.SetEnd(V(x2 + ox, y2 + oy)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNetCode(code)
            self.board.Add(t)

    def via(self, net, x, y, d=0.5, drill=0.3):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(x + self.org[0], y + self.org[1])); v.SetDrill(MM(drill)); v.SetWidth(MM(d))
        v.SetNetCode(self.board.GetNetInfo().GetNetItem(net).GetNetCode())
        self.board.Add(v)
        return v

    # -------------------------------------------------------------- checks before routing
    def overlaps(self):
        """Courtyard overlaps between footprints on the same side (should be empty)."""
        items = []
        for ref, fp in self.fps.items():
            side = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
            items.append((ref, fp.IsFlipped(), courtyard(fp, side)))
        bad = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a[1] == b[1] and a[2].intersection(b[2]).area > 0.01:
                    bad.append((a[0], b[0], round(a[2].intersection(b[2]).area, 2)))
        outside = [r for r, s, c in items if not self.poly.buffer(0.01).contains(c)]
        return bad, outside

    # -------------------------------------------------------------- routing
    STRATEGIES = [("PRIORITIZED", "GREEDY"), ("RANDOM", "GLOBAL"), ("SEQUENTIAL", "HYBRID"), ("RANDOM", "GREEDY"),
                  ("PRIORITIZED", "GLOBAL"), ("RANDOM", "HYBRID")]

    def autoroute(self, passes=40, timeout=900, keep=None, attempts=4, only=None, pin_ok=None):
        """Freerouting sometimes stops with a few connections open. Each attempt rips up its own copper and
        routes again with a different optimisation strategy; the attempt with the fewest open connections is kept."""
        fixed = {t.m_Uuid.AsString() for t in self.board.GetTracks()}      # hand-placed copper stays
        best = None
        for k in range(attempts):
            self._clear_autorouted(fixed)
            try:
                self._autoroute_once(passes, timeout, keep, self.STRATEGIES[k % len(self.STRATEGIES)], only, pin_ok)
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                self.log.append(f"freerouting attempt {k + 1} failed: {str(e)[:200]}")
                continue
            n = self.unrouted()
            self.log.append(f"freerouting attempt {k + 1} ({self.STRATEGIES[k % len(self.STRATEGIES)]}): {n} connections open")
            if best is None or n < best[0]:
                best = (n, self._snapshot(fixed))
            if not n:
                break
        self._clear_autorouted(fixed)
        if best:
            self._restore(best[1])
            self.log.append(f"kept the attempt with {best[0]} open connections")
        self.routed_nets = sorted({t.GetNetname() for t in self.board.GetTracks() if t.m_Uuid.AsString() not in fixed and t.GetNetname()})

    def _clear_autorouted(self, fixed):
        for t in list(self.board.GetTracks()):
            if t.m_Uuid.AsString() not in fixed:
                self.board.Remove(t)

    def _snapshot(self, fixed):
        out = []
        for t in self.board.GetTracks():
            if t.m_Uuid.AsString() in fixed:
                continue
            if t.GetClass() == "PCB_VIA":
                out.append(("via", t.GetNetCode(), t.GetPosition().x, t.GetPosition().y, t.GetWidth(), t.GetDrillValue()))
            else:
                out.append(("trk", t.GetNetCode(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetWidth(), t.GetLayer()))
        return out

    def _restore(self, snap):
        for it in snap:
            if it[0] == "via":
                v = pcbnew.PCB_VIA(self.board); v.SetNetCode(it[1]); v.SetPosition(pcbnew.VECTOR2I(it[2], it[3]))
                v.SetWidth(it[4]); v.SetDrill(it[5]); self.board.Add(v)
            else:
                t = pcbnew.PCB_TRACK(self.board); t.SetNetCode(it[1]); t.SetStart(pcbnew.VECTOR2I(it[2], it[3]))
                t.SetEnd(pcbnew.VECTOR2I(it[4], it[5])); t.SetWidth(it[6]); t.SetLayer(it[7]); self.board.Add(t)

    def continue_route(self, passes=20, timeout=5400):
        """Hand the current (unlocked) routing back to Freerouting for more passes; keep it only if it is better."""
        before = self.unrouted()
        fixed = {t.m_Uuid.AsString() for t in self.board.GetTracks() if t.IsLocked()}
        snap = self._snapshot(fixed)
        work = pathlib.Path(tempfile.mkdtemp(prefix=f"fr-{self.name}-cont-"))
        dsn, ses = work / f"{self.name}.dsn", work / f"{self.name}.ses"
        self._export_dsn(dsn)
        self._patch_dsn(dsn)
        try:
            self._run_freerouting(work, dsn, ses, passes, timeout, ("PRIORITIZED", "GREEDY"))
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            self.log.append(f"continue_route failed: {str(e)[:200]}")
            return before
        self._clear_autorouted(fixed)
        self._import_ses(ses)
        after = self.unrouted()
        if after > before:
            self._clear_autorouted(fixed); self._restore(snap)
            self.log.append(f"continue_route: {after} open is worse than {before}; kept the earlier routing")
            return before
        self.log.append(f"continue_route: {before} -> {after} open connections")
        return after

    def clear_plane_layers(self, layers, name="no tracks on the GND plane"):
        """Freerouting needs plane layers to be ordinary signal layers, or it will not connect pins to the plane.
        So it may also run a few tracks on them. This removes those tracks and puts a no-tracks rule area on the
        layers; the finisher (finisher.py) then routes the connections again on the other layers."""
        n = 0
        for t in list(self.board.GetTracks()):
            if t.GetClass() != "PCB_VIA" and t.GetLayer() in layers:
                self.board.Remove(t)
                n += 1
        ls = pcbnew.LSET()
        for l in layers:
            ls.AddLayer(l)
        self.keepout(ls, self.local, tracks=True, vias=False, pours=False, name=name)
        self.log.append(f"removed {n} track segments that Freerouting put on the plane layers")
        return n

    def track_ids(self):
        return {t.m_Uuid.AsString() for t in self.board.GetTracks()}

    def copy_rotated(self, ids, netmap):
        """Adds a copy of the given tracks and vias rotated 180 degrees about the board origin, with nets renamed by
        netmap(name). Used for channels whose parts are 180-degree copies of an already routed channel."""
        ni = self.board.GetNetInfo()
        ox, oy = MM(self.org[0]), MM(self.org[1])
        rot = lambda p: pcbnew.VECTOR2I(2 * ox - p.x, 2 * oy - p.y)
        n = 0
        for t in list(self.board.GetTracks()):
            if t.m_Uuid.AsString() not in ids:
                continue
            item = ni.GetNetItem(netmap(t.GetNetname()))
            if item is None:
                raise KeyError(netmap(t.GetNetname()))
            if t.GetClass() == "PCB_VIA":
                v = pcbnew.PCB_VIA(self.board); v.SetPosition(rot(t.GetPosition())); v.SetWidth(t.GetWidth())
                v.SetDrill(t.GetDrillValue()); v.SetNetCode(item.GetNetCode()); v.SetLocked(True); self.board.Add(v)
            else:
                c = pcbnew.PCB_TRACK(self.board); c.SetStart(rot(t.GetStart())); c.SetEnd(rot(t.GetEnd()))
                c.SetWidth(t.GetWidth()); c.SetLayer(t.GetLayer()); c.SetNetCode(item.GetNetCode()); c.SetLocked(True)
                self.board.Add(c)
            n += 1
        self.log.append(f"copied {n} tracks and vias by 180-degree rotation")
        return n

    def route_in_groups(self, groups, passes=20, timeout=5400):
        """Route net groups one after another; each group's copper is locked ('fix' in the DSN) before the next.
        groups: list of (label, predicate(netname) -> bool)."""
        for label, pred in groups:
            self.autoroute(passes=passes, timeout=timeout, attempts=1, only=pred)
            for t in self.board.GetTracks():
                t.SetLocked(True)
            self.log.append(f"group {label}: {self.unrouted()} connections open on the board after it")
        self.routed_nets = sorted({t.GetNetname() for t in self.board.GetTracks() if t.GetNetname()})

    def _autoroute_once(self, passes=40, timeout=900, keep=None, strategy=("PRIORITIZED", "GREEDY"), only=None, pin_ok=None):
        work = pathlib.Path(tempfile.mkdtemp(prefix=f"fr-{self.name}-"))
        dsn, ses = work / f"{self.name}.dsn", work / f"{self.name}.ses"
        before = {t.GetNetname() for t in self.board.GetTracks()}
        if not self._export_dsn(dsn):
            raise RuntimeError("DSN export failed")
        self._patch_dsn(dsn, only, pin_ok)
        (work / "freerouting.json").write_text(json.dumps({
            "max_passes": passes, "num_threads": 1, "board_update_strategy": strategy[1], "hybrid_ratio": "1:1",
            "item_selection_strategy": strategy[0], "save_intermediate_stages": False,
            "optimization_improvement_threshold": 1e-5, "disable_logging": False, "disable_analytics": True,
            "dialog_confirmation_timeout": 1, "host": "N/A"}))
        r = self._run_freerouting(work, dsn, ses, passes, timeout, strategy, write_cfg=False)
        self._import_ses(ses)
        self.late_zones_pending = True
        after = {t.GetNetname() for t in self.board.GetTracks()}
        self.routed_nets = sorted(n for n in after if n and n not in before) + sorted(n for n in before & after if n)
        if keep:
            shutil.copy(dsn, keep / dsn.name); shutil.copy(ses, keep / ses.name)
        self.log.append(f"freerouting: {r.returncode}, work dir {work}")
        return work

    def _run_freerouting(self, work, dsn, ses, passes, timeout, strategy, write_cfg=True):
        if write_cfg:
            (work / "freerouting.json").write_text(json.dumps({
                "max_passes": passes, "num_threads": 1, "board_update_strategy": strategy[1], "hybrid_ratio": "1:1",
                "item_selection_strategy": strategy[0], "save_intermediate_stages": False,
                "optimization_improvement_threshold": 1e-5, "disable_logging": False, "disable_analytics": True,
                "dialog_confirmation_timeout": 1, "host": "N/A"}))
        cmd = (["xvfb-run", "-a"] if shutil.which("xvfb-run") and not os.environ.get("DISPLAY") else []) + \
            ["java", "-jar", str(FREEROUTING), "-de", str(dsn), "-do", str(ses), "-mp", str(passes)]
        rules = self._rules_file(work, dsn)
        if rules:
            cmd[cmd.index("-do"):cmd.index("-do")] = ["-dr", str(rules)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=work, start_new_session=True)
        try:
            outtxt, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise
        (work / "freerouting.log").write_text(outtxt)
        if not ses.exists():
            raise RuntimeError("Freerouting produced no session file:\n" + outtxt[-3000:])
        return proc

    def _rules_file(self, work, dsn):
        """Freerouting .rules file: plane layers (self.plane_layers) get a 50x trace cost, so the router keeps tracks off
        them but can still drop vias into them. (Making them inactive, or 'power' layers, also stops the plane
        connections: tested on the ESC, 16 GND plane vias -> 2.) Other layers alternate preferred directions."""
        planes = getattr(self, "plane_layers", None)
        if not planes:
            return None
        name = re.search(r'\(pcb ("[^"]*"|\S+)', dsn.read_text()[:400]).group(1)
        rules = []
        k = 0
        for l in range(pcbnew.PCB_LAYER_ID_COUNT):
            if not (pcbnew.IsCopperLayer(l) and self.board.IsLayerEnabled(l)):
                continue
            cost = 50.0 if l in planes else 1.0
            d = "horizontal" if k % 2 == 0 else "vertical"
            k += 1
            rules.append(f"    (layer_rule {self.board.GetLayerName(l)}\n      (active on)\n      (preferred_direction {d})\n"
                         f"      (preferred_direction_trace_costs {cost:.1f})\n      (against_preferred_direction_trace_costs {cost * 2:.1f})\n    )")
        f = work / "planes.rules"
        f.write_text(f"(rules PCB {name}\n  (snap_angle\n    fortyfive_degree\n  )\n  (autoroute_settings\n    (fanout off)\n"
                     "    (autoroute on)\n    (postroute on)\n    (vias on)\n    (via_costs 50)\n    (plane_via_costs 5)\n"
                     "    (start_ripup_costs 100)\n    (start_pass_no 1)\n" + "\n".join(rules) + "\n  )\n)\n")
        return f

    def _export_dsn(self, dsn):
        """DSN export with rounded-rectangle pads written as plain rectangles. KiCad exports a rounded pad as a
        polygon and Freerouting 1.9 often fails to connect to polygon pads (tested on the ESC: whole 3 mm two-pin nets
        left open). The rectangle covers the rounded pad, so clearances stay conservative; the board keeps its pads."""
        changed = []
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetShape() == pcbnew.PAD_SHAPE_ROUNDRECT:
                    changed.append(pad)
                    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        try:
            return pcbnew.ExportSpecctraDSN(self.board, str(dsn))
        finally:
            for pad in changed:
                pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)

    def _patch_dsn(self, dsn, only=None, pin_ok=None):
        """KiCad 7's DSN export puts every net in the default class; rewrite the class list from our rules.
        only(net): route only these nets. pin_ok(net, ref): route only these pins of each net (a net left with
        fewer than two pins keeps one pin, so its existing copper stays attached to a net)."""
        txt = dsn.read_text()
        if pin_ok is not None:
            def filt(m):
                name = m.group(1).strip('"')
                pins = re.findall(r'"[^"]*"|\S+', m.group(2))
                keep = [t for t in pins if pin_ok(name, t.strip('"').rsplit("-", 1)[0])]
                if len(keep) < 2:
                    keep = pins[:1]
                return f"\n    (net {m.group(1)}\n      (pins {' '.join(keep)})\n    )"
            txt = re.sub(r'\n    \(net ("[^"]*"|\S+)\n      \(pins([^)]*)\)\n    \)', filt, txt)
        # Freerouting already keeps its class clearance from the boundary, so shrink by the remainder only.
        inner = self.poly.buffer(-(JLC["edge"] - JLC["clearance"] + 0.03), join_style=2).simplify(0.01)
        pts = " ".join(f"{x * 1000:.0f} {-y * 1000:.0f}" for x, y in inner.exterior.coords)
        txt = re.sub(r"\(boundary\s*\(path pcb 0 [^)]*\)\s*\)", f"(boundary\n      (path pcb 0  {pts})\n    )", txt, count=1)
        i = txt.index("    (class kicad_default")
        j = txt.index("\n  )\n", i)                    # end of the (network ...) block
        nets = [n for n in self.nets]
        if only is not None:
            routed = {t.GetNetname() for t in self.board.GetTracks()}
            planes = {z.GetNetname() for z in self.board.Zones() if not z.GetIsRuleArea()}
            keepn = {n for n in nets if only(n) or n in routed or n in planes}
            def drop(m):
                name = m.group(1).strip('"')
                return m.group(0) if name in keepn else ""
            txt = re.sub(r'\n    \(net ("[^"]*"|\S+)\n      \(pins[^)]*\)\n    \)', drop, txt)
            nets = [n for n in nets if n in keepn]
            i = txt.index("    (class kicad_default")
            j = txt.index("\n  )\n", i)
        def q(n):
            return '"' + n.replace('"', '\\"') + '"' if re.search(r'[\s()"]', n) or n == "" else n
        assigned, blocks = set(), []
        via = re.search(r"\(use_via ([^)]+)\)", txt[i:j]).group(1)
        for cname, (_, pats, c) in self.classes.items():
            members = [n for n in nets if n not in assigned and any(p.fullmatch(n) for p in pats)]
            assigned.update(members)
            if members:
                blocks.append((cname, members, c["track"], c["clearance"]))
        d = self.ds.m_NetSettings.m_DefaultNetClass
        rest = [n for n in nets if n not in assigned]
        blocks.append(("kicad_default", rest, mm(d.GetTrackWidth()), mm(d.GetClearance())))
        out = []
        for cname, members, w, cl in blocks:
            out.append(f'    (class {cname} ' + " ".join(q(n) for n in members) +
                       f"\n      (circuit\n        (use_via {via})\n      )\n      (rule\n        (width {w * 1000:.1f})\n        (clearance {cl * 1000 + 0.1:.1f})\n      )\n    )")
        dsn.write_text(txt[:i] + "\n".join(out) + txt[j:])

    def _import_ses(self, ses):
        """Adds the wires and vias of a Freerouting session file (KiCad 7's Python cannot import SES headless)."""
        import sexpr
        root = sexpr.parse(ses.read_text())[0]
        routes = next(c for c in root[1:] if isinstance(c, list) and c[0] == "routes")
        res = next(c for c in routes[1:] if isinstance(c, list) and c[0] == "resolution")
        scale = 1.0 / (float(res[2]) * 1000.0)            # session units -> mm
        lay = {self.board.GetLayerName(l): l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l)}
        netout = next(c for c in routes[1:] if isinstance(c, list) and c[0] == "network_out")
        ni = self.board.GetNetInfo()
        nt = nv = 0
        for net in netout[1:]:
            if not isinstance(net, list) or net[0] != "net":
                continue
            code = ni.GetNetItem(str(net[1])).GetNetCode()
            for item in net[2:]:
                if item[0] == "wire":
                    path = next(c for c in item[1:] if isinstance(c, list) and c[0] == "path")
                    layer, width = lay[str(path[1])], float(path[2]) * scale
                    pts = [(float(path[k]) * scale, -float(path[k + 1]) * scale) for k in range(3, len(path) - 1, 2)]
                    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                        t = pcbnew.PCB_TRACK(self.board)
                        t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNetCode(code)
                        self.board.Add(t); nt += 1
                elif item[0] == "via":
                    m = re.search(r"_(\d+):(\d+)_um", str(item[1]))
                    dia, drill = (int(m.group(1)) / 1000, int(m.group(2)) / 1000) if m else (0.5, 0.3)
                    v = pcbnew.PCB_VIA(self.board)
                    v.SetPosition(V(float(item[2]) * scale, -float(item[3]) * scale))
                    v.SetWidth(MM(dia)); v.SetDrill(MM(drill)); v.SetNetCode(code)
                    self.board.Add(v); nv += 1
        self.log.append(f"imported {nt} track segments and {nv} vias from {ses.name}")

    # -------------------------------------------------------------- finish
    def stitch(self, net, region, pitch=1.0, d=None, drill=None, clearance=0.2, max_vias=200):
        """Fill a region (board-relative shapely polygon) with through vias of `net` wherever they clear
        every other net's pads, tracks and vias by `clearance`. Returns the number of vias added."""
        from shapely.geometry import Point, LineString
        from shapely.ops import unary_union
        d = d or JLC["via_d"]; drill = drill or JLC["via_drill"]
        ox, oy = self.org
        obst = []
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() == net:
                    continue
                bb = pad.GetBoundingBox()
                obst.append(Point(pcbnew.ToMM(pad.GetPosition().x) - ox, pcbnew.ToMM(pad.GetPosition().y) - oy)
                            .buffer(max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2))
        for t in self.board.GetTracks():
            if t.GetNetname() == net:
                continue
            if t.GetClass() == "PCB_VIA":
                obst.append(Point(pcbnew.ToMM(t.GetPosition().x) - ox, pcbnew.ToMM(t.GetPosition().y) - oy).buffer(pcbnew.ToMM(t.GetWidth()) / 2))
            else:
                obst.append(LineString([(pcbnew.ToMM(t.GetStart().x) - ox, pcbnew.ToMM(t.GetStart().y) - oy),
                                        (pcbnew.ToMM(t.GetEnd().x) - ox, pcbnew.ToMM(t.GetEnd().y) - oy)]).buffer(pcbnew.ToMM(t.GetWidth()) / 2))
        for fp in self.board.GetFootprints():          # mounting holes
            if fp.GetReference().startswith("H"):
                obst.append(Point(pcbnew.ToMM(fp.GetPosition().x) - ox, pcbnew.ToMM(fp.GetPosition().y) - oy).buffer(2.2))
        bad = unary_union(obst).buffer(d / 2 + clearance) if obst else None
        ok = region.buffer(-d / 2 - 0.1)
        x0, y0, x1, y1 = ok.bounds
        n, placed = 0, []
        y = y0
        while y <= y1 and n < max_vias:
            x = x0
            while x <= x1 and n < max_vias:
                p = Point(x, y)
                if ok.contains(p) and (bad is None or not bad.contains(p)) and all(p.distance(q) >= d + 0.2 for q in placed):
                    self.via(net, x, y, d, drill); placed.append(p); n += 1
                x += pitch
            y += pitch
        self.log.append(f"stitched {n} {net} vias")
        return n

    def add_late_zones(self):
        for kw in getattr(self, "late_zones", []):
            kw = dict(kw, name="late " + (kw.get("name") or kw["net"]))     # the finisher ignores late pours
            self.zone(**kw)
        self.late_zones = []

    def fill(self):
        """Zone filling is done after saving (the filler needs a board loaded from disk with its project)."""
        self.want_fill = True

    def unrouted(self):
        self.board.BuildConnectivity()
        c = self.board.GetConnectivity()
        return c.GetUnconnectedCount(True) if hasattr(c, "GetUnconnectedCount") else None

    def save(self):
        self.out.parent.mkdir(parents=True, exist_ok=True)
        pro = self.out.with_suffix(".kicad_pro")
        keep = json.loads(pro.read_text()) if pro.exists() else None
        pcbnew.SaveBoard(str(self.out), self.board)
        if keep is not None:                      # merge the board settings into the schematic's project file
            new = json.loads(pro.read_text())
            keep["board"] = new["board"]
            keep["net_settings"] = new["net_settings"]
            pats = []
            for cname, (_, ps, c) in self.classes.items():
                for p in c["nets"]:
                    pats.append({"netclass": cname, "pattern": p})
            keep["net_settings"]["netclass_patterns"] = pats
            pro.write_text(json.dumps(keep, indent=2) + "\n")
        if getattr(self, "want_fill", True):
            b = pcbnew.LoadBoard(str(self.out))
            pcbnew.ZONE_FILLER(b).Fill(b.Zones())
            pcbnew.SaveBoard(str(self.out), b)

    def drc(self, report):
        """Re-load the saved board with its project (so net classes apply) and write KiCad's DRC report."""
        b = pcbnew.LoadBoard(str(self.out))
        pcbnew.WriteDRCReport(b, str(report), pcbnew.EDA_UNITS_MILLIMETRES, True)
        txt = pathlib.Path(report).read_text()
        pathlib.Path(report).write_text("STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3\n" + txt)
        counts = {k: int(v) for v, k in re.findall(r"\*\* Found (\d+) (DRC violations|unconnected pads|Footprint errors)", txt)}
        return counts, txt
