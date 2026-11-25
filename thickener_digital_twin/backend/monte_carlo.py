"""Reproducible Monte Carlo uncertainty analysis over feed and settling variability."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from backend.config_loader import get_default_values
from backend.simulator import simulate_operating_point


def run_monte_carlo(params: Dict[str, Any]) -> Dict[str, Any]:
    """Propagate feed-rate and optional settling-parameter uncertainty via Monte Carlo."""
    defaults = get_default_values()
    p = {**defaults, **{k: v for k, v in params.items() if v is not None}}

    n_sim = int(p.get("n_simulations", 1000))
    seed = int(p.get("random_seed", 42))
    if n_sim < 50 or n_sim > 10000:
        raise ValueError("n_simulations must be between 50 and 10000.")

    rng = np.random.default_rng(seed)

    base_feed_rate = float(p["feed_rate_tph"])
    base_feed_solids = float(p["feed_solids_wt_pct"])
    base_v0 = float(p["free_settling_velocity_mph"])
    base_n = float(p["rz_exponent_n"])

    cv_feed = max(0.0, float(p.get("feed_rate_cv_pct", 10.0))) / 100.0
    cv_solids = max(0.0, float(p.get("feed_solids_cv_pct", 5.0))) / 100.0
    cv_v0 = max(0.0, float(p.get("v0_cv_pct", 8.0))) / 100.0
    cv_n = max(0.0, float(p.get("rz_n_cv_pct", 3.0))) / 100.0

    feed_samples = np.clip(
        rng.normal(base_feed_rate, base_feed_rate * cv_feed, n_sim),
        max(1.0, 0.2 * base_feed_rate),
        3.0 * base_feed_rate,
    )
    solids_samples = np.clip(
        rng.normal(base_feed_solids, base_feed_solids * cv_solids, n_sim),
        0.5,
        35.0,
    )
    v0_samples = np.clip(
        rng.normal(base_v0, base_v0 * cv_v0, n_sim),
        0.5,
        5.0 * base_v0,
    )
    n_samples = np.clip(
        rng.normal(base_n, base_n * cv_n, n_sim),
        1.5,
        12.0,
    )

    uf_wt_pct = np.empty(n_sim, dtype=float)
    pump_pressure_bar = np.empty(n_sim, dtype=float)
    limiting_flux = np.empty(n_sim, dtype=float)
    area_util = np.empty(n_sim, dtype=float)
    clarity_idx = np.empty(n_sim, dtype=float)
    is_pump_limited = np.empty(n_sim, dtype=bool)
    is_area_limited = np.empty(n_sim, dtype=bool)

    max_pumpable_wt = None
    for i in range(n_sim):
        trial_p = dict(p)
        trial_p["feed_rate_tph"] = float(feed_samples[i])
        trial_p["feed_solids_wt_pct"] = float(solids_samples[i])
        trial_p["free_settling_velocity_mph"] = float(v0_samples[i])
        trial_p["rz_exponent_n"] = float(n_samples[i])

        res = simulate_operating_point(trial_p)
        uf_wt_pct[i] = res["underflow"]["predicted_underflow_solids_wt_pct"]
        pump_pressure_bar[i] = res["pumpability"]["required_pump_pressure_bar"]
        limiting_flux[i] = res["settling_and_flux"]["limiting_flux_kg_m2_h"]
        area_util[i] = res["area_sizing"]["area_utilization_ratio"]
        clarity_idx[i] = res["overflow_clarity"]["overflow_clarity_index"]
        is_pump_limited[i] = res["pumpability"]["is_pump_limited"]
        is_area_limited[i] = res["area_sizing"]["is_area_limited"]
        if i == 0:
            max_pumpable_wt = res["pumpability"]["max_pumpable_solids_wt_pct"]

    def _stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr, ddof=1)),
            "min": float(np.min(arr)),
            "p5": float(np.percentile(arr, 5)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "max": float(np.max(arr)),
        }

    return {
        "data_status": "SYNTHETIC_MONTE_CARLO",
        "n_simulations": n_sim,
        "random_seed": seed,
        "assumed_distributions": {
            "feed_rate_tph": {"dist": "Normal (clipped)", "mean": base_feed_rate, "cv_pct": cv_feed * 100.0},
            "feed_solids_wt_pct": {"dist": "Normal (clipped)", "mean": base_feed_solids, "cv_pct": cv_solids * 100.0},
            "free_settling_velocity_mph": {"dist": "Normal (clipped)", "mean": base_v0, "cv_pct": cv_v0 * 100.0},
            "rz_exponent_n": {"dist": "Normal (clipped)", "mean": base_n, "cv_pct": cv_n * 100.0},
        },
        "underflow_solids_stats": _stats(uf_wt_pct),
        "pump_pressure_stats": _stats(pump_pressure_bar),
        "limiting_flux_stats": _stats(limiting_flux),
        "clarity_proxy_stats": _stats(clarity_idx),
        "pumpability_violation_probability_pct": float(np.mean(is_pump_limited) * 100.0),
        "area_overload_probability_pct": float(np.mean(is_area_limited) * 100.0),
        "available_pump_pressure_bar": float(p["available_pump_pressure_bar"]),
        "max_pumpable_solids_wt_pct": max_pumpable_wt,
        "samples": {
            "feed_rate_tph": feed_samples.tolist(),
            "feed_solids_wt_pct": solids_samples.tolist(),
            "underflow_solids_wt_pct": uf_wt_pct.tolist(),
            "pump_pressure_bar": pump_pressure_bar.tolist(),
            "is_pump_limited": is_pump_limited.tolist(),
            "area_utilization_ratio": area_util.tolist(),
        },
    }
