# Numerical experiments and implementation — 8 November 2026

This report supersedes the current-status paragraphs in the earlier modelling
report. These are simulations, not physical experiments. The user will check
measured data. Confirmed process dimensions and commands are recorded in
`input/process_specification.json`: 25 mm diameter × 200 mm rod,
50 × 100 × 10 mm plate, 1200 rpm and prescribed 75 mm/min downward feed.
The existing 4 s dwell and 50 mm travel during 35 mm consumption are assumptions.

## Latest coupled checks

The temperature-dependent viscosity contribution to stress divergence is now
included in SUPG/PSPG stabilization through `AFSDStabilized3Eqn`. This correction
is restricted to affine FIRST-order TET4 velocity fields, where the strain rate
is spatially constant inside each element; unsupported elements are rejected.
`check_variable_viscosity.py` verifies the property gradient independently by
finite differences, the clamped branch, the actual momentum residual, and the
unsupported-element guard.

The resulting `variable_mu_flow` case completes 1 ms and passes the existing
screens: maximum feed-volume error 0.8087%, absolute surface leakage 0.6632%,
minimum element-volume ratio 0.9426 and Tmax 738.092 K. These remain short,
initially hot qualification runs, not predictions starting from the cold rod.
The coarse polygonal inlet area is 3.323% below the nominal circular area; volume
screens use the actual mesh area. Geometric and spatial refinement remain needed.

`trace_afsd_rod_material.py` follows rod-origin particles through accepted
velocity/mesh fields using tetrahedral interpolation. The latest run tracks
2,898 particles with no unlocated particles. Some rod material has negative
velocity relative to the moving tool, but **none has yet reached the trailing
region**. Rotation alone is not proof of backward deposition. Particle volume
bookkeeping is not an independent conservation test or a conservative material
concentration solution.

The confirmed cylindrical solid-contact case completes three 25 microsecond
steps. The original quadrature gap treatment fails the declared 2% thermal
screen, losing about 7.50% of generated friction heat. Tighter scaled tolerances
do not remove that deficit.

**The corrected `direct_mortar_bulk` case completes all three steps and passes:**
maximum discrete thermal-budget error is **0.000176%**, with no plastic strain.
`AFSDConservativeContactHeat` integrates finite conductance on one shared mortar
interface, applying equal-and-opposite fluxes without additional thermal
multiplier unknowns. Open gaps do not conduct through this contact model. Bulk
heat kernels and materials are explicitly restricted to the plate and rod;
otherwise lower-dimensional mortar elements introduce spurious surface storage.
The isolated actual-MOOSE tests also pass partial-footprint conservation,
hot-to-cold heat transfer and open-gap insulation. The thermal multiplier variant
remains a failed coupled diagnostic, not the selected generator default.

The budget integrates the backward-Euler capacity term using **current volume**
and end-step rho/cp, matching MOOSE's displaced thermal kernel defaults. It also
reports a reference-volume enthalpy diagnostic separately. This checks the
assembled thermal equation; it does not establish full actuator-work balance,
finite-deformation mass/energy conservation, or complete deposition. The run
still has a small temperature undershoot below ambient that needs numerical
refinement/monotonicity work. No temperatures were clipped to hide it.

The dwell generator now selects direct conservative mortar by default, preserves
the old quadrature source as a reference and includes INITIAL Exodus output for
audit. A fresh generated input passes MOOSE's input check. The retained coupled
run's `T_mean` includes interface averaging; do not use that column. The generator
now restricts that postprocessor to the bulk, and the exported comparison table
omits `T_mean`.

## Free-surface conservation correction

The coplanar inlet/free-surface junction made incompatible normal-motion demands
at the inlet rim. The qualification mesh now includes a short upstream rod
section. Its inlet mesh rotates and translates, remaining fixed in Z while
material enters through it. Layered extrusion makes the initial side facets
vertical, so axial feed is tangent to them. Refining the upper rod layers reduces
junction interpolation error without modifying feed, forcing a bead shape, or
rescaling the resulting volume.

