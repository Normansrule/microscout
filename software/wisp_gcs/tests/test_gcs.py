# SPDX-License-Identifier: MIT
"""Unit tests for the Wisp ground-station pieces. No simulator needed; see test_sitl.py for the one that is."""
import json
import math
import pathlib
import types

import numpy as np
import pytest

from wisp_gcs import bridge
from wisp_gcs.fit import Biquad, closed_loop, fit, margins
from wisp_gcs.replay import build, load
from wisp_gcs.steptest import IGNORE_ATTITUDE, StepPlan, score
from wisp_gcs.telemetry import Dejitter, VehicleState

ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA = ROOT / "docs/control-lab/data/sitl-roll-steps.json"
REC = ROOT / "review/P1/sitl/recording.jsonl.gz"
SUMMARY = ROOT / "review/P1/sitl/session.json"


# ---- telemetry -------------------------------------------------------------------------------------------
def test_heartbeat_mode_and_arming():
    s = VehicleState()
    s.update({"mavpackettype": "HEARTBEAT", "type": 2, "custom_mode": 4, "base_mode": 128 | 1}, 1.0)
    assert (s.mode, s.armed) == ("GUIDED", True)
    s.update({"mavpackettype": "HEARTBEAT", "type": 6, "custom_mode": 0, "base_mode": 0}, 2.0)   # a GCS
    assert (s.mode, s.armed) == ("GUIDED", True)


def test_pid_tuning_rate_axes_are_converted_to_degrees():
    s = VehicleState()
    p = s.update({"mavpackettype": "PID_TUNING", "axis": 1, "desired": math.radians(90), "achieved": 1.0,
                  "FF": 0.0, "P": 0.03, "I": 0.001, "D": 0.02}, 3.0)
    assert p.axis == "roll" and p.des == pytest.approx(90) and p.ach == pytest.approx(57.2958, rel=1e-4)
    z = s.update({"mavpackettype": "PID_TUNING", "axis": 4, "desired": 2.0, "achieved": 1.5,
                  "FF": 0, "P": 0, "I": 0, "D": 0}, 3.1)
    assert z.axis == "accz" and z.des == 2.0          # acceleration loop: not an angle, left alone


def test_battery_unknowns_are_none():
    s = VehicleState()
    s.update({"mavpackettype": "SYS_STATUS", "voltage_battery": 12600, "current_battery": -1,
              "battery_remaining": -1}, 0)
    assert s.batt == {"v": 12.6, "a": None, "pct": None}


def test_dejitter_spreads_a_burst_and_never_runs_ahead():
    d, p = Dejitter(), 0.0116
    true = [k * p for k in range(40)]
    arrive = [true[16] if 10 <= k < 16 else t for k, t in enumerate(true)]
    est = [d(a) for a in arrive]
    assert max(abs(e - t) for e, t in zip(est, true)) < 0.005           # was up to 70 ms
    assert all(e <= a + 1e-12 for e, a in zip(est, arrive))
    assert all(b > a for a, b in zip(est, est[1:]))


# ---- step test ---------------------------------------------------------------------------------------------
def test_step_plan_limits():
    with pytest.raises(ValueError):
        StepPlan(axis="roll", amp=200, dur=0.4)        # 80 degrees of tilt
    with pytest.raises(ValueError):
        StepPlan(axis="throttle")
    StepPlan(axis="yaw", amp=200, dur=0.4)             # yaw does not tilt


def test_step_plan_phases():
    p = StepPlan(axis="pitch", amp=90, dur=0.4)
    assert p.command(0.1, 30)["phase"] == "level"
    c = p.command(0.6, 30)
    assert c["phase"] == "step" and c["type_mask"] == IGNORE_ATTITUDE
    assert c["rates"] == [0.0, pytest.approx(math.radians(90)), 0.0]
    assert p.command(1.0, 30)["phase"] == "zero"
    lv = p.command(2.0, 30)
    assert lv["phase"] == "level" and lv["q"][3] == pytest.approx(math.sin(math.radians(15)))


def test_score_on_an_ideal_first_order_response():
    t = [k * 0.001 for k in range(600)]
    ach = [90 * (1 - math.exp(-x / 0.05)) if x < 0.4 else 0 for x in t]
    des = [90 if x < 0.4 else 0 for x in t]
    s = score(t, des, ach, 0.0, 90)
    assert s["rise_s"] == pytest.approx(0.05 * math.log(9), abs=0.002)     # 10-90 % of a first-order lag
    assert s["overshoot_pct"] == 0.0


# ---- model -------------------------------------------------------------------------------------------------
def test_biquad_has_unity_dc_gain_and_cuts_at_cutoff():
    f = Biquad(400, 20, 0.0)
    y = [f(1.0) for _ in range(400)]
    assert y[-1] == pytest.approx(1.0, abs=1e-9)
    f = Biquad(400, 20, 0.0)
    out = [f(math.sin(2 * math.pi * 20 * k / 400)) for k in range(800)]
    assert max(out[400:]) == pytest.approx(math.sqrt(0.5), abs=0.03)       # -3 dB at the cutoff


