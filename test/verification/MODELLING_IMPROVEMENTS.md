# Modelling improvements — 8 November 2026

This work follows `PROCESS_MECHANICS.md`. The FreeFEM reference is not a
mechanical specification. This report supersedes earlier baseline results where
noted; it does not establish a complete predictive deposition workflow.

## Implemented changes

- The standalone template rotates about its actual rod reference center
  (Y = 0.050 m) and adds the intended Y translation to the rotating spindle.
- A shared absolute-center function drives the friction-radius diagnostic,
  boundary heat-source center and torque axis. Generated stages replace this
  function consistently. Stage translation is clamped at its endpoints.
- `MovingAxisTorqueReaction` calculates the signed resultant moment about the
  current axis on the displaced mesh. The previous MOOSE `TorqueReaction`
  sums the magnitudes of individual nodal moments and uses a fixed origin.
  Opposing nodal moments now cancel. Signed torque changes the meaning of the
  associated signed spindle-power output; old magnitude-only histories are not
  directly comparable.
- Only the rod's top spindle face has prescribed rotation/feed. The bottom
  displacement constraints were removed so contact and stress determine the tip
  motion. A 25-microsecond free-tip contact increment now converges with PJFNK;
  sustained dwell still needs verification.
- Mechanical contact uses the full penalty formulation instead of
  `tangential_penalty`. A controlled diagnostic with the old driven-tip setup
  showed the latter failing at its first linear solve while penalty advanced.
  This is not a proof of penalty accuracy or of stability with a free tip.
- Thermal contact uses quadrature-based gap transfer. On a plate larger than the
  rod footprint, the old nodal setup creates false thermal transients even with
  no heat sources. Quadrature search excludes unmatched surface regions.
- The ALE law now uses J2 equivalent strain rate `sqrt(2/3 D:D + epsilon^2)`
  rather than `sqrt(2 D:D + epsilon^2)`, consistent with its
  `mu = sigma_equivalent/(3*equivalent_rate)` convention for incompressible flow.
- Low-memory rendering no longer silently reduces contact penalty or thermal
  conductance, or relaxes nonlinear/linear convergence tolerances. It still
  selects PJFNK with a pivoting LU preconditioner, backtracking, smaller
  timesteps and reduced Exodus output. The template nonlinear tolerances are now 1e-7 relative and
  1e-8 absolute. Physical/numerical sensitivity studies must use explicit inputs.
- Added minimum and mean temperature diagnostics. The imposed-speed friction
  heat approximation is explicitly labeled; it has not become a solved-slip
  dissipation model merely because its moving center is now correct.

## Reproducible checks

Run from the repository root:

```bash
python3 scripts/check_process_mechanics.py
python3 scripts/check_thermal_expansion.py
UCX_TLS=self ./rotating_disk_deposition-opt -i input/deposition.i --check-input
UCX_TLS=self ./rotating_disk_deposition-opt -i input/afsd_ale_flow_stage.i --check-input
```

The mechanics checker uses actual MOOSE functions/materials/postprocessors,
including freshly rendered dwell and first-feed kinematics. Synthetic stage
metadata avoids requiring a valid prior solution for these function tests; it
is not a restart/transfer test. Checks include quarter/full rotations, traverse,
constant radius, a shared moving center, signed/canceling moments, simple shear,
uniaxial extension, rigid rotation and preservation of physical parameters in
low-memory mode. Thermal-expansion reference tests still pass. Main, freshly
rendered dwell and ALE decks pass syntax checks.

The application was rebuilt against the existing local MOOSE/module libraries.
The general Makefile initially attempted to rebuild framework objects; that
build was stopped and the installed dependency archives were marked old for an
application-only build. This is not a clean rebuild/validation of all dependencies.
Tests use serial `UCX_TLS=self`; this setting is not intended for MPI campaigns.

## Thermal-equilibrium evidence

`test/verification/thermal_contact_equilibrium.i` is a small partially covered,
uniform-temperature two-body problem with no heat sources or environmental
losses. It must remain at 293.15 K.

| Configuration | Result |
| --- | --- |
| Corrected quadrature transfer | Minimum and maximum remain 293.15 K at the requested 0.001 s |
| Old nodal transfer override | Approximately 204–439 K after timestep cutback, despite no heat source |
| Existing dwell mesh, frictionless stationary contact, both heat sources disabled, old transfer | Maximum approximately 324.003 K after 25 microseconds |
| Same stationary diagnostic with quadrature transfer | Maximum and core temperature both 293.15 K |

The stationary dwell comparison used explicit diagnostic penalty 1e7 and
conductance 1e7, the historical literal-rotation mesh and tight nonlinear
tolerances. These are not calibrated process parameters. The small equilibrium
test is the permanent automated regression; the larger runs and logs are under
`/tmp/afsd-motion-work`. Uniform equilibrium preservation does not establish
conservation for nonuniform, evolving contact; that still needs separate tests.

## Continued implementation and executable evidence — 8 November

The user confirmed **prescribed feed at 75 mm/min** (0.00125 m/s). Axial force
is a response. Existing 4 s dwell and 50 mm traverse over 28 s remain assumptions.

