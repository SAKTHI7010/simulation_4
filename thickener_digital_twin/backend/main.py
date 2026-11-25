"""FastAPI application and REST API routes for Thickener Digital Twin (Project 4)."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.bed_dynamics import run_bed_dynamics_simulation
from backend.config_loader import get_default_values, load_raw_config
from backend.data_generator import generate_synthetic_dataset
from backend.flux_model import compute_flux_curve
from backend.monte_carlo import run_monte_carlo
from backend.pumpability import compute_pumpability_curve, evaluate_pumpability
from backend.scenario_analysis import run_scenario_comparison
from backend.simulator import simulate_operating_point
from backend.thickener_area import compute_required_area
from backend.unit_conversions import resolve_mass_rates

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
SYNTHETIC_CSV = ROOT_DIR / "data" / "synthetic" / "synthetic_thickener_dataset.csv"
SYNTHETIC_META = ROOT_DIR / "data" / "synthetic" / "synthetic_dataset_metadata.json"

DEFAULTS = get_default_values()


def _ensure_synthetic_dataset() -> None:
    """Ensure the labelled SYNTHETIC dataset exists on fresh clones or ephemeral disks."""
    if not SYNTHETIC_CSV.exists():
        generate_synthetic_dataset()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_synthetic_dataset()
    yield


app = FastAPI(
    title="Thickener Digital Twin API (Project 4)",
    description=(
        "Physics-based thickener simulator using Richardson-Zaki settling-flux theory, "
        "dynamic bed-level inventory balance, Bingham rheology pumpability, and Monte Carlo uncertainty. "
        "SYNTHETIC / UNCALIBRATED DEVELOPMENT MODEL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OperatingRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    feed_rate_tph: float = Field(default=DEFAULTS["feed_rate_tph"], gt=0.0, le=5000.0)
    feed_rate_basis: Literal["dry_solids", "slurry"] = Field(default=DEFAULTS["feed_rate_basis"])
    feed_solids_wt_pct: float = Field(default=DEFAULTS["feed_solids_wt_pct"], gt=0.1, lt=80.0)
    flocculant_dose_gpt: float = Field(default=DEFAULTS["flocculant_dose_gpt"], ge=0.0, le=200.0)
    underflow_withdrawal_tph: float = Field(default=DEFAULTS["underflow_withdrawal_tph"], gt=0.1, le=5000.0)
    underflow_basis: Literal["slurry", "dry_solids"] = Field(default=DEFAULTS["underflow_basis"])
    bed_level_m: float = Field(default=DEFAULTS["bed_level_m"], ge=0.0, le=15.0)
    thickener_area_m2: float = Field(default=DEFAULTS["thickener_area_m2"], gt=1.0, le=20000.0)
    tank_depth_m: float = Field(default=DEFAULTS["tank_depth_m"], gt=0.5, le=20.0)
    free_settling_velocity_mph: float = Field(default=DEFAULTS["free_settling_velocity_mph"], gt=0.1, le=50.0)
    rz_exponent_n: float = Field(default=DEFAULTS["rz_exponent_n"], ge=1.0, le=15.0)
    model_type: Literal["exponential", "power_law"] = Field(default=DEFAULTS["model_type"])
    available_pump_pressure_bar: float = Field(default=DEFAULTS["available_pump_pressure_bar"], gt=0.5, le=100.0)
    pipe_length_m: float = Field(default=DEFAULTS["pipe_length_m"], gt=1.0, le=10000.0)
    pipe_diameter_m: float = Field(default=DEFAULTS["pipe_diameter_m"], gt=0.02, le=2.0)
    static_elevation_head_m: float = Field(default=DEFAULTS["static_elevation_head_m"], ge=0.0, le=500.0)
    rheology_a_pa: float = Field(default=DEFAULTS["rheology_a_pa"], gt=0.001, le=10.0)
    rheology_b: float = Field(default=DEFAULTS["rheology_b"], ge=0.0, le=50.0)
    plastic_viscosity_pa_s: float = Field(default=DEFAULTS["plastic_viscosity_pa_s"], ge=0.0, le=5.0)
    solids_density_kg_m3: float = Field(default=DEFAULTS["solids_density_kg_m3"], gt=1000.0, le=8000.0)
    liquid_density_kg_m3: float = Field(default=DEFAULTS["liquid_density_kg_m3"], gt=500.0, le=2000.0)


class DynamicsRequest(OperatingRequest):
    duration_h: float = Field(default=12.0, gt=0.5, le=72.0)
    step_time_h: float = Field(default=2.0, ge=0.0, le=72.0)
    feed_rate_step_pct: float = Field(default=20.0, ge=-80.0, le=200.0)
    underflow_withdrawal_step_pct: float = Field(default=0.0, ge=-80.0, le=200.0)
    flocculant_dose_step_pct: float = Field(default=-50.0, ge=-100.0, le=300.0)
    bed_time_constant_h: float = Field(default=DEFAULTS["bed_time_constant_h"], gt=0.05, le=24.0)
    bed_average_solids_wt_pct: float = Field(default=DEFAULTS["bed_average_solids_wt_pct"], gt=15.0, lt=75.0)


class PumpabilityRequest(BaseModel):
    underflow_solids_wt_pct: float = Field(default=63.0, gt=10.0, lt=80.0)
    underflow_slurry_tph: float = Field(default=DEFAULTS["underflow_withdrawal_tph"], gt=1.0, le=5000.0)
    available_pump_pressure_bar: float = Field(default=DEFAULTS["available_pump_pressure_bar"], gt=0.5, le=100.0)
    pipe_length_m: float = Field(default=DEFAULTS["pipe_length_m"], gt=1.0, le=10000.0)
    pipe_diameter_m: float = Field(default=DEFAULTS["pipe_diameter_m"], gt=0.02, le=2.0)
    static_elevation_head_m: float = Field(default=DEFAULTS["static_elevation_head_m"], ge=0.0, le=500.0)
    plastic_viscosity_pa_s: float = Field(default=DEFAULTS["plastic_viscosity_pa_s"], ge=0.0, le=5.0)
    rheology_a_pa: float = Field(default=DEFAULTS["rheology_a_pa"], gt=0.001, le=10.0)
    rheology_b: float = Field(default=DEFAULTS["rheology_b"], ge=0.0, le=50.0)
    solids_density_kg_m3: float = Field(default=DEFAULTS["solids_density_kg_m3"], gt=1000.0, le=8000.0)
    liquid_density_kg_m3: float = Field(default=DEFAULTS["liquid_density_kg_m3"], gt=500.0, le=2000.0)


class MonteCarloRequest(OperatingRequest):
    n_simulations: int = Field(default=int(DEFAULTS["n_simulations"]), ge=50, le=10000)
    random_seed: int = Field(default=int(DEFAULTS["random_seed"]), ge=0, le=2**31 - 1)
    feed_rate_cv_pct: float = Field(default=DEFAULTS["feed_rate_cv_pct"], ge=0.0, le=50.0)
    feed_solids_cv_pct: float = Field(default=DEFAULTS["feed_solids_cv_pct"], ge=0.0, le=50.0)
    v0_cv_pct: float = Field(default=DEFAULTS["v0_cv_pct"], ge=0.0, le=50.0)
    rz_n_cv_pct: float = Field(default=DEFAULTS["rz_n_cv_pct"], ge=0.0, le=50.0)


class ScenarioRequest(BaseModel):
    baseline: OperatingRequest = Field(default_factory=OperatingRequest)
    modified: OperatingRequest = Field(
        default_factory=lambda: OperatingRequest(
            feed_rate_tph=round(DEFAULTS["feed_rate_tph"] * 1.2, 2),
            flocculant_dose_gpt=round(DEFAULTS["flocculant_dose_gpt"] * 0.5, 2),
        )
    )


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Backend health check and data-provenance indicator."""
    raw_cfg = load_raw_config()
    return {
        "status": "ok",
        "service": "thickener-digital-twin",
        "data_status": raw_cfg["metadata"]["data_status"],
        "synthetic_dataset_available": SYNTHETIC_CSV.exists(),
    }


