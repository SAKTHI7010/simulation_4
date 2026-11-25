/**
 * Dashboard (Page 1) controller for Thickener Digital Twin.
 */

import { api, loadSavedParams, resetSavedParams, saveParams } from "/js/api.js";
import { populateFormFromParams, readFormParams, renderWarnings, setAlert } from "/js/app.js";
import { renderDashboardGaugeCharts } from "/js/charts.js";

async function loadDatasetPreview() {
  const box = document.getElementById("dataset-preview-meta");
  const tbody = document.getElementById("dataset-preview-body");
  try {
    const ds = await api.datasetSummary();
    const m = ds.metadata || {};
    box.innerHTML = `<span class="badge badge-synthetic">${ds.data_status}</span> ${m.n_rows || "?"} generated rows (Seed ${m.random_seed || 42}) • Feed ${m.reference_ranges_covered?.feed_solids_wt_pct?.map((x) => x.toFixed(1)).join("–")}% w/w • Pump-limited share: ${m.pump_limited_fraction_pct ?? "?"}%`;
    tbody.innerHTML = (ds.preview_rows || [])
      .slice(0, 6)
      .map(
        (r) => `
        <tr>
          <td>${r.record_id}</td>
          <td><span class="badge badge-synthetic">${r.data_source_label}</span></td>
          <td>${r.feed_rate_tph}</td>
          <td>${r.feed_solids_wt_pct}</td>
          <td>${r.flocculant_dose_gpt}</td>
          <td>${r.underflow_solids_wt_pct}</td>
          <td>${r.overflow_clarity_index}</td>
          <td>${r.pump_pressure_required_bar} bar</td>
          <td><span class="badge ${r.pumpability_flag === "Pump-limited" ? "badge-danger" : "badge-ok"}">${r.pumpability_flag}</span></td>
        </tr>
      `
      )
      .join("");
  } catch (err) {
    box.textContent = `Dataset preview unavailable: ${err.message}`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("dashboard-form");
  const runBtn = document.getElementById("btn-run-sim");
  const resetBtn = document.getElementById("btn-reset-defaults");
  const params = loadSavedParams();
  populateFormFromParams(form, params);

  const runSim = async () => {
    setAlert("page-error", "");
    runBtn.disabled = true;
    runBtn.textContent = "Simulating...";
    try {
      const payload = readFormParams(form, loadSavedParams());
      saveParams(payload);
      const sim = await api.simulate(payload);

      const inp = sim.inputs_summary;
      const uf = sim.underflow;
      const cl = sim.overflow_clarity;
      const pm = sim.pumpability;
      const ar = sim.area_sizing;

      document.getElementById("kpi-feed-rate").textContent = `${inp.dry_solids_feed_tph.toFixed(1)} t/h`;
      document.getElementById("kpi-feed-rate-sub").textContent = `${inp.slurry_feed_tph.toFixed(1)} t/h slurry (${inp.feed_rate_basis})`;
      document.getElementById("kpi-feed-solids").textContent = `${inp.feed_solids_wt_pct.toFixed(1)}% w/w`;
      document.getElementById("kpi-feed-phi").textContent = `φ = ${inp.feed_volume_fraction_phi.toFixed(4)} v/v`;
      document.getElementById("kpi-uf-solids").textContent = `${uf.predicted_underflow_solids_wt_pct.toFixed(1)}% w/w`;
      document.getElementById("kpi-uf-regime").textContent = uf.limiting_regime;
      document.getElementById("kpi-bed-level").textContent = `${inp.bed_level_m.toFixed(2)} m`;
      document.getElementById("kpi-bed-sub").textContent = `Accumulation: ${uf.net_solids_accumulation_tph >= 0 ? "+" : ""}${uf.net_solids_accumulation_tph.toFixed(1)} t/h`;
      document.getElementById("kpi-clarity").textContent = `${cl.overflow_clarity_index.toFixed(1)} / 100`;
      document.getElementById("kpi-clarity-sub").textContent = `${cl.clarity_band} • UNCALIBRATED PROXY`;

      const pumpEl = document.getElementById("kpi-pump-status");
      pumpEl.textContent = pm.pumpability_flag;
      pumpEl.style.color = pm.is_pump_limited ? "#b91c1c" : "#15803d";
      document.getElementById("kpi-pump-sub").textContent = `${pm.required_pump_pressure_bar.toFixed(2)} / ${pm.available_pump_pressure_bar.toFixed(1)} bar • Area util ${(ar.area_utilization_ratio * 100).toFixed(0)}%`;

      renderWarnings("dashboard-warnings", sim.warnings);
      renderDashboardGaugeCharts(sim);
    } catch (err) {
      setAlert("page-error", `Simulation error: ${err.message}`, "critical");
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Run Simulation";
    }
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    runSim();
  });

  resetBtn.addEventListener("click", () => {
    const def = resetSavedParams();
    populateFormFromParams(form, def);
    runSim();
  });

  runSim();
  loadDatasetPreview();
});
