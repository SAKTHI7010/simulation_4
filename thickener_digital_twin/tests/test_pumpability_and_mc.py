"""Tests for synthetic rheology, pumpability constraint, and Monte Carlo uncertainty."""

import pytest

from backend.monte_carlo import run_monte_carlo
from backend.pumpability import evaluate_pumpability
from backend.rheology_model import yield_stress_pa


def test_yield_stress_increases_with_solids():
    t55 = yield_stress_pa(55.0)
    t63 = yield_stress_pa(63.0)
    t70 = yield_stress_pa(70.0)
    assert 0.0 < t55 < t63 < t70


def test_pumpability_flags_pump_limited_above_rating():
    feasible = evaluate_pumpability(
        underflow_solids_wt_pct=58.0,
        underflow_slurry_tph=505.0,
        available_pump_pressure_bar=15.0,
    )
    assert feasible["is_pump_limited"] is False
    assert feasible["pumpability_flag"] == "Feasible"

    limited = evaluate_pumpability(
        underflow_solids_wt_pct=71.0,
        underflow_slurry_tph=505.0,
        available_pump_pressure_bar=15.0,
    )
    assert limited["is_pump_limited"] is True
    assert limited["pumpability_flag"] == "Pump-limited"
    assert limited["required_pump_pressure_bar"] > 15.0


def test_monte_carlo_reproducible_seed_and_percentiles():
    r1 = run_monte_carlo({"n_simulations": 120, "random_seed": 42})
    r2 = run_monte_carlo({"n_simulations": 120, "random_seed": 42})
    assert r1["underflow_solids_stats"]["mean"] == pytest.approx(r2["underflow_solids_stats"]["mean"])
    assert r1["underflow_solids_stats"]["p5"] <= r1["underflow_solids_stats"]["p50"] <= r1["underflow_solids_stats"]["p95"]
    assert 0.0 <= r1["pumpability_violation_probability_pct"] <= 100.0
