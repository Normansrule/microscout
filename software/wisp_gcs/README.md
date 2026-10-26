# Wisp ground station (Phase 1)

> **STATUS: Phase 1 draft, simulation only.** Run against ArduCopter 4.7.2 SITL (software in the loop) on Ubuntu
> 24.04 in a cloud container. Never connected to a real drone; not for one until the Phase 3 review.

The bridge between a drone speaking MAVLink (Micro Air Vehicle Link) and the Wisp apps, which read JSON
(JavaScript Object Notation) over a WebSocket, plus the tools that
record, score and model a rate-loop step test.

| File | What it does |
|---|---|
| `bridge.py` | MAVLink on one side, WebSocket JSON on the other. Serves the Control Lab, measures latency, runs commands with safety rules |
| `telemetry.py` | MAVLink messages to the JSON the apps read; timestamps for PID (proportional-integral-derivative) samples (`Dejitter`) |
| `steptest.py` | The rate-loop step test: what to command in Guided mode, and how to score the response |
| `fit.py` | The rate-loop model (PID, delay, motor lag, airframe, gyro filter), its stability margins, and a plant fit |
| `session.py` | A scripted session through the bridge: take-off, three step tests, a stop mid-step, refused changes, land |
| `replay.py` | A recorded session to the file the Control Lab replays (`docs/control-lab/data/`) |
| `make_fixture.py` | Python model outputs the JavaScript model must reproduce (`docs/control-lab/test/`) |

## Ubuntu commands

Build ArduCopter SITL first ([review/P0/sitl.md](../../review/P0/sitl.md), steps 1-3), then:

```bash
sudo apt install -y python3-venv
git clone https://github.com/Normansrule/wisp.git ~/wisp
python3 -m venv ~/venv-wisp && . ~/venv-wisp/bin/activate
pip install -r ~/wisp/software/wisp_gcs/requirements.txt

# start SITL and the bridge together, recording everything it sends to the apps
cd ~/wisp/software
python3 -m wisp_gcs.bridge --sitl ~/ardupilot --record ~/wisp-rec.jsonl
```

Open <http://127.0.0.1:8765/control-lab/> (the bridge serves the page, so it starts in Live SITL). Wait for
10 or so GPS (Global Positioning System) satellites, then **Take off to 10 m**, **Run step test**, move the gains, **Send gains to SITL**, run
another step. **Stop and hover** (or the Escape key) aborts a step test and puts the drone in Brake mode.

In a second terminal, the scripted session and the replay file:

```bash
. ~/venv-wisp/bin/activate && cd ~/wisp/software
python3 -m wisp_gcs.session --out ~/wisp-session.json          # about 90 s; needs the bridge running
# stop the bridge (Ctrl+C), then:
python3 -m wisp_gcs.replay ~/wisp-rec.jsonl ~/wisp-session.json --out ../docs/control-lab/data/sitl-roll-steps.json
```

Tests:

```bash
cd ~/wisp/software/wisp_gcs
pytest -q tests                                       # unit tests, no simulator
WISP_ARDUPILOT=~/ardupilot pytest -q tests/test_sitl.py   # end to end with SITL, about 2 min
cd ~/wisp && node --test docs/control-lab/test/*.test.mjs   # the JavaScript model matches the Python one
```

Without a bridge, the Control Lab still works from GitHub Pages or any static server in its Model and Recording
modes: `cd ~/wisp/docs && python3 -m http.server 8000`, then <http://127.0.0.1:8000/control-lab/>.

## Safety rules in the bridge

A web page can reach a port on your computer, so the bridge:

- listens on 127.0.0.1 only, and accepts WebSocket connections only from its own pages, other `localhost`
  pages and `https://normansrule.github.io` (Origin check). Pages whose Origin is `null` (sandboxed frames,
  `file://`) are refused. Clients that send no Origin at all, which browsers never do, are accepted, so local
  scripts and the tests can connect;
- writes only tuning parameters on an allowlist (rate and angle PID gains; the
  4.7.2 position-controller gains such as `PSC_NE_VEL_P`; `GCS_PID_MASK`), each under an absolute ceiling;
- while armed, refuses a change of more than 4x in one step, and any change to a parameter that is 0 or cannot
  be read;
- counts a **stop** the moment it arrives: it cancels a take-off or step test received before it, even one not
  yet started, asks for Brake mode and reports whether the vehicle accepted it, and asks for Land if Brake is
  refused;
- starts a step test only when armed in Guided mode above 3 m, aborts it if anything else changes the mode, and
  ends it by braking to a stop before holding position in Guided;
- sends the vehicle a ground-station heartbeat once a second, so ArduPilot's ground-station-loss failsafe can
  work (not tested yet).

The 4x rule is per step: two steps can still reach gains that make SITL oscillate. Tighter limits for a real
Wisp are open question OQ-P1-3 in [review/P1](../../review/P1/README.md).

## Licence

MIT, see [`../LICENSE`](../LICENSE).
