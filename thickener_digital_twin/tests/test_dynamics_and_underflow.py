"""Tests for underflow prediction, overflow clarity proxy, and dynamic bed-level ODE."""

import pytest

from backend.bed_dynamics import run_bed_dynamics_simulation
from backend.overflow_clarity import compute_overflow_clarity_proxy
from backend.underflow_model import predict_underflow_solids


def test_underflow_prediction_mass_balance_vs_compaction():
    res = predict_underflow_solids(
        dry_solids_feed_tph=320.0,
        feed_solids_wt_pct=10.0,
        underflow_withdrawal_tph=505.0,
        underflow_basis="slurry",
        area_utilization_ratio=0.75,
        bed_level_m=1.5,
        floc_modifier=1.15,
    )
    assert 55.0 <= res["predicted_underflow_solids_wt_pct"] <= 70.0
    assert res["outgoing_dry_solids_tph"] <= 320.05


def test_dynamic_bed_rises_on_feed_surge_and_conserves_mass():
    dyn = run_bed_dynamics_simulation(
        feed_rate_tph=320.0,
        feed_rate_basis="dry_solids",
        feed_solids_wt_pct=10.0,
        flocculant_dose_gpt=25.0,
        underflow_withdrawal_tph=505.0,
        underflow_basis="slurry",
        initial_bed_level_m=1.5,
        thickener_area_m2=250.0,
        tank_depth_m=4.5,
        bed_average_solids_wt_pct=45.0,
        bed_time_constant_h=1.5,
        v0_base_mph=7.0,
        rz_exponent_n=4.65,
        floc_model_type="exponential",
        duration_h=8.0,
        step_time_h=1.0,
        feed_rate_step_pct=20.0,
        underflow_withdrawal_step_pct=0.0,
        flocculant_dose_step_pct=-50.0,
    )
    assert dyn["summary"]["final_bed_level_m"] > dyn["summary"]["initial_bed_level_m"]
    assert dyn["mass_balance_check"]["closed_within_1pct"] is True


def test_overflow_clarity_labelled_uncalibrated():
    cl = compute_overflow_clarity_proxy(
        feed_slurry_tph=3200.0,
        feed_solids_wt_pct=10.0,
        underflow_slurry_tph=505.0,
        underflow_solids_wt_pct=63.0,
        actual_area_m2=250.0,
        area_utilization_ratio=0.75,
        bed_level_m=1.5,
        tank_depth_m=4.5,
        v0_effective_mph=8.0,
        rz_exponent_n=4.65,
        floc_modifier=1.15,
    )
    assert 0.0 <= cl["overflow_clarity_index"] <= 100.0
    assert cl["calibration_status"] == "UNCALIBRATED_SYNTHETIC_PROXY"
