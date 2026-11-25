"""Transparent uncalibrated overflow clarity proxy (Project 4)."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from backend.settling_velocity import richardson_zaki_velocity
from backend.unit_conversions import (
    slurry_density_kg_m3,
    slurry_mass_to_volumetric_m3_h,
    wt_pct_to_volume_fraction,
)


def compute_overflow_clarity_proxy(
    feed_slurry_tph: float,
    feed_solids_wt_pct: float,
    underflow_slurry_tph: float,
    underflow_solids_wt_pct: float,
    actual_area_m2: float,
    area_utilization_ratio: float,
    bed_level_m: float,
    tank_depth_m: float,
    v0_effective_mph: float,
    rz_exponent_n: float,
    floc_modifier: float,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    clarity_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute an uncalibrated overflow clarity indicator (0 = severe carryover, 100 = clear).

    Explicitly tagged UNCALIBRATED_SYNTHETIC_PROXY until real overflow turbidity / TSS
    measurements are supplied.
    """
    cfg = clarity_params or {}
    c_rise = float(cfg.get("c_rise_ratio", 0.85))
    c_flux = float(cfg.get("c_flux_overload", 1.20))
    c_bed = float(cfg.get("c_bed_freeboard", 2.50))
    c_floc = float(cfg.get("c_floc_deficit", 0.90))

    rho_feed = slurry_density_kg_m3(feed_solids_wt_pct, solids_density_kg_m3, liquid_density_kg_m3)
    rho_uf = slurry_density_kg_m3(underflow_solids_wt_pct, solids_density_kg_m3, liquid_density_kg_m3)

    q_feed_m3_h = slurry_mass_to_volumetric_m3_h(feed_slurry_tph, rho_feed)
    q_uf_m3_h = slurry_mass_to_volumetric_m3_h(underflow_slurry_tph, rho_uf)
    q_overflow_m3_h = max(0.0, q_feed_m3_h - q_uf_m3_h)

    upflow_velocity_mph = q_overflow_m3_h / actual_area_m2
    phi_feed = wt_pct_to_volume_fraction(feed_solids_wt_pct, solids_density_kg_m3, liquid_density_kg_m3)
    feed_settling_velocity_mph = float(richardson_zaki_velocity(phi_feed, v0_effective_mph, rz_exponent_n))
    rise_ratio = upflow_velocity_mph / max(feed_settling_velocity_mph, 1e-6)

    bed_fraction = bed_level_m / max(tank_depth_m, 0.5)
    penalty = (
        c_rise * max(0.0, rise_ratio - 0.15)
        + c_flux * max(0.0, area_utilization_ratio - 0.85)
        + c_bed * max(0.0, bed_fraction - 0.55)
        + c_floc * max(0.0, 1.0 - floc_modifier)
    )
    clarity_index = max(0.0, min(100.0, 100.0 * math.exp(-0.55 * penalty)))

    if clarity_index >= 75.0:
        band = "Clear (Proxy)"
    elif clarity_index >= 50.0:
        band = "Moderate (Proxy)"
    elif clarity_index >= 25.0:
        band = "Turbid (Proxy)"
    else:
        band = "High Carryover Risk (Proxy)"

    return {
        "overflow_clarity_index": float(clarity_index),
        "clarity_band": band,
        "scale_definition": "0 (severe fine-solids carryover) to 100 (clear overflow)",
        "upflow_velocity_mph": float(upflow_velocity_mph),
        "feed_settling_velocity_mph": float(feed_settling_velocity_mph),
        "rise_to_settling_ratio": float(rise_ratio),
        "overflow_volumetric_m3_h": float(q_overflow_m3_h),
        "calibration_status": "UNCALIBRATED_SYNTHETIC_PROXY",
        "warning": (
            "Overflow clarity index is an UNCALIBRATED proxy derived from rise velocity, "
            "flux loading, mud-bed freeboard, and flocculant deficit. Calibrate with measured "
            "overflow turbidity / suspended solids before plant deployment."
        ),
    }
