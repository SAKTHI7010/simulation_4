"""Tests for Richardson-Zaki settling, flocculant modifier, flux curve, and required area."""

import numpy as np
import pytest

from backend.flocculant_model import flocculant_modifier
from backend.flux_model import compute_flux_curve
from backend.settling_velocity import richardson_zaki_velocity
from backend.thickener_area import compute_required_area


def test_richardson_zaki_monotonically_decreasing():
    phi = np.linspace(0.0, 0.55, 60)
    vel = richardson_zaki_velocity(phi, v0_mph=7.0, n=4.65)
    assert vel[0] == pytest.approx(7.0)
    assert np.all(np.diff(vel) < 0.0)


def test_flocculant_modifiers_bounded_with_diminishing_returns():
    for model_type in ["exponential", "power_law"]:
        m0 = flocculant_modifier(0.0, model_type=model_type)
        m20 = flocculant_modifier(20.0, model_type=model_type)
        m40 = flocculant_modifier(40.0, model_type=model_type)
        m500 = flocculant_modifier(500.0, model_type=model_type)
        assert m0["modifier"] <= m20["modifier"] <= m40["modifier"] <= m500["modifier"]
        assert m500["modifier"] <= m500["max_modifier"]
        assert m0["calibration_status"] == "SYNTHETIC_ASSUMED"


def test_flux_curve_maximum_and_analytical_peak():
    res = compute_flux_curve(v0_base_mph=7.0, rz_exponent_n=4.65, flocculant_dose_gpt=25.0, n_points=400)
    flux = np.array(res["flux_kg_m2_h"])
    assert np.all(np.isfinite(flux))
    assert np.all(flux >= 0.0)
    assert res["limiting_flux_kg_m2_h"] == pytest.approx(float(np.max(flux)))
    assert abs(res["phi_at_limiting_flux"] - res["phi_analytical_peak"]) < 0.005


def test_required_area_uses_dry_solids_basis():
    area = compute_required_area(dry_solids_feed_tph=320.0, limiting_flux_kg_m2_h=1600.0, actual_area_m2=250.0)
    assert area["required_area_m2"] == pytest.approx(200.0)
    assert area["area_utilization_ratio"] == pytest.approx(0.8)
    assert area["is_area_limited"] is False
