# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Vehicle parameters used by the simulator.

Every number mirrors review/G1/calc/budgets.py (rev B). They are ESTIMATES until
system identification from real flight logs (Gate G7); tests/test_params.py checks
that the two files agree. Frame: NED world (x forward at take-off, y right, z down)
and FRD body (x forward, y right, z down).
"""
from dataclasses import dataclass, field
import math


@dataclass
class DroneParams:
    mass_kg: float = 0.0845            # budgets.py takeoff weight (rev B nominal at G2, CAD frame mass)
    motor_to_motor_m: float = 0.095    # diagonal motor-to-motor
    # inertia from budgets.inertia_estimate() (point/slab ESTIMATE incl. battery height)
    ixx: float = 4.67e-5
    iyy: float = 5.74e-5
    izz: float = 8.51e-5
    t_max_per_motor_n: float = 0.085 * 9.81   # conservative scenario: 85 g (ASSUMPTION, -30 % vs vendor table)
    motor_tau_s: float = 0.030         # first-order motor/prop response (ASSUMPTION)
    yaw_torque_per_thrust_m: float = 0.012     # prop drag torque / thrust (ASSUMPTION)
    prop_pitch_speed_ms: float = 59.0  # thrust falls linearly to zero at this axial inflow (ASSUMPTION)
    drag_cda_m2: float = 0.010         # body drag area x Cd for the ducted frame (ASSUMPTION)
    angular_drag: float = 2.0e-6       # N m per (rad/s), crude aero damping (ASSUMPTION)
    battery_mah: float = 550.0         # GNB 2S 550 HV (SOURCED)
    battery_cells: int = 2
    battery_r_int_ohm: float = 0.045   # pack internal resistance (ASSUMPTION)
    hover_eff_g_per_w: float = 3.0     # middle of the 2.5-3.5 g/W bracket (ESTIMATE)
    electronics_w: float = 2.98        # 0.402 A x 7.4 V from budgets.py (ESTIMATE)
    # motor layout (Betaflight Quad-X order: 1 rear-right, 2 front-right, 3 rear-left, 4 front-left)
    # spin: +1 = clockwise seen from above. Placeholders until the G2 schematic.
    motor_spin: tuple = (+1, -1, -1, +1)

    @property
    def arm_m(self):
        """Motor offset from the roll and pitch axes."""
        return self.motor_to_motor_m / math.sqrt(2) / 2

    @property
    def motor_xy(self):
        a = self.arm_m
        return ((-a, +a), (+a, +a), (-a, -a), (+a, -a))   # (x forward, y right) for motors 1..4

    @property
    def inertia(self):
        return (self.ixx, self.iyy, self.izz)


@dataclass
class ControllerGains:
    """Cascaded controller gains (placeholders until tuned on hardware at G7)."""
    rate_kp: tuple = (40.0, 40.0, 25.0)       # 1/s  -> angular acceleration demand
    rate_ki: tuple = (60.0, 60.0, 30.0)
    rate_kd: tuple = (0.006, 0.006, 0.0)
    rate_i_limit: float = 8.0                 # rad/s accumulated error clamp
    att_kp: tuple = (8.0, 8.0, 4.0)           # rad/s per rad
    vel_kp: tuple = (3.0, 3.0, 4.0)           # m/s^2 per m/s
    vel_ki: tuple = (1.0, 1.0, 2.0)
    pos_kp: tuple = (1.2, 1.2, 1.5)           # (m/s) per m
    max_tilt_deg: float = 35.0                # beginner / sport modes
    max_rate_dps: float = 1000.0              # acro and flips
    max_speed_ms: float = 2.0                 # beginner mode horizontal speed limit
    max_climb_ms: float = 1.5


@dataclass
class SafetyLimits:
    """Planned firmware safety behaviour (R-17), emulated in the simulator."""
    altitude_ceiling_m: float = 3.0
    geofence_radius_m: float = 10.0
    low_battery_cell_v: float = 3.4          # auto-land below this (per cell, under load)
    link_timeout_s: float = 0.5              # external-control watchdog -> hover, then land
    obstacle_stop_m: float = 0.40            # beginner mode stops short of walls
    battery_current_limit_a: float = 30.0    # DR-06: keep XT30 within its peak rating


@dataclass
class SimConfig:
    dt: float = 0.001                         # physics step (s)
    fc_rate_hz: int = 1000                    # flight-controller loop rate
    telemetry_hz: int = 100
    room_m: tuple = (10.0, 10.0, 4.0)         # length (x), width (y), height; start in the centre
    sensor_noise: bool = False
    seed: int = 1
    params: DroneParams = field(default_factory=DroneParams)
    gains: ControllerGains = field(default_factory=ControllerGains)
    safety: SafetyLimits = field(default_factory=SafetyLimits)