@app.get("/api/config")
def get_config() -> Dict[str, Any]:
    """Expose explicit parameter register, units, defaults, and calibration status."""
    return load_raw_config()


@app.get("/api/dataset/summary")
def get_dataset_summary() -> Dict[str, Any]:
    """Return summary and sample rows of the labelled SYNTHETIC dataset."""
    _ensure_synthetic_dataset()
    df = pd.read_csv(SYNTHETIC_CSV)
    meta = json.loads(SYNTHETIC_META.read_text(encoding="utf-8")) if SYNTHETIC_META.exists() else {}
    return {
        "data_status": "SYNTHETIC",
        "metadata": meta,
        "preview_rows": df.head(10).to_dict(orient="records"),
    }


@app.post("/api/simulate")
def api_simulate(req: OperatingRequest) -> Dict[str, Any]:
    """Calculate current thickener operating scenario."""
    if req.bed_level_m > req.tank_depth_m:
        raise HTTPException(status_code=422, detail="bed_level_m cannot exceed tank_depth_m.")
    return simulate_operating_point(req.model_dump())


@app.post("/api/flux")
def api_flux(req: OperatingRequest) -> Dict[str, Any]:
    """Return settling velocity, solids-flux curve, limiting flux, and dose comparisons."""
    dry_in_tph, _ = resolve_mass_rates(req.feed_rate_tph, req.feed_solids_wt_pct, req.feed_rate_basis)
    floc_params = {
        "min_modifier": DEFAULTS["min_modifier"],
        "max_modifier": DEFAULTS["max_modifier"],
        "characteristic_dose_gpt": DEFAULTS["characteristic_dose_gpt"],
        "power_k": DEFAULTS["power_k"],
        "power_ref_dose_gpt": DEFAULTS["power_ref_dose_gpt"],
        "power_alpha": DEFAULTS["power_alpha"],
    }
    primary = compute_flux_curve(
        v0_base_mph=req.free_settling_velocity_mph,
        rz_exponent_n=req.rz_exponent_n,
        flocculant_dose_gpt=req.flocculant_dose_gpt,
        solids_density_kg_m3=req.solids_density_kg_m3,
        liquid_density_kg_m3=req.liquid_density_kg_m3,
        floc_model_type=req.model_type,
        floc_params=floc_params,
        phi_max=float(DEFAULTS["phi_grid_max"]),
        n_points=int(DEFAULTS["phi_grid_points"]),
    )
    area = compute_required_area(
        dry_solids_feed_tph=dry_in_tph,
        limiting_flux_kg_m2_h=primary["limiting_flux_kg_m2_h"],
        actual_area_m2=req.thickener_area_m2,
    )

    dose_levels = sorted(set([10.0, round(req.flocculant_dose_gpt * 0.5, 1), 25.0, 40.0, req.flocculant_dose_gpt]))
    dose_comparisons = []
    for d in dose_levels:
        c = compute_flux_curve(
            v0_base_mph=req.free_settling_velocity_mph,
            rz_exponent_n=req.rz_exponent_n,
            flocculant_dose_gpt=d,
            solids_density_kg_m3=req.solids_density_kg_m3,
            liquid_density_kg_m3=req.liquid_density_kg_m3,
            floc_model_type=req.model_type,
            floc_params=floc_params,
            phi_max=float(DEFAULTS["phi_grid_max"]),
            n_points=120,
        )
        dose_comparisons.append(
            {
                "dose_gpt": d,
                "modifier": c["flocculant_info"]["modifier"],
                "limiting_flux_kg_m2_h": c["limiting_flux_kg_m2_h"],
                "phi": c["phi"],
                "flux_kg_m2_h": c["flux_kg_m2_h"],
            }
        )

    return {
        "data_status": "SYNTHETIC_UNVALIDATED",
        "primary_curve": primary,
        "area_sizing": area,
        "dose_comparisons": dose_comparisons,
    }


