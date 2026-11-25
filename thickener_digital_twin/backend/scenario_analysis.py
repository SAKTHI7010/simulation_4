"""Baseline vs modified operating-scenario comparison (Project 4 operator question)."""

from __future__ import annotations

from typing import Any, Dict

from backend.bed_dynamics import run_bed_dynamics_simulation
from backend.config_loader import get_default_values
from backend.flux_model import compute_flux_curve
from backend.simulator import simulate_operating_point


def _extract_kpis(sim: Dict[str, Any], bed_4h: float, bed_8h: float) -> Dict[str, Any]:
    return {
        "dry_solids_feed_tph": sim["inputs_summary"]["dry_solids_feed_tph"],
        "slurry_feed_tph": sim["inputs_summary"]["slurry_feed_tph"],
        "feed_solids_wt_pct": sim["inputs_summary"]["feed_solids_wt_pct"],
        "flocculant_dose_gpt": sim["inputs_summary"]["flocculant_dose_gpt"],
        "flocculant_modifier": sim["settling_and_flux"]["flocculant_modifier"],
        "limiting_flux_kg_m2_h": sim["settling_and_flux"]["limiting_flux_kg_m2_h"],
        "required_area_m2": sim["area_sizing"]["required_area_m2"],
        "area_utilization_pct": sim["area_sizing"]["area_utilization_ratio"] * 100.0,
        "predicted_underflow_solids_wt_pct": sim["underflow"]["predicted_underflow_solids_wt_pct"],
        "net_solids_accumulation_tph": sim["underflow"]["net_solids_accumulation_tph"],
        "overflow_clarity_index": sim["overflow_clarity"]["overflow_clarity_index"],
        "yield_stress_pa": sim["pumpability"]["yield_stress_pa"],
        "required_pump_pressure_bar": sim["pumpability"]["required_pump_pressure_bar"],
        "available_pump_pressure_bar": sim["pumpability"]["available_pump_pressure_bar"],
        "pumpability_flag": sim["pumpability"]["pumpability_flag"],
        "is_pump_limited": sim["pumpability"]["is_pump_limited"],
        "projected_bed_level_4h_m": bed_4h,
        "projected_bed_level_8h_m": bed_8h,
    }


