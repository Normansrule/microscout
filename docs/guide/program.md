> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (written at G1 rev B; simulator only)

# Programming MicroScout

The Python SDK talks to a simulator today and is meant to talk to the real drone over Wi-Fi once the firmware exists (milestone M7) - **same code, different `connect()` string.** The simulator uses estimated parameters from `review/G1/calc/budgets.py`; it shows the control design working in principle, not how the real drone will fly.

## Install

```bash
git clone https://github.com/Normansrule/microscout.git
cd microscout/software/microscout_sdk
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # numpy; matplotlib/scipy/pytest for plots, LQR and tests
pytest                          # 23 simulator tests
microscout demo --plot demo.png # take off, square, turn, back flip, side flip, land
```

## Level 1 - five lines to fly

```python
import microscout

with microscout.connect("sim") as drone:   # later: microscout.connect("udp://192.168.4.1")
    drone.takeoff(1.0)        # arms and climbs to 1 m
    drone.move(forward=1.0)   # metres, relative to where it points
    drone.flip("back")        # 360° back flip (needs 1 m of height)
    drone.land()              # touches down and disarms
```

Every high-level call blocks until it is done and returns the latest telemetry. If something is refused (for example a flip at 0.5 m) you get a `CommandFailed` with the reason.

| Call | What it does |
|---|---|
| `takeoff(height)` / `land()` | Climb and hold / descend, touch down, disarm |
| `move(forward, right, up, speed)` | Relative move in the drone's heading frame |
| `goto(x, y, height, speed)` | Absolute move in the take-off frame (x forward, y right) |
| `turn(degrees)` | Rotate in place, clockwise positive |
| `flip(direction)` | `"back"`, `"front"`, `"left"`, `"right"` |
| `hover(seconds)` / `wait(seconds)` | Hold position / let time pass without new commands |
| `emergency_stop()` | Motors off |

## Level 2 - fly like a pilot

```python
drone.set_mode("beginner")                 # sticks = speed, stops before walls
drone.sticks(pitch=0.5, seconds=2)         # forward at half speed for 2 s
drone.set_mode("acro")                     # sticks = rotation rate
drone.sticks(roll=0.3, throttle=0.3, seconds=0.3)
```

Stick values follow a radio: `pitch=+1` is the stick pushed forward (nose down, fly forward), `roll=+1` right, `yaw=+1` clockwise, `throttle` 0..1. Note the stick pitch sign is the opposite of the `pitch` angle in telemetry and setpoints, where + is nose up.

## Level 3 - your own controller

Write a function that receives telemetry and returns a setpoint; the SDK calls it at the rate you choose. If your code stops answering, the drone's watchdog hovers and then lands.

```python
from microscout.control import PID
pid = PID(kp=1.5, ki=0.3, kd=0.2, limit=1.0)

def height_controller(tel):
    return {"velocity": (0.0, 0.0, pid(2.0, tel.height, 0.01), 0.0)}

drone.control_loop(height_controller, rate_hz=100, seconds=6)
```

| Setpoint | Values | Use it for |
|---|---|---|
| `{"rates": (p, q, r, thrust)}` | deg/s and 0..1 collective | Acro, system identification |
| `{"attitude": (roll, pitch, yaw_rate, thrust or None)}` | deg, deg/s; `None` = hold height | LQR / MPC on translation |
| `{"velocity": (vx, vy, vup, yaw_rate)}` | m/s in the take-off frame | Path following, PID |

`microscout.control` has `PID`, `lqr(A, B, Q, R)` and `hover_axis_model()`; `examples/05_lqr_position.py` designs an LQR position hold and flies it.

## Data

`drone.telemetry` has position, height, velocity, attitude, body rates, motor commands, battery V/A/%, the five ToF distances, mode and status. `drone.log` keeps every sample (100 Hz). `drone.save_log("flight.csv")` writes CSV; `drone.save_trajectory("t.json")` writes poses for the 3D viewer.

Conventions: positions are NED in the take-off frame (x forward, y right, z down; `height` = -z); roll + = right side down, pitch + = nose up, yaw + = clockwise seen from above; motors in Betaflight order (rear-right, front-right, rear-left, front-left).

## Change the drone

```python
from microscout import SimConfig
cfg = SimConfig()
cfg.params.mass_kg = 0.078            # e.g. the 450 mAh battery
cfg.gains.max_rate_dps = 800          # gentler acro
cfg.safety.altitude_ceiling_m = 2.0
drone = microscout.connect("sim", config=cfg)
```

## How the simulator works

Rigid-body 6-DOF model with first-order motors (30 ms), thrust falling with inflow speed, body drag, a simple 2S battery and a 10 x 10 x 4 m room with walls the ToF sensors can see. The **reference flight controller** in `microscout/sim/fc.py` is the behaviour the firmware must implement: position → velocity → attitude → body-rate cascade, an air-mode mixer, pilot modes, onboard tasks (takeoff, land, goto, turn, flip) and the safety rules in [fly.md](fly.md). It reads the true simulated state; the real firmware has to estimate it from the IMU, flow, ToF and barometer, so expect real flight to be less tidy until the estimator is tuned (G7).
