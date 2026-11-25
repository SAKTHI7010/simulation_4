/**
 * Shared navigation, backend health polling, form binding, and page initialization.
 */

import { api, loadSavedParams, resetSavedParams, saveParams } from "/js/api.js";
import {
  renderDynamicsCharts,
  renderFluxCharts,
  renderMonteCarloCharts,
  renderPumpabilityCharts,
  renderScenarioCharts,
} from "/js/charts.js";

export function setAlert(containerId, message, type = "critical") {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!message) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.className = `alert alert-${type}`;
  el.textContent = message;
  el.classList.remove("hidden");
}

export function renderWarnings(containerId, warnings = []) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!warnings.length) {
    el.innerHTML = `<div class="alert alert-ok">All inputs are within Project 4 reference ranges and equipment capacity bounds.</div>`;
    return;
  }
  el.innerHTML = warnings
    .map((w) => {
      const cls = w.severity === "critical" ? "alert-critical" : w.severity === "info" ? "alert-info" : "alert-warning";
      return `<div class="alert ${cls}"><strong>[${w.code}]</strong> ${w.message}</div>`;
    })
    .join("");
}

export async function initHealthIndicator() {
  const dot = document.getElementById("health-dot");
  const text = document.getElementById("health-text");
  if (!dot || !text) return;
  try {
    const h = await api.health();
    dot.className = "health-dot ok";
    text.textContent = `API Online • ${h.data_status}`;
  } catch (err) {
    dot.className = "health-dot err";
    text.textContent = "API Offline";
  }
}

export function populateFormFromParams(form, params) {
  if (!form) return;
  Object.entries(params).forEach(([key, val]) => {
    const input = form.elements.namedItem(key);
    if (input) input.value = val;
  });
}

export function readFormParams(form, baseParams = {}) {
  const out = { ...baseParams };
  Array.from(form.elements).forEach((el) => {
    if (!el.name) return;
    if (el.type === "number" || el.type === "range") {
      const num = parseFloat(el.value);
      if (!Number.isNaN(num)) out[el.name] = num;
    } else {
      out[el.name] = el.value;
    }
  });
  return out;
}

