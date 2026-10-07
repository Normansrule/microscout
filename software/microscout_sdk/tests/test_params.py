# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)
# SPDX-License-Identifier: MIT
"""The simulator's vehicle parameters must agree with the G1 budget model."""
import importlib.util
import pathlib

import pytest

from microscout.params import DroneParams

BUDGETS = pathlib.Path(__file__).resolve().parents[3] / "review" / "G1" / "calc" / "budgets.py"


@pytest.fixture(scope="module")
def budgets():
    if not BUDGETS.exists():
        pytest.skip("budgets.py not found (SDK used outside the repo)")
    spec = importlib.util.spec_from_file_location("budgets", BUDGETS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mass_matches(budgets):
    assert abs(DroneParams().mass_kg * 1000 - budgets.weight_totals()[0]) < 0.5


def test_inertia_matches(budgets):
    p = DroneParams()
    for a, b in zip(p.inertia, budgets.inertia_estimate()):
        assert abs(a - b) / b < 0.02


def test_geometry_and_battery_match(budgets):
    p = DroneParams()
    assert p.motor_to_motor_m * 1000 == budgets.MOTOR_TO_MOTOR_MM.value
    assert p.battery_mah == budgets.CAP_MAH.value
    assert abs(p.t_max_per_motor_n / 9.81 * 1000 - budgets.THRUST_SCENARIOS[0][0]) < 0.5
    assert abs(p.electronics_w - budgets.electronics_battery_current_a() * budgets.V_NOM.value) < 0.05
