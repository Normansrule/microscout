# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""Building blocks for your own controllers: PID and an LQR hover design."""
import numpy as np


class PID:
    """Textbook PID with output limits, anti-windup and derivative on measurement."""

    def __init__(self, kp, ki=0.0, kd=0.0, limit=None, i_limit=None):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.limit, self.i_limit = limit, i_limit
        self.i = 0.0
        self.prev = None

    def reset(self):
        self.i = 0.0
        self.prev = None

    def __call__(self, setpoint, measurement, dt):
        e = setpoint - measurement
        self.i += e * dt
        if self.i_limit is not None:
            self.i = max(-self.i_limit, min(self.i_limit, self.i))
        d = 0.0 if self.prev is None else -(measurement - self.prev) / dt
        self.prev = measurement
        u = self.kp * e + self.ki * self.i + self.kd * d
        if self.limit is not None:
            u = max(-self.limit, min(self.limit, u))
        return u


def lqr(A, B, Q, R):
    """Continuous-time LQR gain K (u = -K x). Uses SciPy if installed."""
    try:
        from scipy.linalg import solve_continuous_are
        P = solve_continuous_are(A, B, Q, R)
    except ImportError:   # fallback: iterate the Riccati equation in small steps
        P = np.array(Q, dtype=float)
        for _ in range(200000):
            dP = A.T @ P + P @ A - P @ B @ np.linalg.solve(R, B.T @ P) + Q
            P += 1e-4 * dP
            if np.abs(dP).max() < 1e-9:
                break
    return np.linalg.solve(R, B.T @ P)


def hover_axis_model(g=9.81):
    """Linearised translation along one horizontal axis near hover, with the attitude
    loop treated as fast: state x = [position, velocity], input u = tilt angle (rad).
    x' = [[0, 1], [0, 0]] x + [[0], [g]] u."""
    A = np.array([[0.0, 1.0], [0.0, 0.0]])
    B = np.array([[0.0], [g]])
    return A, B
