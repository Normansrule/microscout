# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Simulator behaviour tests. They test the reference controller in simulation,
not real hardware."""
import math

import pytest

import microscout
from microscout import CommandFailed
from microscout.control import PID, hover_axis_model, lqr


@pytest.fixture
def drone():
    return microscout.connect("sim")


def test_takeoff_and_hover(drone):
    tel = drone.takeoff(1.2)
    assert abs(tel.height - 1.2) < 0.08
    drone.hover(2.0)
    tel = drone.telemetry
    assert abs(tel.height - 1.2) < 0.05
    assert max(abs(a) for a in tel.attitude_deg[:2]) < 2.0


def test_move_and_goto(drone):
    drone.takeoff(1.0)
    tel = drone.move(forward=1.5, right=-0.5)
    assert abs(tel.position[0] - 1.5) < 0.1 and abs(tel.position[1] + 0.5) < 0.1
    tel = drone.goto(0, 0, 1.5)
    assert abs(tel.position[0]) < 0.1 and abs(tel.height - 1.5) < 0.1


@pytest.mark.parametrize("direction", ["back", "front", "left", "right"])
def test_flip_completes_and_recovers(drone, direction):
    drone.takeoff(1.5)
    t0 = drone.telemetry.t
    tel = drone.flip(direction)
    assert tel.t - t0 < 2.0
    assert max(abs(a) for a in tel.attitude_deg[:2]) < 10
    flip = [s for s in drone.log if s.t > t0]
    axis = 1 if direction in ("back", "front") else 0
    assert max(abs(s.rates_dps[axis]) for s in flip) > 800          # really rotated fast
    assert min(s.height for s in flip) > 0.8                       # did not hit the floor
    assert not drone._sim.phys.events


def test_flip_refused_when_low(drone):
    drone.takeoff(0.6)
    with pytest.raises(CommandFailed):
        drone.flip()


def test_land_disarms(drone):
    drone.takeoff(1.0)
    tel = drone.land()
    assert not tel.armed and tel.height < 0.02


def test_acro_sticks_roll(drone):
    drone.takeoff(1.5)
    drone.set_mode("acro")
    tel = drone.sticks(roll=0.3, throttle=0.25, seconds=0.2)
    assert tel.rates_dps[0] > 150


@pytest.mark.parametrize("mode", ["beginner", "sport", "acro"])
def test_pitch_stick_forward_means_forward(drone, mode):
    drone.takeoff(1.5)
    drone.set_mode(mode)
    x0 = drone.telemetry.position[0]
    if mode == "acro":
        tel = drone.sticks(pitch=0.2, throttle=0.3, seconds=0.15)
        assert tel.rates_dps[1] < -50                 # nose-down rate
        return
    tel = drone.sticks(pitch=0.5, throttle=0.5, seconds=1.0)
    assert tel.position[0] - x0 > 0.2


def test_radio_stick_watchdog(drone):
    drone.takeoff(1.2)
    drone._fc.set_sticks(0.0, 0.3, 0.0, 0.5)         # one frame, then the radio goes silent
    drone.wait(1.0)
    assert "radio link lost: hover" in drone._fc.warnings
    drone.wait(4.0)
    assert "link lost: landing" in drone._fc.warnings


def test_external_velocity_controller(drone):
    drone.takeoff(1.0)
    pid = PID(kp=1.0, limit=1.0)

    def ctrl(tel):
        return {"velocity": (pid(2.0, tel.position[0], 0.01), 0.0, 0.0, 0.0)}

    tel = drone.control_loop(ctrl, rate_hz=100, seconds=6)
    assert abs(tel.position[0] - 2.0) < 0.15


def test_watchdog_hovers_then_lands(drone):
    drone.takeoff(1.0)
    drone.velocity(0.5, 0, 0, seconds=0.5)       # then stop sending setpoints
    drone.wait(1.0)
    assert "link lost: hover" in drone._fc.warnings
    drone.wait(4.0)
    assert "link lost: landing" in drone._fc.warnings


def test_obstacle_stop_in_beginner_mode(drone):
    drone.takeoff(1.0)
    with pytest.raises(CommandFailed):          # the wall is 5 m ahead; it stops short and never arrives
        drone.goto(4.9, 0, 1.0, speed=1.5, timeout=12)
    tel = drone.telemetry
    assert tel.tof_m["front"] is not None and tel.tof_m["front"] > 0.25
    assert not drone._sim.phys.events


def test_altitude_ceiling(drone):
    drone.takeoff(10.0)
    assert drone.telemetry.height <= drone.config.safety.altitude_ceiling_m + 0.1


def test_emergency_stop(drone):
    drone.takeoff(1.0)
    tel = drone.emergency_stop()
    assert not tel.armed


def test_lqr_gain_is_stabilising():
    A, B = hover_axis_model()
    import numpy as np
    K = lqr(A, B, np.diag([4.0, 1.0]), np.array([[2.0]]))
    eig = np.linalg.eigvals(A - B @ K)
    assert all(e.real < 0 for e in eig)


def test_udp_link_not_available_yet():
    with pytest.raises(CommandFailed):
        microscout.connect("udp://192.168.4.1")