def test_fit_recovers_a_known_plant():
    true = {"b": 300.0, "a": 2.0, "tau": 0.02, "td": 0.004, "gyro_hz": 20.0}
    t = np.arange(-0.3, 1.2, 0.0116)
    des = np.radians(np.clip(1100 * t, 0, 90) * (t < 0.4) + np.clip(90 - 1100 * (t - 0.4), 0, 90) * (t >= 0.4))
    segs = []
    for k in (0.5, 1.0):
        g = {"P": 0.135 * k, "I": 0.135 * k, "D": 0.0036 * k, "FLTD": 20.0}
        tt, wf, _ = closed_loop(t, des, g, true)
        segs.append({"t": t, "des": des, "w": np.interp(t, tt, wf), "i0": 0.0, "gains": g})
    got = fit(segs)
    assert got["b"] == pytest.approx(300, rel=0.03)
    assert got["r2"] > 0.999


def test_margins_fall_as_gain_rises():
    plant = {"b": 280.5, "a": 2.33, "tau": 0.0001, "td": 0.003, "gyro_hz": 20}
    pm = [margins({"P": 0.135 * k, "I": 0.135 * k, "D": 0.0036 * k, "FLTD": 20}, plant)["pm_deg"] for k in (0.5, 1, 2)]
    assert pm[0] > pm[1] > 0 > pm[2]


# ---- the recorded SITL session -----------------------------------------------------------------------------
def test_replay_file_rebuilds_from_the_committed_recording():
    data = build(load(REC), json.loads(SUMMARY.read_text()))
    committed = json.loads(DATA.read_text())
    for k in ("b", "a", "td"):
        assert data["plant"][k] == pytest.approx(committed["plant"][k], rel=1e-3, abs=1e-4)
    assert [s["name"] for s in data["steps"]] == [s["name"] for s in committed["steps"]]


def test_recorded_session_findings_hold():
    d = json.loads(DATA.read_text())
    by = {s["name"]: s for s in d["steps"]}
    assert by["half"]["prediction"]["rms_dps"] < 3
    ho = d["holdout"]["steps"]                               # fitted on the default step only
    assert ho["half"]["rms_dps"] < 2 and ho["double"]["diverges"] and ho["double"]["margins"]["pm_deg"] < 0
    assert by["double"]["margins"]["pm_deg"] < 0 and by["double"]["prediction"]["diverges"]
    assert by["default"]["margins"]["pm_deg"] > 0
    assert d["safety"] == {"refused_big_change": True, "refused_non_tuning_param": True,
                           "landed_and_disarmed": True}
    assert any("aborted" in r for r in d["stop_test"]["results"]) and d["stop_test"]["mode_after"] == "BRAKE"


# ---- bridge safety rules -------------------------------------------------------------------------------------
@pytest.mark.parametrize("name,ok", [
    ("ATC_RAT_RLL_P", True), ("ATC_RAT_YAW_FLTE", True), ("PSC_VELXY_P", True), ("GCS_PID_MASK", True),
    ("ARMING_CHECK", False), ("FS_THR_ENABLE", False), ("ATC_RAT_RLL_P2", False), ("SERIAL0_BAUD", False),
])
def test_param_allowlist(name, ok):
    assert bool(bridge.PARAM_ALLOW.match(name)) is ok


class _Conn:
    def respond(self, status, text):
        return ("respond", int(status), text)


def _req(path, upgrade=""):
    return types.SimpleNamespace(path=path, headers={"Upgrade": upgrade} if upgrade else {})


def test_static_server_stays_inside_docs():
    assert bridge.static_files(_Conn(), _req("/../README.md"))[1] == 404
    assert bridge.static_files(_Conn(), _req("/%2e%2e/README.md"))[1] == 404
    assert bridge.static_files(_Conn(), _req("/control-lab/../../software/wisp_gcs/bridge.py"))[1] == 404
    r = bridge.static_files(_Conn(), _req("/control-lab/"))
    assert r.status_code == 200 and b"Wisp Control Lab" in r.body
    assert bridge.static_files(_Conn(), _req("/ws", upgrade="websocket")) is None


def test_origin_allowlist_rejects_other_sites():
    import re
    def allowed(o):
        return any((p.match(o) if isinstance(p, re.Pattern) else p == o) for p in bridge.ALLOWED_ORIGINS if o is not None)
    assert allowed("http://127.0.0.1:8765") and allowed("http://localhost:5173")
    assert allowed("https://normansrule.github.io")
    assert not allowed("https://evil.example") and not allowed("http://127.0.0.1.evil.example")
