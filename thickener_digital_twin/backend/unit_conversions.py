"""Unit-safe engineering conversions for mineral-processing slurry calculations.

All functions keep mass fraction (% w/w) strictly distinct from solids volume
fraction (phi, v/v), and distinguish slurry mass flow from dry-solids mass flow.
"""

from __future__ import annotations

from typing import Literal, Tuple


def wt_pct_to_volume_fraction(
    wt_pct: float,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
) -> float:
    """Convert solids mass concentration (% w/w) to solids volume fraction phi (v/v)."""
    if not (0.0 <= wt_pct < 100.0):
        raise ValueError(f"wt_pct must be in [0, 100), got {wt_pct}")
    if solids_density_kg_m3 <= 0.0 or liquid_density_kg_m3 <= 0.0:
        raise ValueError("Solids and liquid densities must be positive.")
    if wt_pct == 0.0:
        return 0.0
    w = wt_pct / 100.0
    v_solids = w / solids_density_kg_m3
    v_liquid = (1.0 - w) / liquid_density_kg_m3
    return v_solids / (v_solids + v_liquid)


def volume_fraction_to_wt_pct(
    phi: float,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
) -> float:
    """Convert solids volume fraction phi (v/v) to solids mass concentration (% w/w)."""
    if not (0.0 <= phi <= 1.0):
        raise ValueError(f"phi must be in [0, 1], got {phi}")
    if solids_density_kg_m3 <= 0.0 or liquid_density_kg_m3 <= 0.0:
        raise ValueError("Solids and liquid densities must be positive.")
    m_solids = phi * solids_density_kg_m3
    m_liquid = (1.0 - phi) * liquid_density_kg_m3
    return 100.0 * (m_solids / (m_solids + m_liquid))


def slurry_density_kg_m3(
    wt_pct: float,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
) -> float:
    """Compute bulk slurry density in kg/m3 from solids % w/w and phase densities."""
    if not (0.0 <= wt_pct <= 100.0):
        raise ValueError(f"wt_pct must be in [0, 100], got {wt_pct}")
    if solids_density_kg_m3 <= 0.0 or liquid_density_kg_m3 <= 0.0:
        raise ValueError("Solids and liquid densities must be positive.")
    w = wt_pct / 100.0
    inv_rho = (w / solids_density_kg_m3) + ((1.0 - w) / liquid_density_kg_m3)
    return 1.0 / inv_rho


def resolve_mass_rates(
    rate_tph: float,
    wt_pct: float,
    basis: Literal["dry_solids", "slurry"] = "dry_solids",
) -> Tuple[float, float]:
    """Return (dry_solids_tph, slurry_tph) from a given rate, % w/w, and basis."""
    if rate_tph < 0.0:
        raise ValueError(f"rate_tph must be non-negative, got {rate_tph}")
    if not (0.0 < wt_pct <= 100.0):
        raise ValueError(f"wt_pct must be in (0, 100], got {wt_pct}")
    w = wt_pct / 100.0
    if basis == "dry_solids":
        dry_solids_tph = float(rate_tph)
        slurry_tph = dry_solids_tph / w
    elif basis == "slurry":
        slurry_tph = float(rate_tph)
        dry_solids_tph = slurry_tph * w
    else:
        raise ValueError(f"Unknown mass-rate basis '{basis}'. Use 'dry_solids' or 'slurry'.")
    return dry_solids_tph, slurry_tph


def slurry_mass_to_volumetric_m3_h(slurry_tph: float, slurry_density: float) -> float:
    """Convert slurry mass rate (t/h) to volumetric flow rate (m3/h)."""
    if slurry_tph < 0.0:
        raise ValueError(f"slurry_tph must be non-negative, got {slurry_tph}")
    if slurry_density <= 0.0:
        raise ValueError(f"slurry_density must be positive, got {slurry_density}")
    return (slurry_tph * 1000.0) / slurry_density


def tph_to_kg_h(rate_tph: float) -> float:
    """Convert tonnes/hour to kg/hour."""
    return rate_tph * 1000.0


def kg_m2_h_to_t_m2_h(flux_kg_m2_h: float) -> float:
    """Convert solids flux from kg/(m2*h) to t/(m2*h)."""
    return flux_kg_m2_h / 1000.0
