"""Synthetic batch-settling and operating dataset generator (Project 4).

IMPORTANT: No measured Project 4 plant dataset was supplied. Every generated record
is explicitly labelled SYNTHETIC and must never be presented as plant data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from backend.config_loader import get_default_values, load_raw_config
from backend.simulator import simulate_operating_point

ROOT_DIR = Path(__file__).resolve().parent.parent
SYNTHETIC_DIR = ROOT_DIR / "data" / "synthetic"
CSV_PATH = SYNTHETIC_DIR / "synthetic_thickener_dataset.csv"
META_PATH = SYNTHETIC_DIR / "synthetic_dataset_metadata.json"


def generate_synthetic_dataset(
    n_rows: int = 500,
    seed: int = 42,
    output_dir: Path = SYNTHETIC_DIR,
) -> Dict[str, object]:
    """Generate and save a labelled SYNTHETIC dataset covering Project 4 reference ranges."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "synthetic_thickener_dataset.csv"
    meta_path = output_dir / "synthetic_dataset_metadata.json"
    defaults = get_default_values()
    raw_cfg = load_raw_config()
    rng = np.random.default_rng(seed)

    # Sample inputs spanning reference ranges plus moderate excursions to exercise warnings
    feed_rate_tph = rng.uniform(220.0, 460.0, n_rows)
    feed_solids_wt_pct = np.clip(rng.uniform(4.0, 15.0, n_rows), 4.0, 15.0)
    flocculant_dose_gpt = np.clip(rng.uniform(10.0, 40.0, n_rows), 10.0, 40.0)
    thickener_area_m2 = rng.choice([200.0, 250.0, 300.0, 350.0], size=n_rows)
    free_settling_velocity_mph = rng.uniform(5.8, 8.5, n_rows)
    rz_exponent_n = rng.uniform(4.2, 5.1, n_rows)
    bed_level_m = rng.uniform(0.7, 2.8, n_rows)

    # Choose underflow withdrawal around realistic mass-balance pull with variation
    uf_target_guess = rng.uniform(56.0, 68.5, n_rows)
    underflow_withdrawal_tph = np.clip(
        feed_rate_tph / (uf_target_guess / 100.0) * rng.uniform(0.92, 1.12, n_rows),
        320.0,
        850.0,
    )

    records = []
    for i in range(n_rows):
        sim = simulate_operating_point(
            {
                **defaults,
                "feed_rate_tph": float(feed_rate_tph[i]),
                "feed_rate_basis": "dry_solids",
                "feed_solids_wt_pct": float(feed_solids_wt_pct[i]),
                "flocculant_dose_gpt": float(flocculant_dose_gpt[i]),
                "underflow_withdrawal_tph": float(underflow_withdrawal_tph[i]),
                "underflow_basis": "slurry",
                "free_settling_velocity_mph": float(free_settling_velocity_mph[i]),
                "rz_exponent_n": float(rz_exponent_n[i]),
                "thickener_area_m2": float(thickener_area_m2[i]),
                "bed_level_m": float(bed_level_m[i]),
            }
        )

        # Documented low-amplitude synthetic measurement noise
        uf_noisy = float(
            np.clip(
                sim["underflow"]["predicted_underflow_solids_wt_pct"] + rng.normal(0.0, 0.35),
                40.0,
                72.0,
            )
        )
        clarity_noisy = float(
            np.clip(sim["overflow_clarity"]["overflow_clarity_index"] + rng.normal(0.0, 1.2), 0.0, 100.0)
        )
        tau_y = sim["pumpability"]["yield_stress_pa"]
        p_req = sim["pumpability"]["required_pump_pressure_bar"]

        records.append(
            {
                "record_id": i + 1,
                "data_source_label": "SYNTHETIC",
                "feed_rate_tph": round(float(feed_rate_tph[i]), 3),
                "feed_rate_basis": "dry_solids",
                "feed_solids_wt_pct": round(float(feed_solids_wt_pct[i]), 3),
                "flocculant_dose_gpt": round(float(flocculant_dose_gpt[i]), 3),
                "underflow_withdrawal_tph": round(float(underflow_withdrawal_tph[i]), 3),
                "underflow_basis": "slurry",
                "free_settling_velocity_mph": round(float(free_settling_velocity_mph[i]), 4),
                "rz_exponent_n": round(float(rz_exponent_n[i]), 4),
                "thickener_area_m2": round(float(thickener_area_m2[i]), 2),
                "underflow_solids_wt_pct": round(uf_noisy, 3),
                "overflow_clarity_index": round(clarity_noisy, 2),
                "bed_level_m": round(float(bed_level_m[i]), 3),
                "yield_stress_pa": round(float(tau_y), 3),
                "pump_pressure_required_bar": round(float(p_req), 3),
                "pumpability_flag": sim["pumpability"]["pumpability_flag"],
            }
        )

    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False)

    metadata = {
        "data_status": "SYNTHETIC",
        "is_plant_measured": False,
        "warning": (
            "SYNTHETIC DATASET ONLY: Generated from physics equations and assumed parameters "
            "for development and testing. Never present as measured Project 4 plant data."
        ),
        "source_reference": raw_cfg["metadata"]["source_reference"],
        "n_rows": len(df),
        "random_seed": seed,
        "columns": list(df.columns),
        "noise_assumptions": {
            "underflow_solids_wt_pct_sigma": 0.35,
            "overflow_clarity_index_sigma": 1.2,
        },
        "reference_ranges_covered": {
            "feed_solids_wt_pct": [float(df["feed_solids_wt_pct"].min()), float(df["feed_solids_wt_pct"].max())],
            "flocculant_dose_gpt": [float(df["flocculant_dose_gpt"].min()), float(df["flocculant_dose_gpt"].max())],
            "underflow_solids_wt_pct": [float(df["underflow_solids_wt_pct"].min()), float(df["underflow_solids_wt_pct"].max())],
        },
        "pump_limited_fraction_pct": round(float((df["pumpability_flag"] == "Pump-limited").mean() * 100.0), 2),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {"csv_path": str(csv_path), "metadata_path": str(meta_path), "metadata": metadata}


if __name__ == "__main__":
    result = generate_synthetic_dataset()
    print(f"Generated SYNTHETIC dataset ({result['metadata']['n_rows']} rows) -> {result['csv_path']}")
