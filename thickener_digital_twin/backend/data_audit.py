"""Dataset quality and physics-constraint auditor for synthetic and imported CSVs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = ROOT_DIR / "data" / "synthetic" / "synthetic_thickener_dataset.csv"
AUDIT_OUTPUT_PATH = ROOT_DIR / "outputs" / "synthetic_data_audit.json"

REQUIRED_COLUMNS = [
    "record_id",
    "feed_rate_tph",
    "feed_solids_wt_pct",
    "flocculant_dose_gpt",
    "underflow_withdrawal_tph",
    "free_settling_velocity_mph",
    "rz_exponent_n",
    "thickener_area_m2",
    "underflow_solids_wt_pct",
    "overflow_clarity_index",
    "bed_level_m",
    "yield_stress_pa",
    "pump_pressure_required_bar",
    "pumpability_flag",
]


def audit_dataset(csv_path: Path = DEFAULT_CSV_PATH, output_path: Path = AUDIT_OUTPUT_PATH) -> Dict[str, Any]:
    """Validate columns, missingness, duplicates, units/ranges, and physical constraints."""
    df = pd.read_csv(csv_path)
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    null_counts = {col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().any()}
    duplicate_ids = int(df["record_id"].duplicated().sum()) if "record_id" in df.columns else -1

    constraint_checks = {
        "feed_rate_positive": bool((df["feed_rate_tph"] > 0).all()),
        "feed_solids_valid_pct": bool(((df["feed_solids_wt_pct"] > 0) & (df["feed_solids_wt_pct"] < 100)).all()),
        "underflow_denser_than_feed": bool((df["underflow_solids_wt_pct"] >= df["feed_solids_wt_pct"]).all()),
        "flocculant_non_negative": bool((df["flocculant_dose_gpt"] >= 0).all()),
        "clarity_within_0_100": bool(((df["overflow_clarity_index"] >= 0) & (df["overflow_clarity_index"] <= 100)).all()),
        "bed_level_non_negative": bool((df["bed_level_m"] >= 0).all()),
        "yield_stress_positive": bool((df["yield_stress_pa"] > 0).all()),
        "pump_pressure_positive": bool((df["pump_pressure_required_bar"] > 0).all()),
        "pumpability_flag_valid": bool(df["pumpability_flag"].isin(["Feasible", "Pump-limited"]).all()),
        "synthetic_label_present": bool(
            "data_source_label" in df.columns and (df["data_source_label"] == "SYNTHETIC").all()
        ),
    }

    passed = (
        len(missing_cols) == 0
        and len(null_counts) == 0
        and duplicate_ids == 0
        and all(constraint_checks.values())
    )

    report = {
        "csv_path": str(csv_path),
        "data_status": "SYNTHETIC" if constraint_checks["synthetic_label_present"] else "UNLABELLED_OR_EXTERNAL",
        "row_count": int(len(df)),
        "missing_required_columns": missing_cols,
        "null_counts": null_counts,
        "duplicate_record_ids": duplicate_ids,
        "constraint_checks": constraint_checks,
        "summary_ranges": {
            "feed_solids_wt_pct": [float(df["feed_solids_wt_pct"].min()), float(df["feed_solids_wt_pct"].max())],
            "flocculant_dose_gpt": [float(df["flocculant_dose_gpt"].min()), float(df["flocculant_dose_gpt"].max())],
            "underflow_solids_wt_pct": [float(df["underflow_solids_wt_pct"].min()), float(df["underflow_solids_wt_pct"].max())],
            "pump_pressure_required_bar": [
                float(df["pump_pressure_required_bar"].min()),
                float(df["pump_pressure_required_bar"].max()),
            ],
        },
        "passed": passed,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Thickener Digital Twin CSV dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_CSV_PATH, help="Path to CSV dataset")
    args = parser.parse_args()
    res = audit_dataset(csv_path=args.input)
    print(f"Dataset audit passed={res['passed']} ({res['row_count']} rows) -> {AUDIT_OUTPUT_PATH}")
    if not res["passed"]:
        raise SystemExit(1)
