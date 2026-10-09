# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3
# SPDX-License-Identifier: MIT
"""Common end of every board script: placement check, autoroute, zone fill, save, DRC, summary."""
import json
import pathlib
import sys

from common import REPO

G3 = REPO / "review/G3"


def finish(L, passes=100, route=True, timeout=5400, attempts=1, before_fill=None, plane_zone=None, island=None):
    bad, outside = L.overlaps()
    if bad or outside:
        print(f"{L.name}: courtyard overlaps {bad}; outside the outline {outside}")
        if bad:
            raise SystemExit(f"{L.name}: fix placement first")
    if route:
        L.autoroute(passes=passes, timeout=timeout, attempts=attempts)
    if before_fill:
        before_fill(L)
    L.add_late_zones()
    L.fill()
    L.save()
    (G3 / "drc").mkdir(parents=True, exist_ok=True)
    if plane_zone is not None and "--no-route" not in sys.argv:
        # connections Freerouting left open: the grid finisher (tools/pcb/finisher.py) routes them on the saved board
        from finisher import finish_open, clear_islands
        log = lambda m: (print(m, flush=True), L.log.append(m))
        if island is not None:
            clear_islands(L.out, island, log=log)
        finish_open(L, G3 / "drc" / f"{L.name}.rpt", plane_zone=plane_zone, log=log, rip_rounds=(2,))
        tidy(L, plane_zone, log)
    counts, _ = L.drc(G3 / "drc" / f"{L.name}.rpt")
    summary = dict(status="DRAFT - UNVERIFIED - requires human review at Gate G3", board=L.name, pcb=str(L.out.relative_to(REPO)), footprints=len(L.fps), nets=len(L.nets),
                   drc=counts, autorouted_nets=L.routed_nets, notes=L.log)
    (G3 / "drc" / f"{L.name}.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"{L.name}: {len(L.fps)} footprints, DRC {counts}, {len(L.routed_nets)} nets routed by Freerouting")
    return summary


def tidy(L, plane_zone, log):
    """Last pass: delete tracks KiCad flags for clearance, one more finisher round for what that opens, then delete
    dangling stubs."""
    from finisher import finish_open, remove_violators, remove_dangling
    rpt = G3 / "drc" / f"{L.name}.rpt"
    L.drc(rpt)
    if remove_violators(L.out, rpt, log=log):
        finish_open(L, rpt, plane_zone=plane_zone, log=log, rounds=1)
    if "--keep-dangling" not in sys.argv:
        remove_dangling(L.out, log=log)


def refinish(L, plane_zone, island=None):
    """Run only the finisher again on the board already saved by the script (python3 tools/pcb/<board>.py --finish-only)."""
    import pcbnew
    from finisher import finish_open
    j = G3 / "drc" / f"{L.name}.json"
    old = json.loads(j.read_text()) if j.exists() else {}
    L.log = list(old.get("notes", []))
    log = lambda m: (print(m, flush=True), L.log.append(m))
    if island is not None:
        from finisher import clear_islands
        clear_islands(L.out, island, log=log)
    if "--tidy-only" not in sys.argv:
        finish_open(L, G3 / "drc" / f"{L.name}.rpt", plane_zone=plane_zone, log=log, rip_rounds=(2,))
    tidy(L, plane_zone, log)
    counts, _ = L.drc(G3 / "drc" / f"{L.name}.rpt")
    b = pcbnew.LoadBoard(str(L.out))
    nets = sorted({t.GetNetname() for t in b.GetTracks() if t.GetNetname()})
    summary = dict(status="DRAFT - UNVERIFIED - requires human review at Gate G3", board=L.name, pcb=str(L.out.relative_to(REPO)), footprints=len(L.fps), nets=len(L.nets),
                   drc=counts, autorouted_nets=nets, notes=L.log)
    j.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"{L.name}: DRC {counts}")
    return summary
