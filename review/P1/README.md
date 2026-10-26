# Phase 1 review: simulation stack and Control Lab basics

> **STATUS: DRAFT, waiting for the owner's review at the Phase 1 gate.** Everything here ran in ArduCopter 4.7.2
> SITL (software in the loop) in a cloud container. Nothing has been bought, built or flown, and nothing here says
> how a real Wisp will fly. Numbers from a simulator are marked SITL; model numbers are marked ESTIMATE.

**Gate decision needed:** approve Phase 1, answer the open questions below, and say whether to order the Wisp
Nano parts for Phase 2. Nothing will be ordered without that.

## What Phase 1 delivers

| Deliverable | Where |
|---|---|
| Ground bridge: MAVLink (Micro Air Vehicle Link) to WebSocket, latency measurement, commands with safety rules, recording | [`software/wisp_gcs/bridge.py`](../../software/wisp_gcs/bridge.py) |
| Rate-loop step test, scoring, plant fit, stability margins | [`steptest.py`](../../software/wisp_gcs/steptest.py), [`fit.py`](../../software/wisp_gcs/fit.py) |
| Control Lab: the roll-rate loop as a block diagram with the live numbers, the PID equation with values substituted, step response, Bode plot, gains | [`docs/control-lab`](../../docs/control-lab/) ([on Pages](https://normansrule.github.io/wisp/control-lab/)) |
| A recorded SITL session the Control Lab replays without a simulator | [`sitl/`](sitl/), [`docs/control-lab/data`](../../docs/control-lab/data/) |
| Ubuntu commands for the whole stack | [`software/wisp_gcs/README.md`](../../software/wisp_gcs/README.md) |
| Tests: 22 unit, 1 end to end against SITL, 5 that hold the JavaScript model to the Python one | [`software/wisp_gcs/tests`](../../software/wisp_gcs/tests/), [`docs/control-lab/test`](../../docs/control-lab/test/) |
| A recording of the Control Lab flying SITL in a browser (74 s) | [`media/control-lab-live-sitl.mp4`](media/control-lab-live-sitl.mp4) |

<p>
  <img src="media/lab-live-sitl.png" width="100%" alt="Control Lab in Live SITL mode after a step test: block diagram with live values, the PID equation with numbers substituted, step response of target, SITL and model, Bode plot, gains and the vehicle panel with a Stop and hover button">
</p>

The Control Lab has three sources, all with the same screen:

- **Model**: the loop model alone, on the SITL plant fitted below or on the Wisp Follow estimate from Phase 0.
- **Recording**: three roll-rate steps recorded from SITL through the bridge, played back with a scrubber. Works
  on GitHub Pages.
- **Live SITL**: the bridge serves the page at `http://127.0.0.1:8765/control-lab/`. Take off, run a step test,
  move the gains, send them to SITL, compare. **Stop and hover** (or the Escape key) is always one press away.

## What the simulator showed

**1. ArduCopter's default roll-rate gains are close to the edge on SITL's quad.** Same 90 °/s roll-rate step
at three gain sets, scored from the PID_TUNING stream (about 86 samples a second):

| Gains (P, I, D) | Rise 10-90 % | Overshoot | Settles within 5 % | Tracking error, RMS (root mean square) |
|---|---:|---:|---:|---:|
| Half (0.0675, 0.0675, 0.0018) | 117 ms | 6.4 % | not within the step | 17.5 °/s |
| Default (0.135, 0.135, 0.0036) | 93 ms | 3.5 % | 167 ms | 9.4 °/s |
| Double (0.27, 0.27, 0.0072) | 91 ms | 9.3 % | never: a ~20 Hz oscillation | 6.0 °/s |

At double gains SITL breaks into an oscillation whose size changes from run to run (6-64 % overshoot seen in four
runs). These are SITL numbers for SITL's generic quad, not for Wisp.

**2. A small loop model reproduces SITL, and predicts the instability.** PID, a delay, a motor lag, the airframe
(b / (s + a)) and ArduPilot's 20 Hz gyro filter, fitted by simulating the closed loop
([`fit.py`](../../software/wisp_gcs/fit.py)):

- Fitted on the default and half steps: b = 281 /s², a = 2.3 /s, delay 3.0 ms, motor lag below what 86 Hz data
  can resolve; the model tracks those steps to 1.3 and 1.2 °/s RMS.
- **Out of sample:** fitted on the default step alone, it predicts the half-gain step to **1.3 °/s RMS**, and
  predicts the double gains **unstable** (negative phase margin), which matches SITL's oscillation.
- Its first version left out the gyro filter and predicted double gains to be fine. Adding the filter, which
  ArduPilot runs at 20 Hz by default, is what made it right: at these frequencies that filter is the biggest
  source of lag in the loop.

**3. The margins are a range, not one number.** At the default gains the two fits give a crossover near 14 Hz,
phase margin **36-52°** and gain margin **2.8-5.0 dB**. They differ because 86 samples a second pin the delay down
only loosely (0.6-3.0 ms). Phase 6 should identify from the flight controller's 400 Hz logs instead.

**4. Wisp Follow will need lower gains than ArduPilot's defaults (ESTIMATE).** With the Phase 0 estimate
(b = 700 /s², 30 ms motor lag, 40 Hz gyro filter) the default gains leave 3° of phase margin. About half the
defaults (0.07, 0.07, 0.0018) give 41° and 6.3 dB. This is a starting point for a tethered first hover, to be
replaced by ArduPilot's autotune and real logs in Phase 3.

**5. Stop works, after a fix.** The first scripted session found that a stop sent during a step test waited
until the test finished, because the bridge handled each app's commands one at a time. Now stop is handled the
moment it arrives: the step test aborts within **22 ms** and the drone holds in Brake mode (0.11 m/s 2.5 s later,
SITL).

**6. Latency is shown, and small on one computer.** Vehicle round trip (MAVLink TIMESYNC) **2.3-7.9 ms**, app
round trip (WebSocket ping) **0.6-2.9 ms**, so telemetry on screen is about 2-5 ms old. Both are SITL on the same
computer; a radio link will add much more (Phase 3).

**7. Timestamps needed care.** PID_TUNING carries no time of its own, so the bridge stamps it on arrival. When the
computer was busy (SITL, browser and screen recording at once) samples arrived in bursts and a step looked like a
staircase (rise read as 124 ms instead of 93 ms). The bridge now spreads such bursts at the stream's period
(`Dejitter`): on a test burst the timing error fell from 70 ms to 3.5 ms, and the browser run read 93 ms again.

## What was checked, and how

| Check | Result |
|---|---|
| Scripted session through the bridge ([`session.py`](../../software/wisp_gcs/session.py)): take-off, 3 steps, stop mid-step, two refused parameter writes, land | Passed; [`sitl/session.json`](sitl/session.json) |
| End-to-end test against SITL ([`tests/test_sitl.py`](../../software/wisp_gcs/tests/test_sitl.py)) | Passed (105 s) |
| Unit tests: telemetry, step plan and score, filter, fit recovers a known plant, margins, replay file, parameter allowlist, static files stay inside `docs/`, Origin check | 22 passed |
| JavaScript model against Python (closed loop, margins, score) | 5 passed, to 1 part in 10⁶ |
| Browser run with Playwright and Chromium against SITL: take off, step, play, send gains, second step (P 0.18: 89 ms rise, 2.5 % overshoot), stop, land | No page errors; recorded in [`media/`](media/) |
| Accessibility: axe-core 4.10.2 (WCAG 2.2 A and AA rules plus best practice) on Model, Recording and Live at 1440 px and Recording at 390 px | 0 violations, after fixing heading order, two ARIA labels and a scroll region |
| Touch targets at 390 px | All controls 44 px or taller, except inline links, which WCAG exempts |
| Frame rate of the live view (headless Chromium, software rendering, no GPU) | 43-59 frames a second while also running SITL and recording video |

## Not done, or not verified

- **Gazebo** is still not installed: its package host is blocked from this container. Everything used SITL's own
  physics. The Ubuntu commands are in [`review/P0/sitl.md`](../P0/sitl.md) but have not been run here.
- **Only the roll-rate loop** is in the Control Lab. Angle, velocity and position loops (the rest of the cascade)
  come with Phases 3-5; pitch and yaw use the same code but were not step-tested.
- **The Crazyflie simulator** for Wisp Nano is not set up yet.
- **Live SITL from the GitHub Pages site** (https page to `ws://127.0.0.1`) is UNCONFIRMED: browsers may block it
  (Chrome's Private Network Access rules). The supported way is the page the bridge serves.
- **The Impeccable detector** did not run: its launcher downloads a platform binary, and that host is blocked.
  The audit below follows its rubric by hand, with axe-core for the automated part.
- **No 3D view** in the Control Lab yet. The "60 frames a second for 3D views" rule applies when one is added
  (the Flight Lab's 3D view already exists); the live 2D strip chart was measured above.
- **Nothing ran against a real vehicle**, and the bridge's safety rules are designed for SITL (see OQ-P1-3).

## Design audit (Impeccable rubric, by hand)

| # | Dimension | Score | Key finding |
|---|---|---:|---|
| 1 | Accessibility | 4 | axe-core clean in all four views; keyboard: everything is a native control, Escape stops |
| 2 | Performance | 3 | Small SVG redraws on input; the animation loop keeps running when idle (cheap, but could sleep) |
| 3 | Theming | 3 | All colours are tokens, the canvas reads them too; light only, on purpose (read in daylight, Sectional concept) |
| 4 | Responsive | 3 | Works from 390 px up with no sideways page scroll; on phones the block diagram scrolls sideways inside its panel |
| 5 | Implementation integrity | 4 | Every number on screen is computed from the model or recorded data; labels say which (model, recorded, live) |
| | **Total** | **17/20** | Good |

Concept rules kept: one magenta for the vehicle's own motion, airspace blue for the model, sensors and limits,
ink for targets; no legends, each line named in the sentence above its chart; Overpass throughout; press feedback
at scale 0.97 with an ease-out curve, off under reduced motion.

## Open questions

| # | Question | Recommendation |
|---|---|---|
| OQ-P1-1 | **Order the Wisp Nano parts for Phase 2?** Crazyflie 2.1+ STEM ranging bundle ($410, Bitcraze) plus spare batteries; prices and stock from Phase 0, to be rechecked before ordering. | Yes, after you confirm OQ-W6 below. I will recheck stock and price and wait for your go before any order. |
| OQ-P1-2 | The Phase 0 questions are still open (OQ-W1 to W9 in [review/P0](../P0/README.md)). Phase 1 used the recommended defaults: the Sectional design (OQ-W7). Phase 2 needs OQ-W6 (which Crazyflie). | Answer OQ-W6 and OQ-W7 now; the others can wait until Phase 3. |
| OQ-P1-3 | Gain limits for a real vehicle. The bridge now refuses a change of more than 4x per step while armed; two steps can still reach unstable gains (seen in SITL). | Before Phase 3, add absolute limits while armed: rate gains between 0.5x and 1.5x of the values at arming, wider only when disarmed. |
| OQ-P1-4 | Live mode from the public Pages site, or only from the page the bridge serves? | Only from the bridge's page: no cross-site path into a computer that commands a drone. |
| OQ-P1-5 | Wisp Follow starting gains: about half of ArduPilot's defaults, from the estimate in finding 4? | Yes, for the first tethered hover only; then ArduPilot autotune on the tether. |
| OQ-P1-6 | Set up the Crazyflie simulator in Phase 2 before the hardware arrives? | Yes, so the Nano's step tests can be rehearsed. |
| OQ-W8 | The GitHub repository is still named `microscout` (the `wisp` URL does not exist yet), so the Pages links in the repo do not work until it is renamed. | Rename it: Settings, General, Repository name. GitHub redirects the old links. |

## How to reproduce

The Ubuntu commands are in [`software/wisp_gcs/README.md`](../../software/wisp_gcs/README.md). The recorded
session is [`sitl/recording.jsonl.gz`](sitl/recording.jsonl.gz) (every frame the bridge sent, gzipped) and
[`sitl/session.json`](sitl/session.json); `python3 -m wisp_gcs.replay` rebuilds the Control Lab's data file from them,
and a unit test checks that it still does.

<p>
  <img src="media/lab-recording-double.png" width="49%" alt="Recording mode at double gains: SITL oscillating, the model unstable, phase margin minus 31 degrees">
  <img src="media/lab-model-wisp.png" width="49%" alt="Model mode on the Wisp Follow estimate at about half the default gains: 41 degree phase margin">
</p>
