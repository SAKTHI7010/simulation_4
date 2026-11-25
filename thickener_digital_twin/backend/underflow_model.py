"""Underflow solids concentration predictor combining compaction & mass balance."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional


def predict_underflow_solids(
    dry_solids_feed_tph: float,
    feed_solids_wt_pct: float,
    underflow_withdrawal_tph: float,
    underflow_basis: Literal["slurry", "dry_solids"],
    area_utilization_ratio: float,
    bed_level_m: float,
    floc_modifier: float,
    compaction_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Predict achievable underflow % solids subject to settling-flux compaction and mass balance."""
    if underflow_withdrawal_tph <= 0.0:
        raise ValueError(f"underflow_withdrawal_tph must be positive, got {underflow_withdrawal_tph}")

    cfg = compaction_params or {}
    base_uf = float(cfg.get("base_underflow_wt_pct", 63.0))
    ref_util = float(cfg.get("ref_flux_loading_ratio", 0.70))
    k_flux = float(cfg.get("flux_loading_sensitivity", 8.5))
    ref_bed = float(cfg.get("ref_bed_level_m", 1.5))
    k_bed = float(cfg.get("bed_level_sensitivity", 2.5))
    ref_floc = float(cfg.get("ref_floc_modifier", 1.15))
    k_floc = float(cfg.get("floc_compaction_sensitivity", 4.0))
    opt_feed = float(cfg.get("opt_feed_solids_wt_pct", 10.0))
    k_feed = float(cfg.get("feed_solids_penalty", 0.25))
    min_uf = float(cfg.get("min_underflow_wt_pct", 40.0))
    max_uf = float(cfg.get("max_underflow_wt_pct", 72.0))

    raw_compaction = (
        base_uf
        - k_flux * (area_utilization_ratio - ref_util)
        + k_bed * (bed_level_m - ref_bed)
        + k_floc * (floc_modifier - ref_floc)
        - k_feed * abs(feed_solids_wt_pct - opt_feed)
    )
    compaction_limit_wt_pct = max(feed_solids_wt_pct, max(min_uf, min(max_uf, float(raw_compaction))))

    if underflow_basis == "slurry":
        underflow_slurry_tph = float(underflow_withdrawal_tph)
        mass_balance_target_wt_pct = min(95.0, 100.0 * dry_solids_feed_tph / underflow_slurry_tph)
        predicted_wt_pct = max(
            feed_solids_wt_pct,
            min(compaction_limit_wt_pct, mass_balance_target_wt_pct),
        )
        outgoing_dry_solids_tph = underflow_slurry_tph * (predicted_wt_pct / 100.0)
        if area_utilization_ratio > 1.0:
            limiting_regime = "Area/Flux overloaded"
        elif mass_balance_target_wt_pct < compaction_limit_wt_pct - 0.15:
            limiting_regime = "Withdrawal-rate limited (excess volumetric pull)"
        elif compaction_limit_wt_pct < mass_balance_target_wt_pct - 0.15:
            limiting_regime = "Compaction / flux limited (solids accumulating)"
        else:
            limiting_regime = "Balanced"
    elif underflow_basis == "dry_solids":
        predicted_wt_pct = compaction_limit_wt_pct
        mass_balance_target_wt_pct = compaction_limit_wt_pct
        outgoing_dry_solids_tph = float(underflow_withdrawal_tph)
        underflow_slurry_tph = outgoing_dry_solids_tph / (predicted_wt_pct / 100.0)
        if area_utilization_ratio > 1.0:
            limiting_regime = "Area/Flux overloaded"
        else:
            limiting_regime = "Dry-solids controlled"
    else:
        raise ValueError(f"Unknown underflow_basis '{underflow_basis}'.")

    net_solids_accumulation_tph = dry_solids_feed_tph - outgoing_dry_solids_tph

    return {
        "predicted_underflow_solids_wt_pct": float(predicted_wt_pct),
        "compaction_limit_wt_pct": float(compaction_limit_wt_pct),
        "mass_balance_target_wt_pct": float(mass_balance_target_wt_pct),
        "underflow_slurry_tph": float(underflow_slurry_tph),
        "outgoing_dry_solids_tph": float(outgoing_dry_solids_tph),
        "net_solids_accumulation_tph": float(net_solids_accumulation_tph),
        "limiting_regime": limiting_regime,
        "calibration_status": "SYNTHETIC_ASSUMED",
    }