`AFSDDisplaceBoundaryBC` uses the same nodal time derivative as the ALE fluid and
energy kernels. It supports implicit Euler and BDF2 (including BDF2's Euler
startup); it rejects unsupported integrators. This replaces the framework's
Euler-only displacement update in generated qualification cases. Manufactured
constant-velocity translation passes for both schemes. Variable-step BDF2
postprocessing is checked against an exact quadratic history.

| Retained run | Simulated duration | Result |
| --- | --- | --- |
| `circular_flow_tags_fixed` | 10 µs | Original coplanar case: **28.36% excess feed volume**, rejected |
| `extruded_inlet` | 3 µs, Euler 1 µs steps | Maximum volume error **0.805%** |
| `extruded_dt05us` | 3 µs, Euler 0.5 µs steps | Maximum volume error **0.402%**; all numerical screens pass |
| `bdf2_refined` | 100 µs, 4 mm in-plane mesh | Maximum volume error **0.375%**, local surface leakage **1.263%**; all screens pass |
| `bdf2_qualified` | 1 ms, one upstream layer | Volume passes, but **3.477% absolute local leakage** fails the 2% screen |
| `bdf2_inlet_layers4` | 1 ms, four upstream layers | All screens pass: worst volume error **0.809%**, final signed error **-0.0506%**, maximum absolute local leakage **0.663%**, minimum element-volume ratio **0.943** |

All run directories are under `verification_runs/`. The last run used BDF2,
0.5 µs startup, adaptive steps capped at 20 µs, 6 mm in-plane mesh and four
layers in the 4 mm upstream rod section. It took approximately 166 s here.
Tmax reached 738.086 K from the assumed uniform initial 723.15 K. Finer meshes
change temperature and velocity fields; these runs do not establish spatially
converged process predictions. Positive volume is necessary but not a complete
mesh-shape-quality criterion.

The 2% volume/leakage and 1e-6 net-continuity thresholds are explicit numerical
screens, not experimentally justified accuracy tolerances. Every accepted step
is checked. Local absolute surface leakage is checked separately from net volume
so opposing errors cannot hide one another. The original failing case remains
in the regression evidence. CSV/Exodus times must match; incomplete intervals,
nonfinite values and inverted elements cannot pass. The temperature screen
293.15–798.15 K uses existing diagnostic bounds, not a measured melting range.

Reproduce the longest passing qualification case:

```bash
python3 scripts/create_afsd_circular_flow_case.py verification_runs/my_flow \
  --end-time 4.001 --scheme bdf2 --time-step 5e-7 --max-time-step 2e-5 --rod-layers 4
UCX_TLS=self ./rotating_disk_deposition-opt -i verification_runs/my_flow/flow.i
python3 scripts/qualify_afsd_flow.py verification_runs/my_flow \
  --volume-tolerance .02 --surface-tolerance .02 --continuity-tolerance 1e-6
```

The checker writes `qualification.json`, `balance.json` and `surface_flux.json`,
including hashes of the evaluated input, mesh, CSV, Exodus and case metadata.
Its exit code is 2 for a failed screen. The hot initial pad and velocity profile
remain explicit qualification assumptions, not a solved dwell handoff.

## Solved-slip contact heating

`PenaltyContactHeatPowerAux` reads the actual contact force and incremental slip
from MOOSE's penetration information. For fixed, unnormalized Coulomb penalty
contact, it projects onto the current tangent plane and computes

`plastic_slip = incremental_slip_t - (force_t - old_force_t)/penalty`

`heat_power = efficiency * max(0, force_t dot plastic_slip) / dt`.

Thus recoverable tangential penalty-spring motion does not become friction heat.
The signed quantity discarded by the positive clamp is separately reported.
The output is **nodal watts**, applied once through `CoupledForceNodalKernel` and
summed with `NodalSum`; it must not be integrated again as a W/m² flux.

