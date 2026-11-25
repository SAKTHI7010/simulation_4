# Raw Plant Data Import Directory

No measured Project 4 plant dataset was supplied with the specification.
Place measured batch-settling test tables or plant historian CSV exports here when available for calibration.

## Required Columns for Real-Plant Calibration
- `record_id`
- `feed_rate_tph` (specify slurry or dry-solids basis)
- `feed_solids_wt_pct` (% w/w)
- `flocculant_dose_gpt` (g/t dry solids)
- `underflow_withdrawal_tph` (specify slurry or dry-solids basis)
- `free_settling_velocity_mph` (m/h, from batch settling curve)
- `rz_exponent_n` (dimensionless, fitted from hindered settling curve)
- `thickener_area_m2` (m^2)
- `underflow_solids_wt_pct` (% w/w measured)
- `overflow_clarity_index` (or measured turbidity NTU / TSS mg/L)
- `bed_level_m` (m)
- `yield_stress_pa` (Pa, from rheometer)
- `pump_pressure_required_bar` (bar, measured discharge pressure)
- `pumpability_flag` (`Feasible` or `Pump-limited`)

You can audit an imported CSV using:
```bash
python -m backend.data_audit --input data/raw/<your_file>.csv
```
