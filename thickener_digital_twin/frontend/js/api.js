/**
 * REST API client and shared operating-parameter state for Thickener Digital Twin.
 */

const STORAGE_KEY = "tdt_operating_params_v1";

export const DEFAULT_PARAMS = {
  feed_rate_tph: 320.0,
  feed_rate_basis: "dry_solids",
  feed_solids_wt_pct: 10.0,
  flocculant_dose_gpt: 25.0,
  underflow_withdrawal_tph: 505.0,
  underflow_basis: "slurry",
  bed_level_m: 1.5,
  thickener_area_m2: 250.0,
  tank_depth_m: 4.5,
  free_settling_velocity_mph: 7.0,
  rz_exponent_n: 4.65,
  model_type: "exponential",
  available_pump_pressure_bar: 15.0,
  pipe_length_m: 300.0,
  pipe_diameter_m: 0.20,
  static_elevation_head_m: 15.0,
  rheology_a_pa: 0.055,
  rheology_b: 21.3,
  plastic_viscosity_pa_s: 0.08,
  solids_density_kg_m3: 3200.0,
  liquid_density_kg_m3: 1000.0,
};

export function loadSavedParams() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_PARAMS };
    return { ...DEFAULT_PARAMS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_PARAMS };
  }
}

export function saveParams(params) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(params));
  } catch {
    // Ignore storage quota errors
  }
}

export function resetSavedParams() {
  saveParams(DEFAULT_PARAMS);
  return { ...DEFAULT_PARAMS };
}

async function requestJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const msg =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
        ? data.detail.map((d) => `${d.loc?.join(".")}: ${d.msg}`).join("; ")
        : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  health: () => requestJson("/api/health"),
  config: () => requestJson("/api/config"),
  datasetSummary: () => requestJson("/api/dataset/summary"),
  simulate: (payload) =>
    requestJson("/api/simulate", { method: "POST", body: JSON.stringify(payload) }),
  flux: (payload) =>
    requestJson("/api/flux", { method: "POST", body: JSON.stringify(payload) }),
  dynamics: (payload) =>
    requestJson("/api/dynamics", { method: "POST", body: JSON.stringify(payload) }),
  pumpability: (payload) =>
    requestJson("/api/pumpability", { method: "POST", body: JSON.stringify(payload) }),
  monteCarlo: (payload) =>
    requestJson("/api/monte-carlo", { method: "POST", body: JSON.stringify(payload) }),
  scenario: (payload) =>
    requestJson("/api/scenario", { method: "POST", body: JSON.stringify(payload) }),
};