The formulation follows the return map in local MOOSE
`modules/contact/src/constraints/MechanicalContactConstraint.C` and its slip
calculation in `framework/src/geomsearch/PenetrationThread.C`. It is restricted to
this penalty formulation. It is not a generic heating law for mortar, augmented
Lagrange, changing penalty stiffness or normalized penalty contact.

Analytical C++ checks pass for sticking, elastic unloading, sliding, reversal,
normal approach and rotated coordinates. In the retained coupled 25 µs test:

- Solved friction heat: **169.321 W**; discarded negative power: **0 W**.
- Signed spindle torque: **1.69857 Nm**.
- Tmin/Tmax: **293.14786 / 293.15680 K**. The slight numerical undershoot is open.
- With friction coefficient zero, heat is **5.2e-20 W**, and temperature remains
  293.15 K to approximately 1e-9 K.

The inputs explicitly use diagnostic penalty 1e7 N/m, conductance 1e7 and the
existing 5.15 µm initial interference. These are not calibrated physical values.
All heat enters the secondary side and is exchanged through thermal contact;
heat partition and the full mechanical/thermal energy budget remain unverified.
The older main template retains its imposed-speed source as a reference;
`scripts/enable_solved_contact_heat.py` generates a separately labeled solved-slip
variant and preserves the source file. Its penalty substitution follows the
mechanical contact parameter, including command-line overrides.

## Confirmed-geometry solid case

The supported generator is `scripts/create_afsd_dwell_case.py`; it reads the
confirmed dimensions through the stage geometry module and requires explicit
interference, penalty and conductance. It creates a cylinder and plate without
a prescribed bead, and uses solved-slip heating:

```bash
python3 scripts/create_afsd_dwell_case.py verification_runs/my_dwell \
  --initial-interference-mm .00515 --penalty 1e7 --gap-conductance 1e7 \
  --end-time .000025
UCX_TLS=self ./rotating_disk_deposition-opt -i verification_runs/my_dwell/dwell.i
```

The `.00515` mm loading assumption reproduces the diagnostic case; it is not a
confirmed machine preload. Omitting `--end-time` requests the assumed 4 s dwell,
which has not been demonstrated. `input/deposition.i` is the legacy rectangular
rendering template, not the confirmed physical geometry entry point.

## Checks

```bash
python3 scripts/check_process_mechanics.py
python3 scripts/check_thermal_expansion.py
python3 scripts/check_ale_boundary.py
python3 test/verification/test_surface_flux.py
python3 test/verification/test_rod_tracking.py
python3 test/verification/test_thermal_budget.py
python3 scripts/check_variable_viscosity.py
python3 scripts/check_mortar_heat.py
c++ -std=c++17 -Isrc test/verification/test_penalty_slip.cpp -o /tmp/test_penalty_slip
/tmp/test_penalty_slip
```

The application-only build and these tests pass. The build reuses the installed
MOOSE dependencies; it is not a clean rebuild of all dependency libraries.
The original contact CSV was regenerated from its retained Exodus globals after
a qualification variant initially reused the CSV output path; the converter now
writes all outputs beside its target input to prevent recurrence.

## What is still required for the requested full process

Passing these experiments does not complete predictive deposition. Still required:

1. A complete contact/heating dwell with justified initial loading, refined
   thermal/contact behavior and actuator/thermal energy closure.
2. A physically specified, conservative transfer from that solved solid state to
   flow; no uniformly hot initialization as a substitute for friction heating.
3. Conservative rod-origin transport, free-surface remeshing and continuation
   through the full feed/traverse interval, preserving rod/deposit history.
4. Solved rod-material trajectories into the wake and bead/flash cross-sections,
   with mesh/time refinement and final cooling where claimed.
5. Comparison against the user's measured data before claiming predictive validity.

No laboratory experiments, complete 4 s dwell, 28 s deposition, or validated
mushroom-shaped track have been produced by these numerical qualification tests.
