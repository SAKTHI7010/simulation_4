"""Dynamic solids-inventory balance and mud-bed level ODE simulation (SciPy solve_ivp)."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

import numpy as np
from scipy.integrate import solve_ivp

from backend.flux_model import compute_flux_curve
from backend.overflow_clarity import compute_overflow_clarity_proxy
from backend.pumpability import evaluate_pumpability
from backend.thickener_area import compute_required_area
from backend.underflow_model import predict_underflow_solids
from backend.unit_conversions import resolve_mass_rates, wt_pct_to_volume_fraction


def run_bed_dynamics_simulation(
    feed_rate_tph: float,
    feed_rate_basis: Literal["dry_solids", "slurry"],
    feed_solids_wt_pct: float,
    flocculant_dose_gpt: float,
    underflow_withdrawal_tph: float,
    underflow_basis: Literal["slurry", "dry_solids"],
    initial_bed_level_m: float,
    thickener_area_m2: float,
    tank_depth_m: float,
    bed_average_solids_wt_pct: float,
    bed_time_constant_h: float,
    v0_base_mph: float,
    rz_exponent_n: float,
    floc_model_type: Literal["exponential", "power_law"],
    duration_h: float = 12.0,
    step_time_h: float = 2.0,
    feed_rate_step_pct: float = 20.0,
    underflow_withdrawal_step_pct: float = 0.0,
    flocculant_dose_step_pct: float = -50.0,
    n_output_points: int = 121,
    solids_density_kg_m3: float = 3200.0,
    liquid_density_kg_m3: float = 1000.0,
    available_pump_pressure_bar: float = 15.0,
    pipe_length_m: float = 300.0,
    pipe_diameter_m: float = 0.20,
    static_elevation_head_m: float = 15.0,
    plastic_viscosity_pa_s: float = 0.08,
    rheology_a_pa: float = 0.055,
    rheology_b: float = 21.3,
    floc_params: Optional[Dict[str, Any]] = None,
    compaction_params: Optional[Dict[str, Any]] = None,
    clarity_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Integrate dynamic solids inventory M_bed(t) and underflow density w_u(t).

    Solids inventory balance:
        dM_bed / dt = incoming_dry_solids(t) - outgoing_dry_solids(t) - overflow_loss(t)
        h_bed(t) = M_bed(t) / (A * rho_dry_bed)
    """
    if duration_h <= 0.0:
        raise ValueError("duration_h must be positive.")
    if bed_time_constant_h <= 0.0:
        raise ValueError("bed_time_constant_h must be positive.")
    if not (0.0 <= initial_bed_level_m <= tank_depth_m):
        raise ValueError(f"initial_bed_level_m must be in [0, {tank_depth_m}].")

    phi_bed = wt_pct_to_volume_fraction(
        bed_average_solids_wt_pct, solids_density_kg_m3, liquid_density_kg_m3
    )
    rho_dry_bed_t_m3 = phi_bed * (solids_density_kg_m3 / 1000.0)
    max_bed_inventory_t = thickener_area_m2 * tank_depth_m * rho_dry_bed_t_m3
    initial_inventory_t = thickener_area_m2 * initial_bed_level_m * rho_dry_bed_t_m3

    # Pre-compute regime evaluations for pre-step and post-step operating conditions
    def _regime_inputs(after_step: bool) -> Dict[str, Any]:
        f_mult = (1.0 + feed_rate_step_pct / 100.0) if after_step else 1.0
        u_mult = (1.0 + underflow_withdrawal_step_pct / 100.0) if after_step else 1.0
        d_mult = (1.0 + flocculant_dose_step_pct / 100.0) if after_step else 1.0

        f_rate = max(1e-3, feed_rate_tph * f_mult)
        u_rate = max(1e-3, underflow_withdrawal_tph * u_mult)
        f_dose = max(0.0, flocculant_dose_gpt * d_mult)

        dry_in_tph, slurry_in_tph = resolve_mass_rates(f_rate, feed_solids_wt_pct, feed_rate_basis)
        flux_res = compute_flux_curve(
            v0_base_mph=v0_base_mph,
            rz_exponent_n=rz_exponent_n,
            flocculant_dose_gpt=f_dose,
            solids_density_kg_m3=solids_density_kg_m3,
            liquid_density_kg_m3=liquid_density_kg_m3,
            floc_model_type=floc_model_type,
            floc_params=floc_params,
        )
        area_res = compute_required_area(
            dry_solids_feed_tph=dry_in_tph,
            limiting_flux_kg_m2_h=flux_res["limiting_flux_kg_m2_h"],
            actual_area_m2=thickener_area_m2,
        )
        return {
            "feed_rate_tph": f_rate,
            "dry_in_tph": dry_in_tph,
            "slurry_in_tph": slurry_in_tph,
            "u_rate_tph": u_rate,
            "floc_dose_gpt": f_dose,
            "v0_effective_mph": flux_res["v0_effective_mph"],
            "floc_modifier": flux_res["flocculant_info"]["modifier"],
            "area_utilization_ratio": float(area_res["area_utilization_ratio"]),
        }

    pre_reg = _regime_inputs(after_step=False)
    post_reg = _regime_inputs(after_step=True)

    # Initial steady-like underflow concentration at t = 0
    uf_init = predict_underflow_solids(
        dry_solids_feed_tph=pre_reg["dry_in_tph"],
        feed_solids_wt_pct=feed_solids_wt_pct,
        underflow_withdrawal_tph=pre_reg["u_rate_tph"],
        underflow_basis=underflow_basis,
        area_utilization_ratio=pre_reg["area_utilization_ratio"],
        bed_level_m=initial_bed_level_m,
        floc_modifier=pre_reg["floc_modifier"],
        compaction_params=compaction_params,
    )
    w_u_init = uf_init["predicted_underflow_solids_wt_pct"]

    def _rates_at_state(m_bed: float, w_u: float, reg: Dict[str, Any]) -> tuple[float, float, float, float, float]:
        h_bed = max(0.0, min(tank_depth_m, m_bed / (thickener_area_m2 * rho_dry_bed_t_m3)))
        uf = predict_underflow_solids(
            dry_solids_feed_tph=reg["dry_in_tph"],
            feed_solids_wt_pct=feed_solids_wt_pct,
            underflow_withdrawal_tph=reg["u_rate_tph"],
            underflow_basis=underflow_basis,
            area_utilization_ratio=reg["area_utilization_ratio"],
            bed_level_m=h_bed,
            floc_modifier=reg["floc_modifier"],
            compaction_params=compaction_params,
        )
        w_u_target = uf["predicted_underflow_solids_wt_pct"]
        if underflow_basis == "slurry":
            uf_slurry_tph = reg["u_rate_tph"]
            m_out_tph = uf_slurry_tph * (w_u / 100.0)
        else:
            m_out_tph = reg["u_rate_tph"]
            uf_slurry_tph = m_out_tph / max(w_u / 100.0, 1e-3)

        m_in_tph = reg["dry_in_tph"]
        m_overflow_tph = 0.0
        dm_dt = m_in_tph - m_out_tph

        if m_bed <= 0.0 and dm_dt < 0.0:
            m_out_tph = m_in_tph
            dm_dt = 0.0
        elif m_bed >= max_bed_inventory_t and dm_dt > 0.0:
            m_overflow_tph = dm_dt
            dm_dt = 0.0

        return dm_dt, w_u_target, m_out_tph, m_overflow_tph, uf_slurry_tph

    def _make_ode(reg: Dict[str, Any]):
        def _ode(_t: float, y: np.ndarray) -> list[float]:
            m_bed, w_u = float(y[0]), float(y[1])
            dm_dt, w_u_target, _, _, _ = _rates_at_state(m_bed, w_u, reg)
            dw_dt = (w_u_target - w_u) / bed_time_constant_h
            return [dm_dt, dw_dt]
        return _ode

    t_grid = np.linspace(0.0, duration_h, n_output_points)
    y0 = np.array([initial_inventory_t, w_u_init], dtype=float)

    if 0.0 < step_time_h < duration_h:
        t_pre = t_grid[t_grid <= step_time_h]
        if t_pre[-1] < step_time_h:
            t_pre_eval = np.append(t_pre, step_time_h)
        else:
            t_pre_eval = t_pre

        sol_pre = solve_ivp(
            _make_ode(pre_reg),
            (0.0, step_time_h),
            y0,
            t_eval=t_pre_eval,
            method="RK45",
            max_step=0.1,
            rtol=1e-6,
            atol=1e-8,
        )
        if not sol_pre.success:
            raise RuntimeError(f"ODE solver failed before step: {sol_pre.message}")

        y_step = sol_pre.y[:, -1]
        t_post = t_grid[t_grid > step_time_h]
        t_post_eval = np.insert(t_post, 0, step_time_h) if len(t_post) > 0 else np.array([step_time_h])

        sol_post = solve_ivp(
            _make_ode(post_reg),
            (step_time_h, duration_h),
            y_step,
            t_eval=t_post_eval,
            method="RK45",
            max_step=0.1,
            rtol=1e-6,
            atol=1e-8,
        )
        if not sol_post.success:
            raise RuntimeError(f"ODE solver failed after step: {sol_post.message}")

        # Reconstruct exact t_grid outputs
        m_series = np.concatenate([sol_pre.y[0, :len(t_pre)], sol_post.y[0, 1:]])
        w_series = np.concatenate([sol_pre.y[1, :len(t_pre)], sol_post.y[1, 1:]])
    else:
        active_reg = post_reg if step_time_h <= 0.0 else pre_reg
        sol = solve_ivp(
            _make_ode(active_reg),
            (0.0, duration_h),
            y0,
            t_eval=t_grid,
            method="RK45",
            max_step=0.1,
            rtol=1e-6,
            atol=1e-8,
        )
        if not sol.success:
            raise RuntimeError(f"ODE solver failed: {sol.message}")
        m_series = sol.y[0]
        w_series = sol.y[1]

    feed_dry_series = []
    feed_slurry_series = []
    uf_dry_series = []
    uf_slurry_series = []
    overflow_dry_series = []
    bed_level_series = []
    clarity_series = []
    pressure_series = []
    pump_limited_series = []

    for idx, t_val in enumerate(t_grid):
        reg = post_reg if t_val >= step_time_h else pre_reg
        m_bed = max(0.0, min(max_bed_inventory_t, float(m_series[idx])))
        w_u = float(w_series[idx])
        h_bed = max(0.0, min(tank_depth_m, m_bed / (thickener_area_m2 * rho_dry_bed_t_m3)))
        _, _, m_out_tph, m_of_tph, uf_slurry_tph = _rates_at_state(m_bed, w_u, reg)

        clarity = compute_overflow_clarity_proxy(
            feed_slurry_tph=reg["slurry_in_tph"],
            feed_solids_wt_pct=feed_solids_wt_pct,
            underflow_slurry_tph=uf_slurry_tph,
            underflow_solids_wt_pct=w_u,
            actual_area_m2=thickener_area_m2,
            area_utilization_ratio=reg["area_utilization_ratio"],
            bed_level_m=h_bed,
            tank_depth_m=tank_depth_m,
            v0_effective_mph=reg["v0_effective_mph"],
            rz_exponent_n=rz_exponent_n,
            floc_modifier=reg["floc_modifier"],
            solids_density_kg_m3=solids_density_kg_m3,
            liquid_density_kg_m3=liquid_density_kg_m3,
            clarity_params=clarity_params,
        )
        pump = evaluate_pumpability(
            underflow_solids_wt_pct=w_u,
            underflow_slurry_tph=uf_slurry_tph,
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

        feed_dry_series.append(float(reg["dry_in_tph"]))
        feed_slurry_series.append(float(reg["slurry_in_tph"]))
        uf_dry_series.append(float(m_out_tph))
        uf_slurry_series.append(float(uf_slurry_tph))
        overflow_dry_series.append(float(m_of_tph))
        bed_level_series.append(float(h_bed))
        clarity_series.append(float(clarity["overflow_clarity_index"]))
        pressure_series.append(float(pump["required_pump_pressure_bar"]))
        pump_limited_series.append(bool(pump["is_pump_limited"]))

    # Cumulative mass-balance check using trapezoidal integration
    cum_in = float(np.trapz(feed_dry_series, t_grid))
    cum_out = float(np.trapz(uf_dry_series, t_grid))
    cum_of = float(np.trapz(overflow_dry_series, t_grid))
    delta_inventory = float(m_series[-1] - m_series[0])
    balance_residual_t = cum_in - (cum_out + cum_of + delta_inventory)
    balance_error_pct = abs(balance_residual_t) / max(cum_in, 1e-6) * 100.0

    return {
        "time_h": t_grid.tolist(),
        "step_time_h": float(step_time_h),
        "feed_dry_solids_tph": feed_dry_series,
        "feed_slurry_tph": feed_slurry_series,
        "underflow_dry_solids_tph": uf_dry_series,
        "underflow_slurry_tph": uf_slurry_series,
        "overflow_solids_loss_tph": overflow_dry_series,
        "bed_inventory_t": np.clip(m_series, 0.0, max_bed_inventory_t).tolist(),
        "bed_level_m": bed_level_series,
        "underflow_solids_wt_pct": w_series.tolist(),
        "overflow_clarity_index": clarity_series,
        "required_pump_pressure_bar": pressure_series,
        "is_pump_limited": pump_limited_series,
        "tank_depth_m": float(tank_depth_m),
        "bed_average_solids_wt_pct": float(bed_average_solids_wt_pct),
        "bed_dry_density_t_m3": float(rho_dry_bed_t_m3),
        "mass_balance_check": {
            "cumulative_feed_dry_t": cum_in,
            "cumulative_underflow_dry_t": cum_out,
            "cumulative_overflow_dry_t": cum_of,
            "inventory_change_t": delta_inventory,
            "residual_t": float(balance_residual_t),
            "closure_error_pct": float(balance_error_pct),
            "closed_within_1pct": bool(balance_error_pct <= 1.0),
        },
        "summary": {
            "initial_bed_level_m": float(bed_level_series[0]),
            "final_bed_level_m": float(bed_level_series[-1]),
            "peak_bed_level_m": float(max(bed_level_series)),
            "initial_underflow_wt_pct": float(w_series[0]),
            "final_underflow_wt_pct": float(w_series[-1]),
            "final_clarity_index": float(clarity_series[-1]),
            "final_pump_pressure_bar": float(pressure_series[-1]),
            "ever_pump_limited": bool(any(pump_limited_series)),
        },
    }
