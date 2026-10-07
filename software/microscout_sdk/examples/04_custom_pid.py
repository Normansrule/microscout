# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Write your own height controller: a PID on height that commands vertical speed."""
import microscout
from microscout.control import PID

pid = PID(kp=1.5, ki=0.3, kd=0.2, limit=1.0)
target = 2.0

def height_controller(tel):
    vup = pid(target, tel.height, 0.01)
    return {"velocity": (0.0, 0.0, vup, 0.0)}

with microscout.connect("sim") as drone:
    drone.takeoff(1.0)
    drone.control_loop(height_controller, rate_hz=100, seconds=6)
    print("height after 6 s:", round(drone.telemetry.height, 3), "m (target", target, ")")
    drone.land()
