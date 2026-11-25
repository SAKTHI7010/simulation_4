"""Synthetic slurry rheology model relating underflow solids concentration to yield stress."""

from __future__ import annotations

from typing import Union

import numpy as np

from backend.unit_conversions import wt_pct_to_volume_fraction

ArrayOrFloat = Union[float, np.ndarray]


def yield_stress_pa(
    wt_pct: ArrayOrFloat,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    rheology_a_pa: float = 0.055,
    rheology_b: float = 21.3,
) -> ArrayOrFloat:
    """Compute synthetic Bingham yield stress tau_y = a * exp(b * phi) in Pascals.

    Marked synthetic until measured rheometer curves are supplied for the target tailings.
    """
    if rheology_a_pa <= 0.0 or rheology_b < 0.0:
        raise ValueError("Rheology coefficients must satisfy a > 0 and b >= 0.")

    if np.isscalar(wt_pct):
        phi = wt_pct_to_volume_fraction(float(wt_pct), solids_density_kg_m3, liquid_density_kg_m3)
        return float(rheology_a_pa * np.exp(rheology_b * phi))

    wt_arr = np.asarray(wt_pct, dtype=float)
    phi_arr = np.array(
        [wt_pct_to_volume_fraction(float(w), solids_density_kg_m3, liquid_density_kg_m3) for w in wt_arr]
    )
    return rheology_a_pa * np.exp(rheology_b * phi_arr)
