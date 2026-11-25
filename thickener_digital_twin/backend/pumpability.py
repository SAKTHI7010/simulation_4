"""Underflow pipeline hydraulics and positive-displacement pumpability constraint."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np
from scipy.optimize import brentq

from backend.rheology_model import yield_stress_pa
from backend.unit_conversions import slurry_density_kg_m3


def evaluate_pumpability(
    underflow_solids_wt_pct: float,
    underflow_slurry_tph: float,
    available_pump_pressure_bar: float = 15.0,
    pipe_length_m: float = 300.0,
    pipe_diameter_m: float = 0.20,
    static_elevation_head_m: float = 15.0,
    plastic_viscosity_pa_s: float = 0.08,
    rheology_a_pa: float = 0.055,
    rheology_b: float = 21.3,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    gravity_m_s2: float = 9.81,
    compute_max_solids: bool = True,
) -> Dict[str, Any]:
    """Estimate Bingham pipeline pressure loss + static head and flag pump-limited states."""
    if pipe_length_m <= 0.0 or pipe_diameter_m <= 0.0:
        raise ValueError("Pipe length and diameter must be positive.")
    if available_pump_pressure_bar <= 0.0:
        raise ValueError("available_pump_pressure_bar must be positive.")
    if underflow_slurry_tph < 0.0:
        raise ValueError("underflow_slurry_tph must be non-negative.")

    tau_y = float(
        yield_stress_pa(
            underflow_solids_wt_pct,
            solids_density_kg_m3=solids_density_kg_m3,
            liquid_density_kg_m3=liquid_density_kg_m3,
            rheology_a_pa=rheology_a_pa,
            rheology_b=rheology_b,
        )
    )
    rho_uf = slurry_density_kg_m3(underflow_solids_wt_pct, solids_density_kg_m3, liquid_density_kg_m3)
    q_m3_s = (underflow_slurry_tph * 1000.0) / (3600.0 * rho_uf)
    pipe_area_m2 = math.pi * (pipe_diameter_m / 2.0) ** 2
    pipe_velocity_m_s = q_m3_s / pipe_area_m2

    # Laminar Bingham plastic wall shear approximation (Buckingham-Reiner linear asymptotic)
    shear_rate_s = (8.0 * pipe_velocity_m_s) / pipe_diameter_m
    tau_w_pa = (4.0 / 3.0) * tau_y + plastic_viscosity_pa_s * shear_rate_s
    friction_dp_pa = (4.0 * pipe_length_m / pipe_diameter_m) * tau_w_pa
    static_dp_pa = rho_uf * gravity_m_s2 * static_elevation_head_m

    friction_pressure_bar = friction_dp_pa / 1e5
    static_pressure_bar = static_dp_pa / 1e5
    required_pressure_bar = friction_pressure_bar + static_pressure_bar
    pressure_margin_bar = available_pump_pressure_bar - required_pressure_bar
    is_pump_limited = required_pressure_bar > available_pump_pressure_bar
    pumpability_flag = "Pump-limited" if is_pump_limited else "Feasible"

    if is_pump_limited:
        binding_reason = (
            f"Required pressure ({required_pressure_bar:.2f} bar = "
            f"{friction_pressure_bar:.2f} bar friction + {static_pressure_bar:.2f} bar static head) "
            f"exceeds configured PD pump capability ({available_pump_pressure_bar:.2f} bar) "
            f"at yield stress {tau_y:.1f} Pa."
        )
    else:
        binding_reason = (
            f"Feasible: required pressure {required_pressure_bar:.2f} bar is within configured "
            f"pump capability {available_pump_pressure_bar:.2f} bar (margin {pressure_margin_bar:.2f} bar)."
        )

    max_pumpable_wt_pct: Optional[float] = None
    if compute_max_solids:
        def _margin_at_wt(w: float) -> float:
            res = evaluate_pumpability(
                underflow_solids_wt_pct=w,
                underflow_slurry_tph=underflow_slurry_tph,
                available_pump_pressure_bar=available_pump_pressure_bar,
                pipe_length_m=pipe_length_m,
                pipe_diameter_m=pipe_diameter_m,
                static_elevation_head_m=static_elevation_head_m,
                plastic_viscosity_pa_s=plastic_viscosity_pa_s,
                rheology_a_pa=rheology_a_pa,
                rheology_b=rheology_b,
                solids_density_kg_m3=solids_density_kg_m3,
                liquid_density_kg_m3=liquid_density_kg_m3,
                gravity_m_s2=gravity_m_s2,
                compute_max_solids=False,
            )
            return float(res["pressure_margin_bar"])

        low, high = 30.0, 78.0
        f_low, f_high = _margin_at_wt(low), _margin_at_wt(high)
        if f_low <= 0.0:
            max_pumpable_wt_pct = low
        elif f_high >= 0.0:
            max_pumpable_wt_pct = high
        else:
            max_pumpable_wt_pct = float(brentq(_margin_at_wt, low, high, xtol=1e-3))

    return {
        "underflow_solids_wt_pct": float(underflow_solids_wt_pct),
        "slurry_density_kg_m3": float(rho_uf),
        "yield_stress_pa": tau_y,
        "pipe_velocity_m_s": float(pipe_velocity_m_s),
        "friction_pressure_bar": float(friction_pressure_bar),
        "static_pressure_bar": float(static_pressure_bar),
        "required_pump_pressure_bar": float(required_pressure_bar),
        "available_pump_pressure_bar": float(available_pump_pressure_bar),
        "pressure_margin_bar": float(pressure_margin_bar),
        "is_pump_limited": bool(is_pump_limited),
        "pumpability_flag": pumpability_flag,
        "binding_reason": binding_reason,
        "max_pumpable_solids_wt_pct": max_pumpable_wt_pct,
        "calibration_status": "SYNTHETIC_ASSUMED",
    }


def compute_pumpability_curve(
    underflow_slurry_tph: float,
    available_pump_pressure_bar: float = 15.0,
    pipe_length_m: float = 300.0,
    pipe_diameter_m: float = 0.20,
    static_elevation_head_m: float = 15.0,
    plastic_viscosity_pa_s: float = 0.08,
    rheology_a_pa: float = 0.055,
    rheology_b: float = 21.3,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    min_wt_pct: float = 50.0,
    max_wt_pct: float = 72.0,
    n_points: int = 60,
) -> Dict[str, Any]:
    """Generate yield-stress and required-pressure curves across underflow % solids."""
    wt_grid = np.linspace(min_wt_pct, max_wt_pct, n_points)
    yield_list = []
    req_p_list = []
    friction_list = []
    static_list = []

    for w in wt_grid:
        res = evaluate_pumpability(
            underflow_solids_wt_pct=float(w),
            underflow_slurry_tph=underflow_slurry_tph,
            available_pump_pressure_bar=available_pump_pressure_bar,
            pipe_length_m=pipe_length_m,
            pipe_diameter_m=pipe_diameter_m,
            static_elevation_head_m=static_elevation_head_m,
            plastic_viscosity_pa_s=plastic_viscosity_pa_s,
            rheology_a_pa=rheology_a_pa,
            rheology_b=rheology_b,
            solids_density_kg_m3=solids_density_kg_m3,
            liquid_density_kg_m3=liquid_density_kg_m3,
            compute_max_solids=False,
        )
        yield_list.append(res["yield_stress_pa"])
        req_p_list.append(res["required_pump_pressure_bar"])
        friction_list.append(res["friction_pressure_bar"])
        static_list.append(res["static_pressure_bar"])

    return {
        "underflow_solids_wt_pct": wt_grid.tolist(),
        "yield_stress_pa": yield_list,
        "required_pump_pressure_bar": req_p_list,
        "friction_pressure_bar": friction_list,
        "static_pressure_bar": static_list,
        "available_pump_pressure_bar": float(available_pump_pressure_bar),
    }
