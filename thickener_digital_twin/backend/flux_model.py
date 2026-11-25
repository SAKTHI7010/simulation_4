"""Solids settling-flux curve and limiting-flux calculation (Project 4, §5.6)."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

import numpy as np

from backend.flocculant_model import flocculant_modifier
from backend.settling_velocity import richardson_zaki_velocity
from backend.unit_conversions import volume_fraction_to_wt_pct


def compute_flux_curve(
    v0_base_mph: float,
    rz_exponent_n: float,
    flocculant_dose_gpt: float,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    floc_model_type: Literal["exponential", "power_law"] = "exponential",
    floc_params: Optional[Dict[str, Any]] = None,
    phi_max: float = 0.60,
    n_points: int = 250,
) -> Dict[str, Any]:
    """Compute hindered settling curve v(phi), solids flux F(phi), and limiting flux.

    Flux units:
        - Volumetric solids flux: F_vol(phi) = v(phi) * phi   [m3/(m2*h) == m/h]
        - Dry-solids mass flux:   F_mass(phi) = rho_s * v(phi) * phi  [kg/(m2*h)]
        - Tonnes mass flux:       F_t(phi) = F_mass(phi) / 1000       [t/(m2*h)]
    """
    if not (0.05 <= phi_max < 1.0):
        raise ValueError(f"phi_max must be in [0.05, 1.0), got {phi_max}")
    if n_points < 20:
        raise ValueError(f"n_points must be >= 20, got {n_points}")

    floc_info = flocculant_modifier(flocculant_dose_gpt, model_type=floc_model_type, params=floc_params)
    v0_effective_mph = v0_base_mph * floc_info["modifier"]

    phi_grid = np.linspace(0.0, phi_max, n_points)
    vel_mph = richardson_zaki_velocity(phi_grid, v0_effective_mph, rz_exponent_n)
    flux_vol_mph = vel_mph * phi_grid
    flux_mass_kg_m2_h = solids_density_kg_m3 * flux_vol_mph
    flux_mass_t_m2_h = flux_mass_kg_m2_h / 1000.0
    wt_pct_grid = np.array(
        [volume_fraction_to_wt_pct(float(p), solids_density_kg_m3, liquid_density_kg_m3) for p in phi_grid]
    )

    max_idx = int(np.argmax(flux_mass_kg_m2_h))
    limiting_flux_kg_m2_h = float(flux_mass_kg_m2_h[max_idx])
    limiting_flux_t_m2_h = float(flux_mass_t_m2_h[max_idx])
    phi_at_max = float(phi_grid[max_idx])
    wt_pct_at_max = float(wt_pct_grid[max_idx])
    phi_analytical = 1.0 / (rz_exponent_n + 1.0)

    return {
        "phi": phi_grid.tolist(),
        "wt_pct": wt_pct_grid.tolist(),
        "settling_velocity_mph": vel_mph.tolist(),
        "flux_volumetric_mph": flux_vol_mph.tolist(),
        "flux_kg_m2_h": flux_mass_kg_m2_h.tolist(),
        "flux_t_m2_h": flux_mass_t_m2_h.tolist(),
        "v0_base_mph": float(v0_base_mph),
        "v0_effective_mph": float(v0_effective_mph),
        "rz_exponent_n": float(rz_exponent_n),
        "flocculant_info": floc_info,
        "limiting_flux_kg_m2_h": limiting_flux_kg_m2_h,
        "limiting_flux_t_m2_h": limiting_flux_t_m2_h,
        "phi_at_limiting_flux": phi_at_max,
        "wt_pct_at_limiting_flux": wt_pct_at_max,
        "phi_analytical_peak": float(phi_analytical),
        "flux_units": "kg/(m2*h) dry solids",
    }
