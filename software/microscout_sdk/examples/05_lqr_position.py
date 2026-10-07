# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""LQR position hold: design a gain on a linear hover model, fly it through attitude commands."""
import math

import numpy as np

import microscout
from microscout.control import hover_axis_model, lqr

A, B = hover_axis_model()                      # state [x, vx], input = tilt (rad)
K = lqr(A, B, Q=np.diag([4.0, 1.0]), R=np.array([[3.0]]))
print("LQR gain K =", np.round(K, 3))
target = (1.0, -0.5)

def lqr_controller(tel):
    # tilt needed in world x/y (NED, yaw ~ 0): positive pitch = nose up = accelerate backwards
    ax = -float((K @ np.array([tel.position[0] - target[0], tel.velocity[0]]))[0])
    ay = -float((K @ np.array([tel.position[1] - target[1], tel.velocity[1]]))[0])
    pitch, roll = -math.degrees(ax), math.degrees(ay)
    lim = 20
    return {"attitude": (max(-lim, min(lim, roll)), max(-lim, min(lim, pitch)), 0.0, None)}   # None = hold height

with microscout.connect("sim") as drone:
    drone.takeoff(1.0)
    drone.control_loop(lqr_controller, rate_hz=100, seconds=6)
    tel = drone.telemetry
    print("position:", [round(v, 2) for v in tel.position[:2]], "target:", target, "height:", round(tel.height, 2))
    drone.land()
