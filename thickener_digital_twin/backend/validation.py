"""Input validation and calibration-range extrapolation warnings."""

from __future__ import annotations

from typing import Any, Dict, List


def check_calibration_warnings(
    feed_solids_wt_pct: float,
    flocculant_dose_gpt: float,
    predicted_underflow_wt_pct: float,
    area_utilization_ratio: float,
    bed_level_m: float,
    tank_depth_m: float,
    bed_high_alarm_m: float = 3.2,
    bed_low_alarm_m: float = 0.5,
    is_pump_limited: bool = False,
    reference_ranges: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    """Generate explicit warnings for extrapolation beyond reference ranges or physical limits."""
    ranges = reference_ranges or {
        "feed_solids_wt_pct": {"min": 4.0, "max": 15.0},
        "flocculant_dose_gpt": {"min": 10.0, "max": 40.0},
        "underflow_solids_wt_pct": {"min": 55.0, "max": 70.0},
    }
    warnings: List[Dict[str, str]] = []

    fs_min = float(ranges["feed_solids_wt_pct"]["min"])
    fs_max = float(ranges["feed_solids_wt_pct"]["max"])
    if feed_solids_wt_pct < fs_min or feed_solids_wt_pct > fs_max:
        warnings.append({
            "code": "EXTRAPOLATION_FEED_SOLIDS",
            "severity": "warning",
            "message": (
                f"Feed solids ({feed_solids_wt_pct:.1f}% w/w) is outside Project 4 reference range "
                f"({fs_min:.0f}-{fs_max:.0f}% w/w). Predictions involve extrapolation."
            ),
        })

    fl_min = float(ranges["flocculant_dose_gpt"]["min"])
    fl_max = float(ranges["flocculant_dose_gpt"]["max"])
    if flocculant_dose_gpt < fl_min or flocculant_dose_gpt > fl_max:
        warnings.append({
            "code": "EXTRAPOLATION_FLOCCULANT",
            "severity": "warning",
            "message": (
                f"Flocculant dose ({flocculant_dose_gpt:.1f} g/t) is outside Project 4 reference range "
                f"({fl_min:.0f}-{fl_max:.0f} g/t). Settling modifier is extrapolated."
            ),
        })

    uf_min = float(ranges["underflow_solids_wt_pct"]["min"])
    uf_max = float(ranges["underflow_solids_wt_pct"]["max"])
    if predicted_underflow_wt_pct < uf_min or predicted_underflow_wt_pct > uf_max:
        warnings.append({
            "code": "EXTRAPOLATION_UNDERFLOW_SOLIDS",
            "severity": "warning",
            "message": (
                f"Predicted underflow solids ({predicted_underflow_wt_pct:.1f}% w/w) lies outside "
                f"Project 4 reference range ({uf_min:.0f}-{uf_max:.0f}% w/w)."
            ),
        })

    if area_utilization_ratio > 1.0:
        warnings.append({
            "code": "FLUX_AREA_OVERLOAD",
            "severity": "critical",
            "message": (
                f"Required thickener area exceeds actual area (utilization {area_utilization_ratio*100:.1f}%). "
                "Settling capacity is exceeded; mud bed will rise and overflow clarity will degrade."
            ),
        })

    if bed_level_m >= tank_depth_m * 0.95:
        warnings.append({
            "code": "BED_OVERFLOW_CRITICAL",
            "severity": "critical",
            "message": f"Bed level ({bed_level_m:.2f} m) is near/at tank depth ({tank_depth_m:.2f} m).",
        })
    elif bed_level_m >= bed_high_alarm_m:
        warnings.append({
            "code": "BED_HIGH_ALARM",
            "severity": "warning",
            "message": f"Bed level ({bed_level_m:.2f} m) exceeds high alarm threshold ({bed_high_alarm_m:.2f} m).",
        })
    elif bed_level_m <= bed_low_alarm_m:
        warnings.append({
            "code": "BED_LOW_ALARM",
            "severity": "info",
            "message": f"Bed level ({bed_level_m:.2f} m) is below low alarm threshold ({bed_low_alarm_m:.2f} m).",
        })

    if is_pump_limited:
        warnings.append({
            "code": "PUMP_LIMITED",
            "severity": "critical",
            "message": "Target underflow concentration is PUMP-LIMITED: required pressure exceeds available pump rating.",
        })

    return warnings
