"""Richardson-Zaki hindered settling velocity model (Project 4, §5.6)."""

from __future__ import annotations

from typing import Union

import numpy as np

ArrayOrFloat = Union[float, np.ndarray]


def richardson_zaki_velocity(
    phi: ArrayOrFloat,
    v0_mph: float,
    n: float,
) -> ArrayOrFloat:
    """Compute hindered settling velocity v(phi) = v0 * (1 - phi)^n in m/h.

    Args:
        phi: Solids volume fraction in [0, 1).
        v0_mph: Effective free settling velocity in m/h (>= 0).
        n: Richardson-Zaki exponent (dimensionless, >= 0).
    """
    if v0_mph < 0.0:
        raise ValueError(f"v0_mph must be non-negative, got {v0_mph}")
    if n < 0.0:
        raise ValueError(f"Richardson-Zaki exponent n must be non-negative, got {n}")

    phi_arr = np.asarray(phi, dtype=float)
    if np.any(phi_arr < 0.0) or np.any(phi_arr >= 1.0):
        raise ValueError("Solids volume fraction phi must lie in [0, 1).")

    vel = v0_mph * np.power(1.0 - phi_arr, n)
    if np.isscalar(phi):
        return float(vel)
    return vel
