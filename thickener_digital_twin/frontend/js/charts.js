/**
 * Plotly.js chart builders for all six Thickener Digital Twin pages.
 */

const BASE_LAYOUT = {
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#f8fafc",
  font: { family: "Inter, system-ui, sans-serif", size: 12, color: "#0f172a" },
  margin: { t: 44, r: 24, b: 48, l: 60 },
  hovermode: "closest",
};

const PLOT_CFG = { responsive: true, displayModeBar: true };

export function renderDashboardGaugeCharts(sim) {
  const area = sim.area_sizing;
  const pump = sim.pumpability;

  Plotly.newPlot(
    "chart-area-pressure",
    [
      {
        x: ["Required Area (m²)", "Installed Area (m²)"],
        y: [area.required_area_m2, area.actual_area_m2],
        type: "bar",
        marker: { color: [area.is_area_limited ? "#ef4444" : "#2563eb", "#0f172a"] },
        text: [area.required_area_m2.toFixed(1), area.actual_area_m2.toFixed(1)],
        textposition: "auto",
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Thickener Area Utilization (Dry-Solids Basis)",
      yaxis: { title: "Area (m²)" },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-pump-overview",
    [
      {
        x: ["Friction Drop", "Static Head", "Total Required", "Available Rating"],
        y: [
          pump.friction_pressure_bar,
          pump.static_pressure_bar,
          pump.required_pump_pressure_bar,
          pump.available_pump_pressure_bar,
        ],
        type: "bar",
        marker: {
          color: [
            "#0891b2",
            "#64748b",
            pump.is_pump_limited ? "#ef4444" : "#16a34a",
            "#0f172a",
          ],
        },
        text: [
          pump.friction_pressure_bar.toFixed(2),
          pump.static_pressure_bar.toFixed(2),
          pump.required_pump_pressure_bar.toFixed(2),
          pump.available_pump_pressure_bar.toFixed(2),
        ],
        textposition: "auto",
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Underflow Pump Pressure Breakdown (Synthetic Rheology)",
      yaxis: { title: "Pressure (bar)" },
    },
    PLOT_CFG
  );
}

export function renderFluxCharts(data) {
  const c = data.primary_curve;
  const area = data.area_sizing;

  Plotly.newPlot(
    "chart-flux-curve",
    [
      {
        x: c.phi,
        y: c.flux_kg_m2_h,
        name: `Active (${c.flocculant_info.dose_gpt} g/t)`,
        type: "scatter",
        mode: "lines",
        line: { color: "#2563eb", width: 3 },
      },
      {
        x: [c.phi_at_limiting_flux],
        y: [c.limiting_flux_kg_m2_h],
        name: `Limiting Flux F_lim = ${c.limiting_flux_kg_m2_h.toFixed(1)} kg/(m²·h)`,
        type: "scatter",
        mode: "markers",
        marker: { color: "#ef4444", size: 12, symbol: "diamond" },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Solids Flux Curve F(φ) = ρ_s · v(φ) · φ",
      xaxis: { title: "Solids Volume Fraction φ (v/v)" },
      yaxis: { title: "Dry-Solids Flux [kg/(m²·h)]" },
      legend: { orientation: "h", y: -0.2 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-settling-velocity",
    [
      {
        x: c.phi,
        y: c.settling_velocity_mph,
        name: `v(φ), v0_eff = ${c.v0_effective_mph.toFixed(2)} m/h`,
        type: "scatter",
        mode: "lines",
        line: { color: "#0891b2", width: 3 },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Richardson-Zaki Hindered Settling Velocity v(φ)",
      xaxis: { title: "Solids Volume Fraction φ (v/v)" },
      yaxis: { title: "Settling Velocity v(φ) [m/h]" },
    },
    PLOT_CFG
  );

  const compTraces = data.dose_comparisons.map((d) => ({
    x: d.phi,
    y: d.flux_kg_m2_h,
    name: `${d.dose_gpt} g/t (F_lim=${d.limiting_flux_kg_m2_h.toFixed(0)})`,
    type: "scatter",
    mode: "lines",
  }));

  Plotly.newPlot(
    "chart-floc-comparison",
    compTraces,
    {
      ...BASE_LAYOUT,
      title: "Flocculant Dose-Response Comparison (Bounded Diminishing Returns)",
      xaxis: { title: "Solids Volume Fraction φ (v/v)" },
      yaxis: { title: "Dry-Solids Flux [kg/(m²·h)]" },
      legend: { orientation: "h", y: -0.25 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-area-comparison",
    [
      {
        x: ["Required Area", "Installed Area"],
        y: [area.required_area_m2, area.actual_area_m2],
        type: "bar",
        marker: { color: [area.is_area_limited ? "#ef4444" : "#16a34a", "#1e293b"] },
        text: [`${area.required_area_m2.toFixed(1)} m²`, `${area.actual_area_m2.toFixed(1)} m²`],
        textposition: "auto",
      },
    ],
    {
      ...BASE_LAYOUT,
      title: `Area Check (Utilization: ${(area.area_utilization_ratio * 100).toFixed(1)}%)`,
      yaxis: { title: "Thickener Area (m²)" },
    },
    PLOT_CFG
  );
}

export function renderDynamicsCharts(dyn) {
  const t = dyn.time_h;
  const stepLine = {
    type: "line",
    x0: dyn.step_time_h,
    x1: dyn.step_time_h,
    y0: 0,
    y1: 1,
    yref: "paper",
    line: { color: "#f59e0b", width: 2, dash: "dash" },
  };

  Plotly.newPlot(
    "chart-dyn-solids-flow",
    [
      { x: t, y: dyn.feed_dry_solids_tph, name: "Incoming Dry Solids (t/h)", mode: "lines", line: { color: "#2563eb", width: 2.5 } },
      { x: t, y: dyn.underflow_dry_solids_tph, name: "Outgoing Dry Solids (t/h)", mode: "lines", line: { color: "#16a34a", width: 2.5 } },
      { x: t, y: dyn.overflow_solids_loss_tph, name: "Overflow Solids Carryover (t/h)", mode: "lines", line: { color: "#ef4444", width: 2, dash: "dot" } },
    ],
    {
      ...BASE_LAYOUT,
      title: "Dry Solids Mass Balance Flows",
      xaxis: { title: "Time (h)" },
      yaxis: { title: "Dry Solids Rate (t/h)" },
      shapes: [stepLine],
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-dyn-withdrawal",
    [
      { x: t, y: dyn.feed_slurry_tph, name: "Feed Slurry (t/h)", mode: "lines", line: { color: "#0891b2", width: 2.5 } },
      { x: t, y: dyn.underflow_slurry_tph, name: "Underflow Slurry Withdrawal (t/h)", mode: "lines", line: { color: "#7c3aed", width: 2.5 } },
    ],
    {
      ...BASE_LAYOUT,
      title: "Slurry Feed vs Underflow Withdrawal",
      xaxis: { title: "Time (h)" },
      yaxis: { title: "Slurry Flow (t/h)" },
      shapes: [stepLine],
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-dyn-bed-level",
    [
      { x: t, y: dyn.bed_level_m, name: "Mud Bed Level (m)", mode: "lines", line: { color: "#b45309", width: 3 } },
      { x: t, y: t.map(() => dyn.tank_depth_m), name: "Tank Depth Limit (m)", mode: "lines", line: { color: "#ef4444", dash: "dash" } },
    ],
    {
      ...BASE_LAYOUT,
      title: "Dynamic Mud Bed Level Response",
      xaxis: { title: "Time (h)" },
      yaxis: { title: "Bed Level (m)", range: [0, dyn.tank_depth_m * 1.1] },
      shapes: [stepLine],
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-dyn-underflow",
    [
      { x: t, y: dyn.underflow_solids_wt_pct, name: "Underflow Solids (% w/w)", mode: "lines", line: { color: "#0f172a", width: 2.5 } },
      { x: t, y: dyn.overflow_clarity_index, name: "Clarity Proxy (0-100, UNCALIBRATED)", mode: "lines", yaxis: "y2", line: { color: "#0284c7", width: 2, dash: "dot" } },
    ],
    {
      ...BASE_LAYOUT,
      title: "Underflow % Solids & Clarity Proxy Trajectory",
      xaxis: { title: "Time (h)" },
      yaxis: { title: "Underflow Solids (% w/w)" },
      yaxis2: { title: "Clarity Proxy", overlaying: "y", side: "right", range: [0, 105] },
      shapes: [stepLine],
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );
}

export function renderPumpabilityCharts(data) {
  const ev = data.evaluation;
  const c = data.curve;

  Plotly.newPlot(
    "chart-yield-stress",
    [
      {
        x: c.underflow_solids_wt_pct,
        y: c.yield_stress_pa,
        name: "Synthetic Yield Stress τ_y",
        type: "scatter",
        mode: "lines",
        line: { color: "#7c3aed", width: 3 },
      },
      {
        x: [ev.underflow_solids_wt_pct],
        y: [ev.yield_stress_pa],
        name: `Target (${ev.underflow_solids_wt_pct.toFixed(1)}% w/w, ${ev.yield_stress_pa.toFixed(1)} Pa)`,
        type: "scatter",
        mode: "markers",
        marker: { color: ev.is_pump_limited ? "#ef4444" : "#16a34a", size: 12 },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Synthetic Rheology Curve: Yield Stress vs Underflow % Solids",
      xaxis: { title: "Underflow Solids (% w/w)" },
      yaxis: { title: "Yield Stress τ_y (Pa)" },
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-pump-pressure",
    [
      {
        x: c.underflow_solids_wt_pct,
        y: c.required_pump_pressure_bar,
        name: "Required Pump Pressure",
        type: "scatter",
        mode: "lines",
        line: { color: "#2563eb", width: 3 },
      },
      {
        x: c.underflow_solids_wt_pct,
        y: c.underflow_solids_wt_pct.map(() => ev.available_pump_pressure_bar),
        name: `Available PD Pump Rating (${ev.available_pump_pressure_bar.toFixed(1)} bar)`,
        type: "scatter",
        mode: "lines",
        line: { color: "#ef4444", width: 2, dash: "dash" },
      },
      {
        x: [ev.underflow_solids_wt_pct],
        y: [ev.required_pump_pressure_bar],
        name: `Target (${ev.required_pump_pressure_bar.toFixed(2)} bar)`,
        type: "scatter",
        mode: "markers",
        marker: { color: ev.is_pump_limited ? "#ef4444" : "#16a34a", size: 12 },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Required vs Available Pump Pressure",
      xaxis: { title: "Underflow Solids (% w/w)" },
      yaxis: { title: "Discharge Pressure (bar)" },
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );
}

export function renderMonteCarloCharts(mc) {
  const s = mc.underflow_solids_stats;
  const shapes = [
    { type: "line", x0: s.p5, x1: s.p5, y0: 0, y1: 1, yref: "paper", line: { color: "#f59e0b", dash: "dash", width: 2 } },
    { type: "line", x0: s.mean, x1: s.mean, y0: 0, y1: 1, yref: "paper", line: { color: "#0f172a", width: 2.5 } },
    { type: "line", x0: s.p95, x1: s.p95, y0: 0, y1: 1, yref: "paper", line: { color: "#f59e0b", dash: "dash", width: 2 } },
  ];
  if (mc.max_pumpable_solids_wt_pct !== null) {
    shapes.push({
      type: "line",
      x0: mc.max_pumpable_solids_wt_pct,
      x1: mc.max_pumpable_solids_wt_pct,
      y0: 0,
      y1: 1,
      yref: "paper",
      line: { color: "#ef4444", dash: "dot", width: 2.5 },
    });
  }

  Plotly.newPlot(
    "chart-mc-uf-hist",
    [
      {
        x: mc.samples.underflow_solids_wt_pct,
        type: "histogram",
        nbinsx: 35,
        marker: { color: "#2563eb", opacity: 0.78 },
        name: "Underflow % Solids",
      },
    ],
    {
      ...BASE_LAYOUT,
      title: `Underflow % Solids Distribution (P5=${s.p5.toFixed(1)}%, Mean=${s.mean.toFixed(1)}%, P95=${s.p95.toFixed(1)}%)`,
      xaxis: { title: "Predicted Underflow Solids (% w/w)" },
      yaxis: { title: "Trial Count" },
      shapes,
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-mc-pressure-hist",
    [
      {
        x: mc.samples.pump_pressure_bar,
        type: "histogram",
        nbinsx: 35,
        marker: { color: "#7c3aed", opacity: 0.78 },
        name: "Required Pressure (bar)",
      },
    ],
    {
      ...BASE_LAYOUT,
      title: `Pump Pressure Distribution (Violation Prob: ${mc.pumpability_violation_probability_pct.toFixed(1)}%)`,
      xaxis: { title: "Required Pump Pressure (bar)" },
      yaxis: { title: "Trial Count" },
      shapes: [
        {
          type: "line",
          x0: mc.available_pump_pressure_bar,
          x1: mc.available_pump_pressure_bar,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: "#ef4444", width: 2.5, dash: "dash" },
        },
      ],
    },
    PLOT_CFG
  );

  const feasibleX = [];
  const feasibleY = [];
  const limitedX = [];
  const limitedY = [];
  mc.samples.feed_rate_tph.forEach((f, i) => {
    if (mc.samples.is_pump_limited[i]) {
      limitedX.push(f);
      limitedY.push(mc.samples.underflow_solids_wt_pct[i]);
    } else {
      feasibleX.push(f);
      feasibleY.push(mc.samples.underflow_solids_wt_pct[i]);
    }
  });

  Plotly.newPlot(
    "chart-mc-scatter",
    [
      { x: feasibleX, y: feasibleY, mode: "markers", type: "scatter", name: "Feasible", marker: { color: "#16a34a", size: 5, opacity: 0.65 } },
      { x: limitedX, y: limitedY, mode: "markers", type: "scatter", name: "Pump-limited", marker: { color: "#ef4444", size: 6, opacity: 0.8 } },
    ],
    {
      ...BASE_LAYOUT,
      title: "Sampled Feed Rate vs Predicted Underflow Solids",
      xaxis: { title: "Sampled Feed Rate (t/h)" },
      yaxis: { title: "Underflow Solids (% w/w)" },
      legend: { orientation: "h", y: -0.2 },
    },
    PLOT_CFG
  );
}

export function renderScenarioCharts(sc) {
  const b = sc.baseline.kpis;
  const m = sc.modified.kpis;

  Plotly.newPlot(
    "chart-scenario-bars",
    [
      {
        x: ["Underflow %", "Clarity Proxy", "Area Util %", "Req Press (bar)"],
        y: [
          b.predicted_underflow_solids_wt_pct,
          b.overflow_clarity_index,
          b.area_utilization_pct,
          b.required_pump_pressure_bar,
        ],
        name: "Baseline",
        type: "bar",
        marker: { color: "#1e293b" },
      },
      {
        x: ["Underflow %", "Clarity Proxy", "Area Util %", "Req Press (bar)"],
        y: [
          m.predicted_underflow_solids_wt_pct,
          m.overflow_clarity_index,
          m.area_utilization_pct,
          m.required_pump_pressure_bar,
        ],
        name: "Modified Scenario",
        type: "bar",
        marker: { color: "#2563eb" },
      },
    ],
    {
      ...BASE_LAYOUT,
      barmode: "group",
      title: "Baseline vs Modified KPI Comparison",
      legend: { orientation: "h", y: -0.2 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-scenario-flux",
    [
      {
        x: sc.baseline.flux_curve.phi,
        y: sc.baseline.flux_curve.flux_kg_m2_h,
        name: `Baseline (F_lim=${b.limiting_flux_kg_m2_h.toFixed(0)} kg/m²·h)`,
        type: "scatter",
        mode: "lines",
        line: { color: "#1e293b", width: 2.5 },
      },
      {
        x: sc.modified.flux_curve.phi,
        y: sc.modified.flux_curve.flux_kg_m2_h,
        name: `Modified (F_lim=${m.limiting_flux_kg_m2_h.toFixed(0)} kg/m²·h)`,
        type: "scatter",
        mode: "lines",
        line: { color: "#ef4444", width: 2.5, dash: "dash" },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "Solids Flux Shift (Baseline vs Modified Flocculant)",
      xaxis: { title: "Solids Volume Fraction φ" },
      yaxis: { title: "Solids Flux [kg/(m²·h)]" },
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );

  Plotly.newPlot(
    "chart-scenario-bed",
    [
      {
        x: sc.baseline.bed_projection.time_h,
        y: sc.baseline.bed_projection.bed_level_m,
        name: "Baseline Bed Level (m)",
        type: "scatter",
        mode: "lines",
        line: { color: "#1e293b", width: 2.5 },
      },
      {
        x: sc.modified.bed_projection.time_h,
        y: sc.modified.bed_projection.bed_level_m,
        name: "Modified Bed Level (m)",
        type: "scatter",
        mode: "lines",
        line: { color: "#f59e0b", width: 3 },
      },
    ],
    {
      ...BASE_LAYOUT,
      title: "8-Hour Projected Mud Bed Trajectory",
      xaxis: { title: "Time (h)" },
      yaxis: { title: "Bed Level (m)" },
      legend: { orientation: "h", y: -0.22 },
    },
    PLOT_CFG
  );
}
