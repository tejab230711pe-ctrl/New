# Numerical experiment data

These files contain MOOSE simulation results, not laboratory measurements.
The user will supply/check independent experimental measurements for validation.

- `hot_flow_1ms.csv`: accepted solution history from `verification_runs/variable_mu_flow`,
  with the initially assumed 723.15 K flow domain. Time 4 s is the assumed start
  of this separate flow qualification, not a solved cold-to-hot dwell history.
  Temperature columns are kelvin; area is m² and volume is m³.

See `../NUMERICAL_EXPERIMENTS.md` for acceptance limits, mesh-area error,
failed alternatives and the full-process limitations. Source decks, geometry,
qualification reports and artifact hashes remain in the corresponding run folders.
