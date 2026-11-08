# Intended deposition mechanics

User clarification, 7 November 2026. This specification governs further model
work. `scratch/final.edp` is reference material only: it is not a complete
mechanical specification or a correctness baseline for the MOOSE implementation.

## Process and coordinates

A consumable rod rotates at 1200 rpm, contacts the initially solid base plate,
and heats/deforms the contact region. Continued axial feed and traverse along
the plate's longest direction must produce a deposited track. Material must be
able to spread radially under the rod and move into the trailing region, giving
the mushroom-shaped deformation and backward material transport described by
the user. Shape, height, width and transported volume must emerge from the solve.

Use model Y for the longest plate direction, X across the track, and Z upward.
Positive traverse is +Y and axial feed is -Z. The existing clockwise/counterclockwise
choice has not been experimentally specified; current expressions use positive
rotation about +Z. At 1200 rpm, angular velocity is 40*pi rad/s and the period is
0.05 s. For a translating axis c(t), prescribed spindle velocities are
vx = -omega*(y-c_y), vy = omega*(x-c_x)+V_traverse, vz = -V_feed.
These are spindle/inlet conditions, not constraints on every point in the
plasticized material. Interfacial slip and material velocity must be solved.

The user confirmed prescribed axial feed at 75 mm/min on 8 November 2026;
axial force is an output, not a prescribed control target. Current timing (4 s
dwell, 28 s deposition) and 50 mm traverse remain existing code assumptions.
Plate and rod dimensions differ between the main template and generated stages;
a single physical geometry still needs to be established.

## Thermal interpretation

The active code treats hot deformation as solid-state plastic/viscoplastic flow.
Its ALE material uses 623.15 K (350 C) and 798.15 K (525 C) as diagnostic
plasticization thresholds, and the solid hardening table extends to 850 K.
These parameters are not evidence of actual melting. The diagnostic
`plastic_fraction` is neither a liquid fraction nor a solid-to-flow coupling law.
No active latent-heat/solid-liquid phase-change model establishes melting.
Until evidence requires a melt model, interpret the user's description of
material trying to melt as frictional heating and strong softening; do not claim
that liquid deposition is already implemented. If actual melting is intended,
solidus/liquidus, latent heat, liquid behavior and phase transition must be specified.

## Present implementation versus required behavior

| Requirement | Current evidence | Remaining work |
| --- | --- | --- |
| 1200 rpm rod rotation | Trigonometric displacement BCs exist; generated stages use a local axis | Top-only spindle BCs and a 25-microsecond free-tip increment pass; sustained rotation remains unverified |
| Traverse along longest plate direction | Generated stages add +Y translation to rotation | Moving axis, heat-source center, torque origin and spin Uy translation corrected and analytically tested; full travel solve remains open |
| Continuous rod feed and consumption | Template prescribes top feed; renderer instead holds local Z fixed and shortens stage geometry externally | Resolve material influx/consumption continuously with a mass budget, rather than equating geometry replacement with solved transport |
| Contact heating and softening | Solid contact, friction heat and temperature-dependent plasticity are present | Verify pressure, slip, dissipation, heat partition and transition to large material flow |
| Mushroom-shaped spreading | Separate ALE prototype moves free sides | Circular qualification mesh now exists; its free-surface volume error is 28.36% of feed and must be corrected |
| Backward material transport | No accepted coupled flow solution demonstrates it | Resolve velocity, pressure and thermal advection, and trace rod material into the wake |
| Deposited track | Generator imports profiles and creates rectangular bead volumes | Generate bead/flash geometry from the solved free surface and carry state conservatively through rezoning |

A free-tip rotating-contact increment now converges with PJFNK; the complete
dwell remains unverified. The separate circular ALE qualification solve advances
but fails its volume screen. Neither establishes the complete solid-contact-to-
deposition handoff. See `test/verification/MODELLING_IMPROVEMENTS.md` for evidence.

## Acceptance checks for backward flow and layer formation

- Verify spindle angular speed from solved boundary positions/velocities and the
  moving center, and verify that its path follows the longest plate direction.
- Report material velocity in both laboratory and translating-rod frames:
  v_relative = v_material - V_traverse*e_y. Negative relative Y velocity alone
  does not prove transported rod material: a stationary substrate also has that
  velocity in the moving frame.
- Advect a conservative rod-origin marker or material tracers. Demonstrate that
  entering rod material spreads beneath the contact and reaches the trailing
  deposited track; show trajectories and marker-weighted mass fluxes.
- Extract transverse and longitudinal free-surface sections around the rod.
  Measure radial spread, trailing height/width, and retained side flash from
  the solution. Do not prescribe a mushroom profile to demonstrate prediction.
- Balance supplied rod mass against remaining rod, bead, flash and any outflow.
  Track thermal storage, mechanical work, dissipation and heat losses separately.
- Demonstrate sustained rotation/traverse, positive element Jacobians, conservative
  remeshing and mesh/time refinement before interpreting the morphology physically.

## Implementation sequence

1. Resolve contact-baseline convergence and unify process geometry and moving-axis
   definitions across generated inputs.
2. Verify hot-flow constitutive conventions and replace the rectangular ALE inlet
   with the physical circular rod footprint and surrounding material free surface.
3. Couple thermal/mechanical contact to the flow region, preserving incoming
   temperature, material history and mass; do not initialize the entire flow region
   hot as a substitute for the contact-heating calculation.
4. Implement continuous feed, solved surface evolution, rod-origin transport and
   conservative rezoning; connect these to a single process driver.
5. Validate the resulting mushroom spread, backward transport and deposited track
   against measured shape, forces/torque and temperature histories.
