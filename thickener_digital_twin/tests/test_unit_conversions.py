"""Unit tests for unit-safe slurry mass, volume-fraction, and flux conversions."""

import pytest

from backend.unit_conversions import (
    kg_m2_h_to_t_m2_h,
    resolve_mass_rates,
    slurry_density_kg_m3,
    slurry_mass_to_volumetric_m3_h,
    tph_to_kg_h,
    volume_fraction_to_wt_pct,
    wt_pct_to_volume_fraction,
)


def test_wt_pct_phi_round_trip():
    for wt in [4.0, 10.0, 15.0, 55.0, 65.0, 70.0]:
        phi = wt_pct_to_volume_fraction(wt, solids_density_kg_m3=3200.0, liquid_density_kg_m3=1000.0)
        assert 0.0 < phi < wt / 100.0  # Because rho_s > rho_l, phi < mass fraction
        recovered = volume_fraction_to_wt_pct(phi, solids_density_kg_m3=3200.0, liquid_density_kg_m3=1000.0)
        assert recovered == pytest.approx(wt, rel=1e-6)


def test_slurry_density_and_volumetric_flow():
    rho = slurry_density_kg_m3(10.0, solids_density_kg_m3=3200.0, liquid_density_kg_m3=1000.0)
    assert 1050.0 < rho < 1100.0
    q = slurry_mass_to_volumetric_m3_h(3200.0, rho)
    assert q == pytest.approx(3200.0 * 1000.0 / rho, rel=1e-6)


def test_resolve_mass_rates_dry_vs_slurry_basis():
    dry1, slurry1 = resolve_mass_rates(100.0, 10.0, basis="dry_solids")
    assert dry1 == pytest.approx(100.0)
    assert slurry1 == pytest.approx(1000.0)

    dry2, slurry2 = resolve_mass_rates(1000.0, 10.0, basis="slurry")
    assert slurry2 == pytest.approx(1000.0)
    assert dry2 == pytest.approx(100.0)


def test_flux_and_mass_rate_scaling():
    assert tph_to_kg_h(320.0) == pytest.approx(320000.0)
    assert kg_m2_h_to_t_m2_h(1650.0) == pytest.approx(1.65)