- Solid contact now uses PJFNK/GMRES with LU preconditioning in low-memory mode;
  the slip damper is inactive and backtracking remains active. The initial step
  is 25 microseconds and the maximum is 250 microseconds (200 steps/revolution).
  The previous 0.05 s maximum was exactly one revolution and could alias rotation.
  The renderer rejects larger low-memory starting steps. Historical trial scripts
  requesting 1 s steps are unsupported, rather than silently accepted.
- The flow deck explicitly uses pivoting MUMPS LU and automatic scaling. The
  previous default preconditioner encountered a zero pivot. The rectangular
  prototype advanced three steps; this alone is not process validation.
- The flow material supplies `viscoplastic_heat = 2*beta*mu*D:D` and `grad_k`.
  Both the energy source and new `AFSDEnergySUPG` use the same AD heat property;
  SUPG now uses material-relative-to-mesh velocity. Taylor–Quinney conversion is
  configured on the material, not independently on the heat kernel. Analytical
  shear/extension/rigid-rotation tests check rate and heat, including zero heat
  under rigid rotation. A full energy budget remains unverified.
- `scripts/create_afsd_circular_flow_case.py` generates a conforming circular
  inlet and surrounding exposed material, with prescribed spin/traverse/feed,
  a fixed-height translating inlet mesh, and disjoint surface-motion node sets.
  Signed Gmsh boundary IDs are normalized before subtracting the inlet/base.
  This fixes accidental inclusion of the base in the exposed-surface group.
  The initial 723.15 K and divergence-free velocity seed are explicit assumed
  qualification conditions, **not a solved dwell handoff**.

### Accepted contact increment

`verification_runs/contact_pjfnk/contact.i`, `run.log`, `contact.csv` and Exodus
record a converged 25-microsecond increment with released tip and rotation.
This diagnostic explicitly overrides penalty and gap conductance to 1e7; these
are not calibrated values and were not substituted into production defaults.
It took about 61 s in this environment. Tmax was 293.155395 K, Tmin 293.148487 K,
axial force 0.583826 kN and signed torque 1.698565 Nm. The slight temperature
undershoot remains a numerical issue to assess. The 4 s dwell is not complete.

### Circular flow: converged, but rejected for volume conservation

`verification_runs/circular_flow_tags_fixed/` retains the generated mesh/input,
run log, CSV and Exodus. The solve reaches its requested 4.00001 s endpoint
from 4 s (one 10-microsecond step), taking about 11 s. It is an intentionally
short qualification run, not a completed deposition. The following diagnostics
are reproducible:

```bash
python3 test/verification/test_surface_flux.py
python3 scripts/analyze_afsd_surface_flux.py verification_runs/circular_flow_tags_fixed
python3 scripts/check_afsd_flow_balance.py verification_runs/circular_flow_tags_fixed --max-relative-feed-error .02
```

The last command **correctly exits 2 (failed screen)**. The explicit 2% threshold
is exploratory, not a validated universal tolerance. Results:

| Quantity | Result |
| --- | --- |
| Supplied volume | 5.93200425e-12 m³ |
| Excess mesh volume | 1.68208375e-12 m³ |
| Excess / supplied volume | **28.3561%** |
| Excess / initial domain volume | 2.25567e-7 |
| Net fluid surface flux / inlet flux | approximately 3.2e-15 |
| Free-surface relative flux / inlet flux | -0.283283 (artificial influx) |
| Polygonal inlet area error against ideal circle | -3.32336% |

The fluid inlet and outlet fluxes balance; the mesh boundary does not follow
material-normal motion consistently. At the inlet rim the mesh is fixed in Z
while material enters downward; adjacent free-face interpolation spreads this
mismatch over finite area. The integrated flux test localizes the error to the
free surface. A tighter nonlinear solve does not remove it. The measured area
is used in the volume budget, so circle discretization does not explain this
28% excess. Future mesh/time studies must still resolve both errors.

`analyze_afsd_surface_flux.py` independently integrates fluid and mesh velocities
over oriented exterior tetrahedron faces. Its analytical tests use the divergence
theorem, translation and internal-face cancellation. It supports the generated
serial TET4 qualification case only. End-step surface flux and finite-step volume
change differ slightly because the mesh geometry changes within the step.

## Remaining blockers, in implementation order

1. Replace the inlet-rim/free-surface kinematic treatment with a conservative
   formulation that respects boundary junctions. Enforce the normal material
   condition with compatible inlet geometry/interface treatment; use tangential
   mesh smoothing without adding material. Do not conceal this defect through a
   prescribed bead profile, relaxed volume tolerance or changed feed profile.
2. Demonstrate sustained, refined contact and flow transients, positive element
   Jacobians and temperature robustness. Unify the synthetic rectangular main
   rod with the cylindrical generated geometry.
3. Replace `mu*p*omega*r` heating with verified solved traction/slip work and
   complete actuator/contact/thermal energy budgets.
4. Transfer the actual dwell state to flow. Preserve material history, feed,
   energy and volume through conservative rezoning. The old stage renderer still
   shortens geometry externally instead of proving continuous feed conservation.
5. Add conservative rod-origin transport and demonstrate spreading and trailing
   rod-material flux. Complete deposition/cooling and independent experimental
   validation before claiming predictive mushroom geometry or backward transport.

No full process, validated bead shape, or completed predictive workflow is claimed.
