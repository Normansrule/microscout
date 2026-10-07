# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Fly with stick inputs like a radio, in the three pilot modes."""
import microscout

with microscout.connect("sim") as drone:
    drone.takeoff(1.5)

    drone.set_mode("beginner")          # sticks = speed; stops itself near walls
    drone.sticks(pitch=0.5, seconds=2.0)
    print("beginner: speed", round(drone.telemetry.speed, 2), "m/s")

    drone.set_mode("sport")             # sticks = tilt angle, height held
    drone.sticks(roll=0.4, throttle=0.5, seconds=1.0)
    print("sport: roll", round(drone.telemetry.roll), "deg")

    drone.set_mode("acro")              # sticks = rotation rate, you control throttle
    drone.sticks(roll=0.2, throttle=0.3, seconds=0.3)
    print("acro: roll rate", round(drone.telemetry.rates_dps[0]), "deg/s")

    drone.set_mode("beginner")
    drone.hover(1.0)
    drone.land()
