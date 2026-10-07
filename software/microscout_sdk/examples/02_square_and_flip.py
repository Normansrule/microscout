# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Fly a square, then do a back flip and a side flip."""
import microscout

with microscout.connect("sim") as drone:
    drone.takeoff(1.5)
    for _ in range(4):
        drone.move(forward=1.0)
        drone.turn(90)
    drone.flip("back")
    drone.flip("left")
    drone.land()
    import tempfile, os
    path = os.path.join(tempfile.gettempdir(), "square_and_flip.csv")
    drone.save_log(path)
    print("log written to", path)