@app.post("/api/dynamics")
def api_dynamics(req: DynamicsRequest) -> Dict[str, Any]:
    """Run time-based solids-inventory and bed-level dynamic simulation."""
    if req.bed_level_m > req.tank_depth_m:
        raise HTTPException(status_code=422, detail="bed_level_m cannot exceed tank_depth_m.")
    if req.step_time_h > req.duration_h:
        raise HTTPException(status_code=422, detail="step_time_h cannot exceed duration_h.")
    return run_bed_dynamics_simulation(
        feed_rate_tph=req.feed_rate_tph,
        feed_rate_basis=req.feed_rate_basis,
        feed_solids_wt_pct=req.feed_solids_wt_pct,
        flocculant_dose_gpt=req.flocculant_dose_gpt,
        underflow_withdrawal_tph=req.underflow_withdrawal_tph,
        underflow_basis=req.underflow_basis,
        initial_bed_level_m=req.bed_level_m,
        thickener_area_m2=req.thickener_area_m2,
        tank_depth_m=req.tank_depth_m,
        bed_average_solids_wt_pct=req.bed_average_solids_wt_pct,
        bed_time_constant_h=req.bed_time_constant_h,
        v0_base_mph=req.free_settling_velocity_mph,
        rz_exponent_n=req.rz_exponent_n,
        floc_model_type=req.model_type,
        duration_h=req.duration_h,
        step_time_h=req.step_time_h,
        feed_rate_step_pct=req.feed_rate_step_pct,
        underflow_withdrawal_step_pct=req.underflow_withdrawal_step_pct,
        flocculant_dose_step_pct=req.flocculant_dose_step_pct,
        solids_density_kg_m3=req.solids_density_kg_m3,
        liquid_density_kg_m3=req.liquid_density_kg_m3,
        available_pump_pressure_bar=req.available_pump_pressure_bar,
        pipe_length_m=req.pipe_length_m,
        pipe_diameter_m=req.pipe_diameter_m,
        static_elevation_head_m=req.static_elevation_head_m,
        plastic_viscosity_pa_s=req.plastic_viscosity_pa_s,
        rheology_a_pa=req.rheology_a_pa,
        rheology_b=req.rheology_b,
    )


