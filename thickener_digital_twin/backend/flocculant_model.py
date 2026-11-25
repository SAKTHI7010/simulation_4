"""Configurable, bounded flocculant dose-response modifier."""

from __future__ import annotations

import math
from typing import Any, Dict, Literal, Optional


def flocculant_modifier(
    dose_gpt: float,
    model_type: Literal["exponential", "power_law"] = "exponential",
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute a bounded settling-velocity multiplier for flocculant dosage (g/t).

    Both exponential and power-law forms enforce diminishing returns and a strict
    upper bound so indefinitely increasing flocculant does not yield unbounded flux.
    """
    if dose_gpt < 0.0:
        raise ValueError(f"flocculant dose_gpt must be non-negative, got {dose_gpt}")

    cfg = params or {}
    m_min = float(cfg.get("min_modifier", 0.25))
    m_max = float(cfg.get("max_modifier", 1.45))
    if m_min <= 0.0 or m_max < m_min:
        raise ValueError("Invalid flocculant modifier bounds: require 0 < min_modifier <= max_modifier.")

    if model_type == "exponential":
        d_c = float(cfg.get("characteristic_dose_gpt", 18.0))
        if d_c <= 0.0:
            raise ValueError(f"characteristic_dose_gpt must be positive, got {d_c}")
        raw = m_min + (m_max - m_min) * (1.0 - math.exp(-dose_gpt / d_c))
        formula = "M(d) = M_min + (M_max - M_min) * (1 - exp(-d / d_c))"
    elif model_type == "power_law":
        k = float(cfg.get("power_k", 0.90))
        d_ref = float(cfg.get("power_ref_dose_gpt", 25.0))
        alpha = float(cfg.get("power_alpha", 0.55))
        if d_ref <= 0.0 or not (0.0 < alpha < 1.0):
            raise ValueError("Power-law requires power_ref_dose_gpt > 0 and 0 < power_alpha < 1.")
        raw = m_min + k * ((dose_gpt / d_ref) ** alpha)
        formula = "M(d) = min(M_max, M_min + k * (d / d_ref)^alpha)"
    else:
        raise ValueError(f"Unsupported flocculant model_type '{model_type}'.")

    bounded = max(m_min, min(m_max, float(raw)))
    return {
        "modifier": bounded,
        "model_type": model_type,
        "dose_gpt": float(dose_gpt),
        "min_modifier": m_min,
        "max_modifier": m_max,
        "formula": formula,
        "calibration_status": "SYNTHETIC_ASSUMED",
    }
