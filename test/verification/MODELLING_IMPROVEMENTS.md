# Modelling improvements — 7 November 2026

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
  motion. This is required for a deforming tip, but the resulting coupled solve
  still needs convergence work.
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
  selects direct Newton solves, backtracking, smaller timesteps and reduced
  Exodus output. The template nonlinear tolerances are now 1e-7 relative and
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

## Remaining blockers

The old driven-tip penalty case advanced three 25-microsecond steps, but its
spurious thermal rise invalidates it as physical evidence. With the corrected
thermal transfer and released tip, the rotating Coulomb-contact diagnostic still
fails to establish a sustained transient. Active contact/stick/slip changes and
initial interference need further investigation; smaller timesteps alone are
not a demonstrated remedy. No complete dwell or deposition run is claimed.

The heat boundary condition still uses `mu*p*omega*r`, so it does not correctly
represent general local sticking, tip deformation or relative sliding. Replace
it with verified contact-work/slip heating and close the mechanical/thermal
energy budget before interpreting temperature predictions.

The flow prototype still needs a circular rod footprint, a validated solid-to-flow
handoff, continuous feed, conservative rod-origin transport, solved bead/flash
surfaces and conservative remeshing. The current main mesh remains a synthetic
rectangular-rod template; generated stages use cylinders. Geometry must be unified
before quantitative process validation. These improvements do not yet predict
the mushroom shape or backward transport requested by the user.