def run_scenario_comparison(
    baseline_params: Dict[str, Any],
    modified_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare baseline and modified operating points, flux curves, and bed trajectories."""
    defaults = get_default_values()
    base_full = {**defaults, **{k: v for k, v in baseline_params.items() if v is not None}}
    mod_full = {**base_full, **{k: v for k, v in modified_params.items() if v is not None}}

    base_sim = simulate_operating_point(base_full)
    mod_sim = simulate_operating_point(mod_full)

    def _flux_for(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return compute_flux_curve(
            v0_base_mph=float(cfg["free_settling_velocity_mph"]),
            rz_exponent_n=float(cfg["rz_exponent_n"]),
            flocculant_dose_gpt=float(cfg["flocculant_dose_gpt"]),
            solids_density_kg_m3=float(cfg["solids_density_kg_m3"]),
            liquid_density_kg_m3=float(cfg["liquid_density_kg_m3"]),
            floc_model_type=cfg["model_type"],
            floc_params={
                "min_modifier": cfg["min_modifier"],
                "max_modifier": cfg["max_modifier"],
                "characteristic_dose_gpt": cfg["characteristic_dose_gpt"],
                "power_k": cfg["power_k"],
                "power_ref_dose_gpt": cfg["power_ref_dose_gpt"],
                "power_alpha": cfg["power_alpha"],
            },
            phi_max=float(cfg["phi_grid_max"]),
            n_points=int(cfg["phi_grid_points"]),
        )

    base_flux = _flux_for(base_full)
    mod_flux = _flux_for(mod_full)

    # 8-hour dynamic projections with immediate step at t=0
    def _dyn_proj(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return run_bed_dynamics_simulation(
            feed_rate_tph=float(cfg["feed_rate_tph"]),
            feed_rate_basis=cfg["feed_rate_basis"],
            feed_solids_wt_pct=float(cfg["feed_solids_wt_pct"]),
            flocculant_dose_gpt=float(cfg["flocculant_dose_gpt"]),
            underflow_withdrawal_tph=float(cfg["underflow_withdrawal_tph"]),
            underflow_basis=cfg["underflow_basis"],
            initial_bed_level_m=float(cfg["bed_level_m"]),
            thickener_area_m2=float(cfg["thickener_area_m2"]),
            tank_depth_m=float(cfg["tank_depth_m"]),
            bed_average_solids_wt_pct=float(cfg["bed_average_solids_wt_pct"]),
            bed_time_constant_h=float(cfg["bed_time_constant_h"]),
            v0_base_mph=float(cfg["free_settling_velocity_mph"]),
            rz_exponent_n=float(cfg["rz_exponent_n"]),
            floc_model_type=cfg["model_type"],
            duration_h=8.0,
            step_time_h=0.0,
            feed_rate_step_pct=0.0,
            underflow_withdrawal_step_pct=0.0,
            flocculant_dose_step_pct=0.0,
            n_output_points=41,
            solids_density_kg_m3=float(cfg["solids_density_kg_m3"]),
            liquid_density_kg_m3=float(cfg["liquid_density_kg_m3"]),
            available_pump_pressure_bar=float(cfg["available_pump_pressure_bar"]),
            pipe_length_m=float(cfg["pipe_length_m"]),
            pipe_diameter_m=float(cfg["pipe_diameter_m"]),
            static_elevation_head_m=float(cfg["static_elevation_head_m"]),
            plastic_viscosity_pa_s=float(cfg["plastic_viscosity_pa_s"]),
            rheology_a_pa=float(cfg["rheology_a_pa"]),
            rheology_b=float(cfg["rheology_b"]),
        )

    base_dyn = _dyn_proj(base_full)
    mod_dyn = _dyn_proj(mod_full)
    idx_4h = 20  # 4.0h out of 8.0h with 41 points

    base_kpis = _extract_kpis(base_sim, base_dyn["bed_level_m"][idx_4h], base_dyn["bed_level_m"][-1])
    mod_kpis = _extract_kpis(mod_sim, mod_dyn["bed_level_m"][idx_4h], mod_dyn["bed_level_m"][-1])

    numeric_keys = [
        "dry_solids_feed_tph",
        "flocculant_dose_gpt",
        "limiting_flux_kg_m2_h",
        "required_area_m2",
        "area_utilization_pct",
        "predicted_underflow_solids_wt_pct",
        "net_solids_accumulation_tph",
        "overflow_clarity_index",
        "yield_stress_pa",
        "required_pump_pressure_bar",
        "projected_bed_level_4h_m",
        "projected_bed_level_8h_m",
    ]
    deltas: Dict[str, Dict[str, float]] = {}
    for k in numeric_keys:
        b_val = float(base_kpis[k])
        m_val = float(mod_kpis[k])
        abs_d = m_val - b_val
        pct_d = (abs_d / b_val * 100.0) if abs(b_val) > 1e-9 else 0.0
        deltas[k] = {"baseline": b_val, "modified": m_val, "abs_delta": abs_d, "pct_delta": pct_d}

    verdict_parts = []
    if mod_sim["pumpability"]["is_pump_limited"]:
        verdict_parts.append(
            f"PUMPABILITY VIOLATION: Modified scenario requires {mod_kpis['required_pump_pressure_bar']:.2f} bar "
            f"vs {mod_kpis['available_pump_pressure_bar']:.2f} bar available — target is PUMP-LIMITED."
        )
    if mod_sim["area_sizing"]["is_area_limited"]:
        verdict_parts.append(
            f"SETTLING CAPACITY EXCEEDED: Required area ({mod_kpis['required_area_m2']:.1f} m2) exceeds "
            f"installed area ({mod_full['thickener_area_m2']:.1f} m2), causing solids accumulation and bed rise "
            f"to {mod_kpis['projected_bed_level_8h_m']:.2f} m over 8 h."
        )
    if not verdict_parts:
        verdict_parts.append(
            f"FEASIBLE WITH DEGRADATION CHECK: Underflow solids shifts from "
            f"{base_kpis['predicted_underflow_solids_wt_pct']:.1f}% to "
            f"{mod_kpis['predicted_underflow_solids_wt_pct']:.1f}% w/w; "
            f"clarity proxy changes by {deltas['overflow_clarity_index']['abs_delta']:+.1f} points "
            f"and 8-h bed level moves to {mod_kpis['projected_bed_level_8h_m']:.2f} m."
        )

    return {
        "data_status": base_sim["data_status"],
        "baseline": {
            "kpis": base_kpis,
            "warnings": base_sim["warnings"],
            "flux_curve": {
                "phi": base_flux["phi"],
                "flux_kg_m2_h": base_flux["flux_kg_m2_h"],
                "limiting_flux_kg_m2_h": base_flux["limiting_flux_kg_m2_h"],
            },
            "bed_projection": {
                "time_h": base_dyn["time_h"],
                "bed_level_m": base_dyn["bed_level_m"],
                "underflow_solids_wt_pct": base_dyn["underflow_solids_wt_pct"],
            },
        },
        "modified": {
            "kpis": mod_kpis,
            "warnings": mod_sim["warnings"],
            "flux_curve": {
                "phi": mod_flux["phi"],
                "flux_kg_m2_h": mod_flux["flux_kg_m2_h"],
                "limiting_flux_kg_m2_h": mod_flux["limiting_flux_kg_m2_h"],
            },
            "bed_projection": {
                "time_h": mod_dyn["time_h"],
                "bed_level_m": mod_dyn["bed_level_m"],
                "underflow_solids_wt_pct": mod_dyn["underflow_solids_wt_pct"],
            },
        },
        "deltas": deltas,
        "operator_verdict": " ".join(verdict_parts),
    }