@app.post("/api/pumpability")
def api_pumpability(req: PumpabilityRequest) -> Dict[str, Any]:
    """Calculate yield stress, required pump pressure, pumpability status, and curve."""
    evaluation = evaluate_pumpability(
        underflow_solids_wt_pct=req.underflow_solids_wt_pct,
        underflow_slurry_tph=req.underflow_slurry_tph,
        available_pump_pressure_bar=req.available_pump_pressure_bar,
        pipe_length_m=req.pipe_length_m,
        pipe_diameter_m=req.pipe_diameter_m,
        static_elevation_head_m=req.static_elevation_head_m,
        plastic_viscosity_pa_s=req.plastic_viscosity_pa_s,
        rheology_a_pa=req.rheology_a_pa,
        rheology_b=req.rheology_b,
        solids_density_kg_m3=req.solids_density_kg_m3,
        liquid_density_kg_m3=req.liquid_density_kg_m3,
        compute_max_solids=True,
    )
    curve = compute_pumpability_curve(
        underflow_slurry_tph=req.underflow_slurry_tph,
        available_pump_pressure_bar=req.available_pump_pressure_bar,
        pipe_length_m=req.pipe_length_m,
        pipe_diameter_m=req.pipe_diameter_m,
        static_elevation_head_m=req.static_elevation_head_m,
        plastic_viscosity_pa_s=req.plastic_viscosity_pa_s,
        rheology_a_pa=req.rheology_a_pa,
        rheology_b=req.rheology_b,
        solids_density_kg_m3=req.solids_density_kg_m3,
        liquid_density_kg_m3=req.liquid_density_kg_m3,
    )
    return {
        "data_status": "SYNTHETIC_UNVALIDATED",
        "evaluation": evaluation,
        "curve": curve,
    }


@app.post("/api/monte-carlo")
def api_monte_carlo(req: MonteCarloRequest) -> Dict[str, Any]:
    """Run Monte Carlo uncertainty analysis and return distributions and statistics."""
    if req.bed_level_m > req.tank_depth_m:
        raise HTTPException(status_code=422, detail="bed_level_m cannot exceed tank_depth_m.")
    return run_monte_carlo(req.model_dump())


@app.post("/api/scenario")
def api_scenario(req: ScenarioRequest) -> Dict[str, Any]:
    """Compare baseline and modified thickener operating conditions."""
    return run_scenario_comparison(req.baseline.model_dump(), req.modified.model_dump())


# Serve the HTML/CSS/JS frontend from root after all API routes are registered
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
