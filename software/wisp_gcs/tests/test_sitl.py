# SPDX-License-Identifier: MIT
"""End-to-end against ArduCopter SITL (software in the loop): bridge plus the scripted session.

Skipped unless WISP_ARDUPILOT points at an ArduPilot tree with SITL built (review/P1/README.md, setup). Takes
about two minutes: take-off, three step tests, a stop in the middle of a step, refused parameter changes, land.
"""
import asyncio
import os
import pathlib
import subprocess
import sys
import time

import pytest

ARDUPILOT = os.environ.get("WISP_ARDUPILOT")
pytestmark = pytest.mark.skipif(not ARDUPILOT, reason="set WISP_ARDUPILOT to an ArduPilot tree with SITL built")


def test_full_session(tmp_path):
    from wisp_gcs.session import run
    sw = pathlib.Path(__file__).resolve().parents[2]
    port = 8799
    proc = subprocess.Popen([sys.executable, "-m", "wisp_gcs.bridge", "--sitl", ARDUPILOT, "--instance", "7",
                             "--port", str(port), "--workdir", str(tmp_path / "sitl")],
                            cwd=sw, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        t0 = time.time()
        for line in proc.stdout:
            if "Control Lab at" in line:
                break
            if time.time() - t0 > 90 or "busy" in line or "Traceback" in line:
                pytest.fail(line)
        summary = asyncio.run(run(f"ws://127.0.0.1:{port}/ws", str(tmp_path / "session.json")))
    finally:
        proc.terminate()
        proc.wait(10)
    steps = {s["name"]: s["score"] for s in summary["steps"]}
    assert 0.05 < steps["default"]["rise_s"] < 0.15
    assert steps["half"]["rise_s"] > steps["default"]["rise_s"]      # less gain, slower
    # Double gains are past the stability limit: SITL breaks into an oscillation whose size changes from run to
    # run (6-64 % overshoot seen), so only its existence is checked, not its size.
    assert steps["double"]["settle_s"] is None or steps["double"]["overshoot_pct"] > steps["default"]["overshoot_pct"]
    assert any("aborted" in r for r in summary["stop_test"]["results"])
    assert summary["stop_test"]["abort_reply_s"] < 0.5 and summary["stop_test"]["mode_after"] == "BRAKE"
    assert summary["refused_big_change"] and summary["refused_non_tuning_param"]
    assert summary["landed_and_disarmed"]
