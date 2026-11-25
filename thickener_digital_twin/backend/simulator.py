"""Unified single-point thickener simulation pipeline combining all process sub-models."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.config_loader import get_default_values, load_raw_config
from backend.flux_model import compute_flux_curve
from backend.overflow_clarity import compute_overflow_clarity_proxy
from backend.pumpability import evaluate_pumpability
from backend.settling_velocity import richardson_zaki_velocity
from backend.thickener_area import compute_required_area
from backend.underflow_model import predict_underflow_solids
from backend.unit_conversions import resolve_mass_rates, wt_pct_to_volume_fraction
from backend.validation import check_calibration_warnings


def simulate_operating_point(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete steady-state / instantaneous thickener evaluation for an input dict."""
    defaults = get_default_values()
    raw_cfg = load_raw_config()
    p = {**defaults, **{k: v for k, v in params.items() if v is not None}}

    rho_s = float(p["solids_density_kg_m3"])
    rho_l = float(p["liquid_density_kg_m3"])
    g = float(p["gravity_m_s2"])

    feed_solids_wt_pct = float(p["feed_solids_wt_pct"])
    dry_in_tph, slurry_in_tph = resolve_mass_rates(
        float(p["feed_rate_tph"]), feed_solids_wt_pct, p["feed_rate_basis"]
    )
    phi_feed = wt_pct_to_volume_fraction(feed_solids_wt_pct, rho_s, rho_l)

    floc_params = {
        "min_modifier": p["min_modifier"],
        "max_modifier": p["max_modifier"],
        "characteristic_dose_gpt": p["characteristic_dose_gpt"],
        "power_k": p["power_k"],
        "power_ref_dose_gpt": p["power_ref_dose_gpt"],
        "power_alpha": p["power_alpha"],
    }
    flux_res = compute_flux_curve(
        v0_base_mph=float(p["free_settling_velocity_mph"]),
        rz_exponent_n=float(p["rz_exponent_n"]),
        flocculant_dose_gpt=float(p["flocculant_dose_gpt"]),
        solids_density_kg_m3=rho_s,
        liquid_density_kg_m3=rho_l,
        floc_model_type=p["model_type"],
        floc_params=floc_params,
        phi_max=float(p["phi_grid_max"]),
        n_points=int(p["phi_grid_points"]),
    )

    feed_settling_vel_mph = float(
        richardson_zaki_velocity(phi_feed, flux_res["v0_effective_mph"], float(p["rz_exponent_n"]))
    )

    area_res = compute_required_area(
        dry_solids_feed_tph=dry_in_tph,
        limiting_flux_kg_m2_h=flux_res["limiting_flux_kg_m2_h"],
        actual_area_m2=float(p["thickener_area_m2"]),
    )

    compaction_params = {
        "base_underflow_wt_pct": p["base_underflow_wt_pct"],
        "ref_flux_loading_ratio": p["ref_flux_loading_ratio"],
        "flux_loading_sensitivity": p["flux_loading_sensitivity"],
        "ref_bed_level_m": p["ref_bed_level_m"],
        "bed_level_sensitivity": p["bed_level_sensitivity"],
        "ref_floc_modifier": p["ref_floc_modifier"],
        "floc_compaction_sensitivity": p["floc_compaction_sensitivity"],
        "opt_feed_solids_wt_pct": p["opt_feed_solids_wt_pct"],
        "feed_solids_penalty": p["feed_solids_penalty"],
        "min_underflow_wt_pct": p["min_underflow_wt_pct"],
        "max_underflow_wt_pct": p["max_underflow_wt_pct"],
    }
    uf_res = predict_underflow_solids(
        dry_solids_feed_tph=dry_in_tph,
        feed_solids_wt_pct=feed_solids_wt_pct,
        underflow_withdrawal_tph=float(p["underflow_withdrawal_tph"]),
        underflow_basis=p["underflow_basis"],
        area_utilization_ratio=float(area_res["area_utilization_ratio"]),
        bed_level_m=float(p["bed_level_m"]),
        floc_modifier=flux_res["flocculant_info"]["modifier"],
        compaction_params=compaction_params,
    )

    clarity_params = {
        "c_rise_ratio": p["c_rise_ratio"],
        "c_flux_overload": p["c_flux_overload"],
        "c_bed_freeboard": p["c_bed_freeboard"],
        "c_floc_deficit": p["c_floc_deficit"],
    }
    clarity_res = compute_overflow_clarity_proxy(
        feed_slurry_tph=slurry_in_tph,
        feed_solids_wt_pct=feed_solids_wt_pct,
        underflow_slurry_tph=uf_res["underflow_slurry_tph"],
        underflow_solids_wt_pct=uf_res["predicted_underflow_solids_wt_pct"],
        actual_area_m2=float(p["thickener_area_m2"]),
        area_utilization_ratio=float(area_res["area_utilization_ratio"]),
        bed_level_m=float(p["bed_level_m"]),
        tank_depth_m=float(p["tank_depth_m"]),
        v0_effective_mph=flux_res["v0_effective_mph"],
        rz_exponent_n=float(p["rz_exponent_n"]),
        floc_modifier=flux_res["flocculant_info"]["modifier"],
        solids_density_kg_m3=rho_s,
        liquid_density_kg_m3=rho_l,
        clarity_params=clarity_params,
    )

    pump_res = evaluate_pumpability(
        underflow_solids_wt_pct=uf_res["predicted_underflow_solids_wt_pct"],
        underflow_slurry_tph=uf_res["underflow_slurry_tph"],
        available_pump_pressure_bar=float(p["available_pump_pressure_bar"]),
        pipe_length_m=float(p["pipe_length_m"]),
        pipe_diameter_m=float(p["pipe_diameter_m"]),
        static_elevation_head_m=float(p["static_elevation_head_m"]),
        plastic_viscosity_pa_s=float(p["plastic_viscosity_pa_s"]),
        rheology_a_pa=float(p["rheology_a_pa"]),
        rheology_b=float(p["rheology_b"]),
        solids_density_kg_m3=rho_s,
        liquid_density_kg_m3=rho_l,
        gravity_m_s2=g,
        compute_max_solids=True,
    )

    warnings = check_calibration_warnings(
        feed_solids_wt_pct=feed_solids_wt_pct,
        flocculant_dose_gpt=float(p["flocculant_dose_gpt"]),
        predicted_underflow_wt_pct=uf_res["predicted_underflow_solids_wt_pct"],
        area_utilization_ratio=float(area_res["area_utilization_ratio"]),
        bed_level_m=float(p["bed_level_m"]),
        tank_depth_m=float(p["tank_depth_m"]),
        bed_high_alarm_m=float(p["bed_high_alarm_m"]),
        bed_low_alarm_m=float(p["bed_low_alarm_m"]),
        is_pump_limited=bool(pump_res["is_pump_limited"]),
        reference_ranges=raw_cfg.get("reference_ranges"),
    )

    return {
        "data_status": raw_cfg["metadata"]["data_status"],
        "disclaimer": raw_cfg["metadata"]["disclaimer"],
        "inputs_summary": {
            "feed_rate_tph": float(p["feed_rate_tph"]),
            "feed_rate_basis": p["feed_rate_basis"],
            "dry_solids_feed_tph": dry_in_tph,
            "slurry_feed_tph": slurry_in_tph,
            "feed_solids_wt_pct": feed_solids_wt_pct,
            "feed_volume_fraction_phi": phi_feed,
            "flocculant_dose_gpt": float(p["flocculant_dose_gpt"]),
            "underflow_withdrawal_tph": float(p["underflow_withdrawal_tph"]),
            "underflow_basis": p["underflow_basis"],
            "bed_level_m": float(p["bed_level_m"]),
            "thickener_area_m2": float(p["thickener_area_m2"]),
            "tank_depth_m": float(p["tank_depth_m"]),
        },
        "settling_and_flux": {
            "v0_base_mph": float(p["free_settling_velocity_mph"]),
            "v0_effective_mph": flux_res["v0_effective_mph"],
            "rz_exponent_n": float(p["rz_exponent_n"]),
            "flocculant_modifier": flux_res["flocculant_info"]["modifier"],
            "flocculant_model_type": p["model_type"],
            "feed_settling_velocity_mph": feed_settling_vel_mph,
            "limiting_flux_kg_m2_h": flux_res["limiting_flux_kg_m2_h"],
            "limiting_flux_t_m2_h": flux_res["limiting_flux_t_m2_h"],
            "phi_at_limiting_flux": flux_res["phi_at_limiting_flux"],
            "wt_pct_at_limiting_flux": flux_res["wt_pct_at_limiting_flux"],
        },
        "area_sizing": area_res,
        "underflow": uf_res,
        "overflow_clarity": clarity_res,
        "pumpability": pump_res,
        "warnings": warnings,
    }
