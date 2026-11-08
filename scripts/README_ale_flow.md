# AFSD numerical qualification workflow

The confirmed commands are 1200 rpm and prescribed downward feed at 75 mm/min.
The confirmed geometry is a 25 mm diameter × 200 mm rod and a 50 × 100 × 10 mm
plate. `input/process_specification.json` distinguishes confirmations from
existing timing assumptions. The user will compare numerical experiments with
measured data; these scripts do not perform physical experiments.

Generate and run the tested circular hot-flow qualification from the repository
root (Gmsh, NumPy/SciPy, the built application and its MOOSE runtime are required):

```bash
python3 scripts/create_afsd_circular_flow_case.py verification_runs/my_flow \
  --end-time 4.001 --scheme bdf2 --time-step 5e-7 --max-time-step 2e-5 --rod-layers 4
UCX_TLS=self ./rotating_disk_deposition-opt -i verification_runs/my_flow/flow.i
python3 scripts/qualify_afsd_flow.py verification_runs/my_flow \
  --volume-tolerance .02 --surface-tolerance .02 --continuity-tolerance 1e-6
```

The generator now defaults to this time scheme and mesh layering. Use a new
output directory for each experiment. `UCX_TLS=self` is for serial checks, not
MPI campaigns. A supported original-case comparison uses the retained files in
`verification_runs/circular_flow_tags_fixed`; the new generator changes the
inlet geometry and mesh motion, so setting zero extension alone does not exactly
reproduce every aspect of that historical case.

The retained 1 ms four-layer case passes all numerical screens. The original
coplanar case fails. A one-layer 1 ms case passes total volume but fails local
surface leakage: this is why both quantities are checked. The checker writes
JSON diagnostics and artifact hashes, and returns 2 on rejection. The thresholds
shown are exploratory numerical screens, not validated prediction tolerances.

The flow generator assumes an initially hot 723.15 K pad and a divergence-free
velocity seed. The short upstream rod section is a truncated qualification domain,
not the full 200 mm rod. No actual dwell-state transfer is performed. The thermal
model is solid-state viscoplasticity, with no active phase-change model. A full
energy balance has not been demonstrated.

For the confirmed full rod/plate geometry and solved-slip contact heating:

```bash
python3 scripts/create_afsd_dwell_case.py verification_runs/my_dwell \
  --initial-interference-mm .00515 --penalty 1e7 --gap-conductance 1e7 \
  --end-time .000025
UCX_TLS=self ./rotating_disk_deposition-opt -i verification_runs/my_dwell/dwell.i
```

Interference and contact parameters above reproduce a numerical diagnostic;
they are not calibrated machine loading. The generator does not require a bead
profile. The old rectangular `input/deposition.i` remains its rendering template.
A separate conversion script, `enable_solved_contact_heat.py`, preserves a source
input while creating a fixed-penalty solved-slip heating variant. Its heat field
is nodal W, not W/m². It does not support normalized/augmented/mortar penalties.

Before complete deposition is supported, demonstrate the complete dwell,
conservative solved-state handoff, rod-origin transport, surface remeshing and
full feed/traverse continuation. No prescribed bead profile or assumed flash
percentage can replace those calculations. See
`test/verification/NUMERICAL_EXPERIMENTS.md` for the evidence and remaining work.

For a qualified flow directory, inspect rod-origin transport separately:

```bash
python3 scripts/trace_afsd_rod_material.py verification_runs/variable_mu_flow
```

This requires passing qualification and checks the Exodus hash. Outputs include
`rod_particles.csv`, selected `rod_trajectories.csv` and `rod_transport.json`.
These passive particles do not establish a conservative concentration field.

For an elastic contact run with INITIAL Exodus output, audit generated heat:

```bash
python3 scripts/check_contact_thermal_balance.py verification_runs/confirmed_geometry_3steps --tolerance .02
```

The retained three-step quadrature-gap run fails this screen. A separate mortar
candidate is generated with `enable_mortar_contact_heat.py SOURCE.i TARGET.i`;
this is thermal coupling only and retains penalty mechanical contact. Consult
the numerical report before selecting a qualified variant.
