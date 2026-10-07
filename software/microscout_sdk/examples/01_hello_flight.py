# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Your first flight: take off, look around, land. Runs in the simulator."""
import microscout

with microscout.connect("sim") as drone:
    drone.takeoff(1.0)                 # arms automatically, climbs to 1 m
    print("hovering at", round(drone.telemetry.height, 2), "m")
    drone.turn(360)                    # look around
    drone.land()
print("landed. battery left:", round(drone.telemetry.battery_pct), "%")
