"""Thickener sizing and area-utilization calculation on dry-solids mass basis."""

from __future__ import annotations

from typing import Dict


def compute_required_area(
    dry_solids_feed_tph: float,
    limiting_flux_kg_m2_h: float,
    actual_area_m2: float,
) -> Dict[str, float | bool]:
    """Calculate required thickener area A_req = dry_solids_mass_rate / F_lim.

    Uses dry-solids mass rate in kg/h divided by limiting flux in kg/(m2*h).
    """
    if dry_solids_feed_tph < 0.0:
        raise ValueError(f"dry_solids_feed_tph must be non-negative, got {dry_solids_feed_tph}")
    if limiting_flux_kg_m2_h <= 0.0:
        raise ValueError(f"limiting_flux_kg_m2_h must be positive, got {limiting_flux_kg_m2_h}")
    if actual_area_m2 <= 0.0:
        raise ValueError(f"actual_area_m2 must be positive, got {actual_area_m2}")

    dry_solids_kg_h = dry_solids_feed_tph * 1000.0
    required_area_m2 = dry_solids_kg_h / limiting_flux_kg_m2_h
    utilization_ratio = required_area_m2 / actual_area_m2
    area_margin_m2 = actual_area_m2 - required_area_m2

    return {
        "dry_solids_feed_tph": float(dry_solids_feed_tph),
        "dry_solids_feed_kg_h": float(dry_solids_kg_h),
        "limiting_flux_kg_m2_h": float(limiting_flux_kg_m2_h),
        "required_area_m2": float(required_area_m2),
        "actual_area_m2": float(actual_area_m2),
        "area_utilization_ratio": float(utilization_ratio),
        "area_margin_m2": float(area_margin_m2),
        "is_area_limited": bool(required_area_m2 > actual_area_m2),
    }
