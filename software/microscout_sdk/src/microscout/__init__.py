# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""MicroScout Python SDK.

    import microscout
    with microscout.connect("sim") as drone:
        drone.takeoff(1.0)
        drone.flip("back")
        drone.land()

Today only the simulator exists (Gate G1 - no hardware yet). The same calls are
meant to drive the real drone over Wi-Fi once the firmware lands (milestone M7).
"""
from .drone import CommandFailed, Drone, connect
from .params import ControllerGains, DroneParams, SafetyLimits, SimConfig
from .telemetry import Telemetry

__version__ = "0.1.0.dev0"
__all__ = ["connect", "Drone", "CommandFailed", "Telemetry", "SimConfig", "DroneParams", "ControllerGains", "SafetyLimits"]