async function initFluxPage() {
  const form = document.getElementById("flux-form");
  const btn = document.getElementById("btn-run-flux");
  const params = loadSavedParams();
  populateFormFromParams(form, params);

  const run = async () => {
    setAlert("page-error", "");
    btn.disabled = true;
    btn.textContent = "Calculating...";
    try {
      const payload = readFormParams(form, loadSavedParams());
      saveParams(payload);
      const data = await api.flux(payload);
      const c = data.primary_curve;
      const a = data.area_sizing;
      document.getElementById("kpi-flim").textContent = `${c.limiting_flux_kg_m2_h.toFixed(1)} kg/(m²·h)`;
      document.getElementById("kpi-phi-lim").textContent = `φ = ${c.phi_at_limiting_flux.toFixed(3)} (${c.wt_pct_at_limiting_flux.toFixed(1)}% w/w)`;
      document.getElementById("kpi-v0-eff").textContent = `${c.v0_effective_mph.toFixed(2)} m/h`;
      document.getElementById("kpi-floc-mod").textContent = `${c.flocculant_info.modifier.toFixed(3)}× (${c.flocculant_info.model_type})`;
      document.getElementById("kpi-req-area").textContent = `${a.required_area_m2.toFixed(1)} m²`;
      document.getElementById("kpi-area-util").textContent = `${(a.area_utilization_ratio * 100).toFixed(1)}% of ${a.actual_area_m2.toFixed(0)} m²`;
      renderFluxCharts(data);
    } catch (err) {
      setAlert("page-error", `Flux calculation error: ${err.message}`, "critical");
    } finally {
      btn.disabled = false;
      btn.textContent = "Calculate Flux Curve";
    }
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  await run();
}

async function initDynamicsPage() {
  const form = document.getElementById("dynamics-form");
  const btn = document.getElementById("btn-run-dynamics");
  const params = loadSavedParams();
  populateFormFromParams(form, params);

  const run = async () => {
    setAlert("page-error", "");
    btn.disabled = true;
    btn.textContent = "Integrating ODE...";
    try {
      const payload = readFormParams(form, loadSavedParams());
      const data = await api.dynamics(payload);
      const s = data.summary;
      const mb = data.mass_balance_check;
      document.getElementById("kpi-bed-final").textContent = `${s.final_bed_level_m.toFixed(2)} m`;
      document.getElementById("kpi-bed-peak").textContent = `Peak: ${s.peak_bed_level_m.toFixed(2)} m`;
      document.getElementById("kpi-uf-final").textContent = `${s.final_underflow_wt_pct.toFixed(1)}% w/w`;
      document.getElementById("kpi-clarity-final").textContent = `${s.final_clarity_index.toFixed(1)} / 100`;
      document.getElementById("kpi-mb-closure").textContent = `${mb.closure_error_pct.toFixed(4)}%`;
      document.getElementById("kpi-mb-status").textContent = mb.closed_within_1pct ? "Mass balance closed (<1%)" : "Check tolerance";
      renderDynamicsCharts(data);
    } catch (err) {
      setAlert("page-error", `Dynamic simulation error: ${err.message}`, "critical");
    } finally {
      btn.disabled = false;
      btn.textContent = "Run Dynamic Simulation";
    }
  };

  document.querySelectorAll("[data-preset]").forEach((pBtn) => {
    pBtn.addEventListener("click", () => {
      const kind = pBtn.dataset.preset;
      if (kind === "project4") {
        form.elements.feed_rate_step_pct.value = 20;
        form.elements.flocculant_dose_step_pct.value = -50;
        form.elements.underflow_withdrawal_step_pct.value = 0;
      } else if (kind === "withdrawal-drop") {
        form.elements.feed_rate_step_pct.value = 0;
        form.elements.flocculant_dose_step_pct.value = 0;
        form.elements.underflow_withdrawal_step_pct.value = -15;
      } else if (kind === "feed-surge") {
        form.elements.feed_rate_step_pct.value = 30;
        form.elements.flocculant_dose_step_pct.value = 0;
        form.elements.underflow_withdrawal_step_pct.value = 10;
      }
      run();
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  await run();
}

async function initPumpabilityPage() {
  const form = document.getElementById("pumpability-form");
  const btn = document.getElementById("btn-run-pump");
  const slider = document.getElementById("target-density-slider");
  const sliderVal = document.getElementById("target-density-label");
  const params = loadSavedParams();
  populateFormFromParams(form, {
    ...params,
    underflow_slurry_tph: params.underflow_withdrawal_tph,
    underflow_solids_wt_pct: 63.0,
  });

  const syncSlider = () => {
    sliderVal.textContent = `${parseFloat(slider.value).toFixed(1)}% w/w`;
  };
  slider.addEventListener("input", syncSlider);
  syncSlider();

  const run = async () => {
    setAlert("page-error", "");
    btn.disabled = true;
    btn.textContent = "Evaluating...";
    try {
      const payload = readFormParams(form, {});
      const data = await api.pumpability(payload);
      const ev = data.evaluation;
      document.getElementById("kpi-yield-stress").textContent = `${ev.yield_stress_pa.toFixed(1)} Pa`;
      document.getElementById("kpi-req-press").textContent = `${ev.required_pump_pressure_bar.toFixed(2)} bar`;
      document.getElementById("kpi-max-pumpable").textContent =
        ev.max_pumpable_solids_wt_pct !== null ? `${ev.max_pumpable_solids_wt_pct.toFixed(1)}% w/w` : "N/A";
      document.getElementById("kpi-pump-status").textContent = ev.pumpability_flag;

      const statusBox = document.getElementById("pump-status-alert");
      statusBox.className = ev.is_pump_limited ? "alert alert-critical" : "alert alert-ok";
      statusBox.textContent = ev.binding_reason;

      renderPumpabilityCharts(data);
    } catch (err) {
      setAlert("page-error", `Pumpability error: ${err.message}`, "critical");
    } finally {
      btn.disabled = false;
      btn.textContent = "Evaluate Pumpability";
    }
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  slider.addEventListener("change", run);
  await run();
}

async function initMonteCarloPage() {
  const form = document.getElementById("mc-form");
  const btn = document.getElementById("btn-run-mc");
  const params = loadSavedParams();
  populateFormFromParams(form, params);

  const run = async () => {
    setAlert("page-error", "");
    btn.disabled = true;
    btn.textContent = "Running Trials...";
    try {
      const payload = readFormParams(form, loadSavedParams());
      const mc = await api.monteCarlo(payload);
      const uf = mc.underflow_solids_stats;
      document.getElementById("kpi-mc-mean").textContent = `${uf.mean.toFixed(2)}% w/w`;
      document.getElementById("kpi-mc-std").textContent = `± ${uf.std.toFixed(2)}%`;
      document.getElementById("kpi-mc-p5-p95").textContent = `${uf.p5.toFixed(1)}% – ${uf.p95.toFixed(1)}%`;
      document.getElementById("kpi-mc-pump-prob").textContent = `${mc.pumpability_violation_probability_pct.toFixed(1)}%`;
      document.getElementById("kpi-mc-area-prob").textContent = `${mc.area_overload_probability_pct.toFixed(1)}%`;
      renderMonteCarloCharts(mc);
    } catch (err) {
      setAlert("page-error", `Monte Carlo error: ${err.message}`, "critical");
    } finally {
      btn.disabled = false;
      btn.textContent = "Run Monte Carlo";
    }
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  await run();
}

async function initScenarioPage() {
  const baseForm = document.getElementById("scenario-base-form");
  const modForm = document.getElementById("scenario-mod-form");
  const btn = document.getElementById("btn-run-scenario");
  const params = loadSavedParams();

  populateFormFromParams(baseForm, params);
  populateFormFromParams(modForm, {
    ...params,
    feed_rate_tph: +(params.feed_rate_tph * 1.2).toFixed(1),
    flocculant_dose_gpt: +(params.flocculant_dose_gpt * 0.5).toFixed(1),
  });

  const run = async () => {
    setAlert("page-error", "");
    btn.disabled = true;
    btn.textContent = "Comparing...";
    try {
      const baseline = readFormParams(baseForm, params);
      const modified = readFormParams(modForm, baseline);
      const sc = await api.scenario({ baseline, modified });

      const verdictEl = document.getElementById("scenario-verdict");
      verdictEl.className = sc.modified.kpis.is_pump_limited
        ? "alert alert-critical"
        : sc.modified.kpis.area_utilization_pct > 100
        ? "alert alert-warning"
        : "alert alert-ok";
      verdictEl.textContent = sc.operator_verdict;

      const labels = {
        dry_solids_feed_tph: ["Dry Solids Feed (t/h)", 1],
        flocculant_dose_gpt: ["Flocculant Dose (g/t)", 1],
        limiting_flux_kg_m2_h: ["Limiting Flux [kg/(m²·h)]", 1],
        required_area_m2: ["Required Area (m²)", 1],
        area_utilization_pct: ["Area Utilization (%)", 1],
        predicted_underflow_solids_wt_pct: ["Underflow Solids (% w/w)", 2],
        net_solids_accumulation_tph: ["Solids Accumulation (t/h)", 2],
        overflow_clarity_index: ["Overflow Clarity Proxy (0-100, UNCALIBRATED)", 1],
        yield_stress_pa: ["Underflow Yield Stress (Pa)", 1],
        required_pump_pressure_bar: ["Required Pump Pressure (bar)", 2],
        projected_bed_level_4h_m: ["Projected Bed Level @ 4 h (m)", 2],
        projected_bed_level_8h_m: ["Projected Bed Level @ 8 h (m)", 2],
      };

      const tbody = document.getElementById("scenario-delta-body");
      tbody.innerHTML = Object.entries(labels)
        .map(([k, [label, dec]]) => {
          const d = sc.deltas[k];
          const cls = d.abs_delta >= 0 ? "delta-pos" : "delta-neg";
          return `
            <tr>
              <td>${label}</td>
              <td>${d.baseline.toFixed(dec)}</td>
              <td>${d.modified.toFixed(dec)}</td>
              <td class="${cls}">${d.abs_delta >= 0 ? "+" : ""}${d.abs_delta.toFixed(dec)}</td>
              <td class="${cls}">${d.pct_delta >= 0 ? "+" : ""}${d.pct_delta.toFixed(1)}%</td>
            </tr>
          `;
        })
        .join("");

      renderWarnings("scenario-warnings", sc.modified.warnings);
      renderScenarioCharts(sc);
    } catch (err) {
      setAlert("page-error", `Scenario error: ${err.message}`, "critical");
    } finally {
      btn.disabled = false;
      btn.textContent = "Compare Scenarios";
    }
  };

  document.getElementById("btn-preset-p4").addEventListener("click", () => {
    const b = readFormParams(baseForm, params);
    modForm.elements.feed_rate_tph.value = (b.feed_rate_tph * 1.2).toFixed(1);
    modForm.elements.flocculant_dose_gpt.value = (b.flocculant_dose_gpt * 0.5).toFixed(1);
    run();
  });

  document.getElementById("scenario-form-wrap").addEventListener("submit", (e) => {
    e.preventDefault();
    run();
  });
  btn.addEventListener("click", run);
  await run();
}

document.addEventListener("DOMContentLoaded", () => {
  initHealthIndicator();
  const page = document.body.dataset.page;
  if (page === "flux") initFluxPage();
  else if (page === "dynamics") initDynamicsPage();
  else if (page === "pumpability") initPumpabilityPage();
  else if (page === "monte_carlo") initMonteCarloPage();
  else if (page === "scenario") initScenarioPage();
});

export { resetSavedParams };
