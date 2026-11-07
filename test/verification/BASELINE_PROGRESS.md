# Baseline verification — 7 November 2026

## Implemented

In `input/deposition.i`, the finite-strain mechanics action now explicitly uses
`thermal_eigenstrain` and couples temperature `T`. The three `ReactionForceAux`
objects no longer set the private `execute_on` parameter. The installed MOOSE
`TagAuxBase` already fixes execution to `TIMESTEP_END`. Their block restrictions
now match the displacement variables (`plate rod`); without this restriction,
the standalone template attempts to read displacements on its nonmechanical bead.
The stage renderer expands those restrictions with the other mechanical blocks.

## Passed checks

- Main input: `UCX_TLS=self ./rotating_disk_deposition-opt -i input/deposition.i --check-input` reports `Syntax OK`.
- Newly rendered low-memory dwell input from the literal-rotation manifest reports `Syntax OK`.
- `python3 scripts/check_thermal_expansion.py` passes both reference solves.
- `git diff --check` passes.

The thermal test uses an eight-element, 10 mm cube, E = 70.3 GPa,
Poisson ratio = 0.33, thermal expansion coefficient = 2.38e-5 /K and a 0.01 K
uniform temperature rise. Symmetry constraints remove rigid-body modes in the
free case. Opposite faces constrain each corresponding displacement component
in the fully constrained case. Both use finite strain and Hughes–Winget decomposition,
as in the main input. The small temperature rise permits comparison with the
linear analytical limit at relative tolerance 1e-5.

| Case | Analytical reference | Computed result |
| --- | --- | --- |
| Free expansion, each positive face | alpha × deltaT × L = 2.38e-9 m | 2.3800002832415e-9 m |
| Free expansion, normal stress | 0 Pa | absolute value below 9e-12 Pa |
| Fully constrained, displacement | 0 m | 0 m |
| Fully constrained, each normal stress | -E × alpha × deltaT / (1 - 2 nu) = -49,210 Pa | -49,210.000000445 Pa |

The script checks all three displacement and normal-stress components, finite
values through numerical comparisons, process success and final time. It creates
outputs in a temporary directory. These tests verify elastic thermal coupling;
they do not validate temperature-dependent plasticity, contact or deposition.
The current executable was used; a clean source rebuild remains outstanding.

## Coupled dwell remains failing

A newly rendered input used the existing literal-rotation dwell mesh, the current
source template, and the renderer's existing low-memory settings (penalty and
gap conductance both 1e7, time increment 25 microseconds). This is a diagnostic
configuration, not a calibrated baseline. Only one step was requested.

After all input fixes, the default LU run still fails before accepting its first
step: `FACTOR_NUMERIC_ZEROPIVOT`, followed by `Unable to find closest node!`.
There are no missing-temperature-coupling warnings in that final run.

An intermediate diagnostic run using MUMPS, before adding the explicit action
`temperature` parameter, advanced into Newton iterations but encountered negative
element Jacobians and exhausted timestep cutbacks. This does not establish the
root cause of the final configuration's failure or justify changing the default
solver. No contact solver change has been committed.

Generated inputs, logs and diagnostic output are isolated under
`/tmp/afsd-baseline-verification`; historical campaign outputs were not overwritten.
The mesh and old manifest used here are existing artifacts, not a newly verified
predictive geometry pipeline. Later feed/transfer stages have not been reverified.

To reproduce the dwell deck without writing into an old campaign, run from the
repository root:

```python
import json
import sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from render_afsd_remesh_stage import render
out = Path('/tmp/afsd-baseline-verification')
out.mkdir(exist_ok=True)
manifest = json.loads(Path(
    'remesh_stages/feed_5mm_literal_rotation/feed_5mm/manifest.json').read_text())
stage = manifest['dwell'].copy()
stage['output_exodus'] = str(out / 'dwell.e')
render(Path('input/deposition.i').resolve(), stage, out / 'dwell.i', True, 0.000025)
```

```bash
UCX_TLS=self OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 timeout 60 \
  ./rotating_disk_deposition-opt -i /tmp/afsd-baseline-verification/dwell.i \
  Executioner/num_steps=1 Executioner/end_time=0.000025
```

`UCX_TLS=self` is for these serial checks on a host where MPI socket initialization
is restricted. It is not a setting for a multi-rank campaign.

## Next acceptance work

1. Isolate the dwell Jacobian failure with block/row diagnostics and controlled
   contact, heating and motion subcases; verify mesh connectivity and constraints.
2. Demonstrate stable first contact and rotation with physically justified initial
   contact loading, then perform step/mesh/penalty sensitivity checks.
3. Reverify feed stages and state transfer using accepted predecessor results.
4. Complete the full 4 s dwell with conservation checks before marking G1 complete.

The thermal-expansion checklist item is complete. The broader input-validation
item and G1 remain open.
