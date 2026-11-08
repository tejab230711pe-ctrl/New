# ALE flow qualification workflow

The confirmed commands are 1200 rpm and prescribed downward feed at 75 mm/min.
`input/deposition.i` models solid contact. `input/afsd_ale_flow_stage.i` is a
separate rectangular flow prototype, not an automatic continuation of dwell.
The code uses solid-state viscoplastic flow; it has no active melting model.

Generate and run a short circular-inlet qualification case from the repository
root (Gmsh, the built application and its MOOSE runtime must be available):

```bash
python3 scripts/create_afsd_circular_flow_case.py verification_runs/my_flow --end-time 4.00001
UCX_TLS=self ./rotating_disk_deposition-opt -i verification_runs/my_flow/flow.i
python3 scripts/analyze_afsd_surface_flux.py verification_runs/my_flow
python3 scripts/check_afsd_flow_balance.py verification_runs/my_flow --max-relative-feed-error .02
```

The analysis requires NumPy/SciPy. `UCX_TLS=self` is for these serial checks,
not distributed runs. The generator initializes a uniformly hot 723.15 K domain
and an assumed divergence-free velocity field. These are explicit qualification
assumptions, not transferred contact-heating results. Use a new output directory
for each experiment to retain provenance. The source material owns the
Taylor–Quinney coefficient; the heat kernel and energy SUPG share its heat property.

**The current circular case fails the volume check.** The fixed inlet rim and
adjacent nodal free-surface motion yield about 28.36% excess volume relative to
supplied feed in the retained short test. Fluid continuity itself balances.
The checker deliberately returns exit status 2 for a failed screen or incomplete
requested interval. The 2% threshold shown is an explicit exploratory screen,
not a validated process tolerance. A small error normalized by the *entire*
domain volume can hide a large error normalized by newly supplied material.

The flux diagnostic reports fluid and mesh fluxes separately using the exported
TET4 fields. Negative relative flux across a nominal material free surface means
artificial influx. It is an end-step diagnostic, while the volume checker
integrates supplied volume over accepted steps. Neither certifies energy closure.

Before a production workflow is supported, correct the free-surface junction
kinematics, verify sustained refined runs, transfer the actual dwell state,
and implement conservative state/geometry remeshing with rod-origin transport.
Do not delete flash or replace the solved surface with a prescribed bead profile.
See `test/verification/MODELLING_IMPROVEMENTS.md` for retained results and blockers.
