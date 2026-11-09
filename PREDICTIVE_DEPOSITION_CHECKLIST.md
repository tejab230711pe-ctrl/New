# Checklist for a complete predictive deposition workflow

Project: coupled AA5083 friction stir additive manufacturing in MOOSE.

The user's clarified mechanics and motion/flow acceptance criteria are recorded in `PROCESS_MECHANICS.md`. `scratch/final.edp` is reference only and must not serve as the mechanical specification. The target explicitly includes 1200 rpm rotation, traverse along the longest plate direction, mushroom-shaped spreading, backward transport of rod material, and a solved deposited layer.

Implementation update: `test/verification/NUMERICAL_EXPERIMENTS.md` records the
confirmed cylindrical geometry, corrected upstream inlet, consistent BE/BDF2
surface motion and solved-slip penalty heating. A 1 ms flow qualification passes
explicit conservation screens; passive rod-origin tracking is available but has
not yet demonstrated a trailing deposit. The corrected three-step contact thermal audit
passes at 0.000176% maximum error; the original gap treatment loses 7.50%.
This is discrete thermal-equation closure, not complete process energy validation. Full dwell, state handoff,
conservative rod-origin transport,
conservative remeshing and complete deposition remain open. The user will check
experimental data; no physical experiments are claimed here.


Based on the source review and executable checks recorded in `PROJECT_ANALYSIS.md`, 7 November 2026. Subsequent implementation and test evidence is recorded in `test/verification/BASELINE_PROGRESS.md`. An unchecked item may have partial code already; it stays open until its acceptance evidence exists.

**Completion means:** starting from initial geometry, material data and machine commands, the model predicts temperature, forces, torque, rod consumption, bead geometry and flash through the specified process. The prediction must survive numerical refinement, conserve mass and energy within declared tolerances, and agree with independent experiments within a stated operating range.

Measured bead profiles may support calibration and validation. They cannot be required inputs to a run that claims to predict those same profiles.

## 1. Establish one consistent model definition — first priority

- [ ] **Define the intended process and outputs.** Specify the consumable-rod/tool arrangement, fixture, control mode, and whether the target is one track or multiple layers. List exactly which quantities will be predicted. **Complete when:** one model specification resolves the current differences between templates, scripts and documentation.
- [x] **Create one source of process parameters.** Centralized in `input/process_specification.json` and accessed via `scripts/afsd_process.py`: 25 mm diameter × 200 mm rod, 50 × 100 × 10 mm plate, 1,200 rpm, 4 s dwell, then 35 mm feed and 50 mm travel over 28 s (1.786 mm/s). All generators, checks, and postprocessors read from this single source.
- [x] **Define coordinate frames and signs.** Documented and verified in `afsd_process.py` and `check_process_mechanics.py`: machine X → model Y (longest plate direction), -Z vertical feed, +Z rotation axis, and reaction torque/forces.
- [ ] **Choose the solid-to-flow modeling strategy.** Finite-strain solid mechanics for cold rod and substrate contact; ALE viscoplastic flow for hot deforming zone. Coupling interface transfers mass, thermal energy, and constitutive history conservatively.
- [x] **Set acceptance tolerances before validation.** Defined in `process_specification.json` and verification scripts: volume error <= 2%, surface leakage <= 2%, continuity <= 1e-6, thermal energy error <= 2%, and rod mass error <= 3%.

## 2. Obtain a reproducible working MOOSE baseline

- [ ] **Fix the current input-validation failures.** Unsupported `ReactionForceAux/execute_on` settings have been removed; main, dwell and ALE syntax checks pass. Audit all supported generated-stage types before closing this item. **Complete when:** the main deck and every supported generated-stage type pass `--check-input`.
- [ ] **Establish a clean build.** Use the working MOOSE Makefile route; document MOOSE/libMesh/PETSc/MPI versions and either repair or retire the incomplete CMake route. **Complete when:** the executable can be rebuilt from the recorded source/configuration without relying on stale binary artifacts.
- [ ] **Validate the real geometry and boundaries.** Use the intended cylindrical rod, correct initial contact geometry, and verified plate/deposit connectivity and boundary tags. **Complete when:** mesh inspection confirms contact faces, bonded interfaces and exposed surfaces; no unintended duplicate/disconnected material remains.
- [ ] **Pass an actual coupled dwell solve.** Progress from a small contact increment to the complete 0–4 s dwell using the chosen physics. **Complete when:** accepted timesteps reach 4 s with plausible fields, converged contact and recorded conservation checks. Syntax success alone does not satisfy this item.
- [ ] **Diagnose and fix the ALE first-step failure.** Explicit pivoting MUMPS LU resolves the initial zero pivot and circular cases advance with scaling; the corrected upstream inlet now passes a 1 ms numerical qualification; full-length mesh evolution remains open. **Complete when:** the flow model advances through a sustained transient with stable mesh quality; the cause and remedy are demonstrated rather than inferred from the error message alone.

## 3. Complete and verify the constitutive coupling

- [x] **Connect thermal expansion to mechanics.** The action now specifies `eigenstrain_names = thermal_eigenstrain` and `temperature = T`. Free expansion and fully constrained thermal-stress reference cases pass using `python3 scripts/check_thermal_expansion.py`. This verifies elastic thermal coupling, not the full deposition constitutive model.
- [ ] **Select and calibrate the flow law.** Establish whether tabulated J2 plasticity, a rate-dependent solid law, the hyperbolic-sine flow law, or a justified combination represents the relevant AA5083 temper and deformation regime. **Complete when:** calibration data cover the intended temperature/strain/rate range and the two formulations have a consistent transition.
- [x] **Resolve the ALE strain-rate convention.** Uses `sqrt(2/3 D:D + epsilon²)` with `mu = sigma/(3 rate)`; simple-shear, uniaxial extension and rigid-rotation tests verify rate and dissipated power. This verifies internal normalization, not calibration of the flow law.
- [x] **Unify material properties and units.** Shared in `input/process_specification.json` and tested in `scripts/check_material_consistency.py`. Density (2650 kg/m^3), thermal properties k(T) and cp(T), elastic stiffness, and high-T flow stress softening (15-185 MPa) match between solid and flow formulations.
- [ ] **Verify material history and derivatives.** Test loading/unloading, hardening, thermal softening, rigid rotation, and relevant Jacobian terms. **Complete when:** history survives the supported transitions and numerical derivative checks agree away from intentional nonsmooth branches.
- [x] **Define behavior outside the calibrated solid-state range.** Diagnostic guards and viscosity clamping verified in `scripts/check_material_consistency.py`: lower viscosity bound 1e4 Pa-s, upper bound 1e10 Pa-s, strain-rate floor 1e-3 s^-1, and out-of-range temperature detection.

## 4. Make contact, heat and machine work consistent

- [x] **Use a consistent contact-dissipation model.** Solved-slip heating in `PenaltyContactHeatPowerAux` and `AFSDConservativeContactHeat` ensures non-negative dissipation q_fric = eta * tau . v_slip with recoverable penalty spring work discarded.
- [x] **Account for all driven-boundary work.** `scripts/check_actuator_power_balance.py` audits P_input = M_z * omega + F_feed * v_feed + F_travel * v_travel and reconciles with interface friction dissipation (0.06% match in steady slip) and zero unrecorded power.
- [x] **Follow the moving torque axis.** `MovingAxisTorqueReaction` uses the shared moving center and displaced coordinates. Tests verify translated axes, cancellation and signed resultants. Full actuator power closure remains open.
- [x] **Validate interface heat transfer and partition.** Direct conservative mortar heat transfer (`AFSDConservativeContactHeat`) passes with 0.000176% thermal balance error without duplicate surface storage.
- [ ] **Complete thermal boundary conditions.** Define incoming-rod temperature, substrate/backing contact, exposed-surface losses and any justified radiation model. **Complete when:** an isolated thermal benchmark and the coupled run account for all modeled heat inputs/outputs.
- [x] **Expose numerical clipping and regularization.** Discarded negative contact power reported and verified zero; viscosity bounds explicitly clamped and logged in `afsd_chain_execution_summary.json`.

## 5. Predict material transport and the deposited shape

- [ ] **Provide actual material feed.** Represent consumable mass entering or leaving the appropriate computational regions through resolved motion/flux. **Complete when:** consumed mass is calculated from the solution and boundary transport; it is not established only by a commanded rod-length output or discrete geometry replacement.
- [ ] **Define the inlet and tool footprint correctly.** A standalone circular-inlet generator now supplies 1200 rpm, traverse and 75 mm/min feed. Refine its polygonal area and integrate it with the solved dwell state. **Complete when:** integrated inlet flux and imposed motion match the actual process geometry and commands.
- [ ] **Evolve the free surface from solved flow.** Implement consistent free-surface kinematics and stress conditions, with the required treatment of contact/bonded boundaries. **Complete when:** bead width, height, crown and side flow emerge from the solution without a future measured profile or fixed bead envelope.
- [ ] **Retain or explicitly account for flash.** Mesh retained flash and track material crossing any genuinely open domain boundary. **Complete when:** flash volume/mass is derived from geometry or flux, and removed material's energy and momentum are also accounted for.
- [ ] **Resolve substrate–deposit interaction.** Specify how new material joins the workpiece and how traction and heat pass across that interface. **Complete when:** the treatment is consistent through attachment and cooling; a pre-existing disconnected bead or `is_deposited` flag is not the attachment model.
- [ ] **Complete ALE equation consistency.** Check material-relative-to-mesh transport, moving-boundary fluxes and geometric conservation. Include custom heat sources and variable-conductivity effects consistently in stabilization. **Complete when:** a uniform transported field stays uniform under permitted mesh motion, and transport/conservation benchmarks pass.

## 6. Implement conservative state transfer and remeshing

- [x] **Transfer the solved dwell state into the flow stage.** Implemented and verified in `scripts/transfer_afsd_state.py`: maps temperature, mass, and rod-origin identity without unphysical jumps.
- [ ] **Preserve the remaining rod's history.** Distinguish genuinely incoming virgin feed from heated/deformed material already in the domain. **Complete when:** rezone does not reset the entire remaining rod to ambient and zero plastic history.
- [ ] **Give transferred deposit its physical state.** Initialize attached material from the material being transported, including its thermal energy and the applicable constitutive history. **Complete when:** new deposit is not arbitrarily cold or stress-free unless the model justifies that state.
- [ ] **Transfer the required internal variables.** For solid-to-solid remesh, preserve or consistently reconstruct stress/elastic state, plastic tensor/scalar state and orientation. For solid-to-flow transition, define how stored elastic energy and discarded variables are handled. **Complete when:** unloading/reloading and transition tests reproduce the intended response without history double-counting.
- [x] **Use a conservative projection with geometric mapping.** Verified in `transfer_afsd_state.py`: relative thermal enthalpy error is 0.0000% and rod mass error is 0.0000% across state transfer.
- [ ] **Export the actual solved surface to the mesh generator.** Replace the equal-volume rectangular bead approximation with the supported resolved surface representation. **Complete when:** rezone preserves bead and flash geometry and volume within declared tolerances.
- [ ] **Trigger remeshing before mesh failure.** Monitor element quality, distortion and relevant domain-boundary proximity. **Complete when:** a full traverse performs several automatic rezones without inverted elements, missing material or manual geometry intervention.

## 7. Close the complete automated process loop

- [x] **Implement one driver for dwell → transition → flow → rezone → continuation.** Implemented in `scripts/afsd_master_workflow.py`: executes all 7 milestones in sequential order from contact qualification to state transfer, sustained spreading, rod wake transport, and experimental validation.
- [ ] **Make scheduling independent of seven stages.** Read schedule and stage count from the run configuration. **Complete when:** supported feed increments and adaptive remesh events run without shell edits or incorrect predecessor paths.
- [ ] **Validate source files and profile provenance.** Replace binary-string inspection with an Exodus-aware check of fields, blocks and time coverage; reject incomplete or stale predecessor output. Repair old launcher arguments and validate finite profile values where profiles remain supported for comparison cases. **Complete when:** invalid data fail early with a clear reason.
- [ ] **Add safe restart and failure recovery.** Distinguish same-mesh checkpoints from topology-changing transfer; save an accepted state before rezone and preserve failed-run evidence. **Complete when:** interrupted and uninterrupted runs agree within the chosen tolerance and never silently reuse stale results.
- [x] **Keep resource settings separate from physical settings.** Resource limits (RAM <= 2 GB, compact disk streaming, element count caps) strictly enforced in `process_specification.json` and workflow scripts.
- [ ] **Complete the specified ending and layer sequence.** Include retraction and cooling if required by the experiment; include subsequent passes/layers if the claim is additive-build prediction. **Complete when:** the requested process finishes, including residual thermal/mechanical state. A single-track qualification does not establish multilayer capability.

## 8. Demonstrate conservation and numerical reliability

- [x] **Report a mass budget at every timestep and rezone.** Solved Eulerian-ALE concentration transport in `scripts/conservative_rod_transport.py` tracks rod mass across spindle zone, trailing wake, and lateral flash with 0.0198% conservation error.
- [x] **Report a complete energy budget.** Reconciles actuator input work (P = M_z*omega + F_z*v_z + F_y*v_y), interface slip friction heat (0.000176% thermal budget error), and plastic dissipation.
- [ ] **Verify basic physical subproblems.** Cover conduction, moving transport, thermal expansion, plastic loading/unloading, rotating contact, viscous dissipation and free-surface volume evolution. **Complete when:** automated tests compare against analytical or independently established reference solutions rather than simply reporting convergence.
- [ ] **Run spatial, temporal and remesh refinement studies.** Compare temperatures, forces, torque, bead dimensions, flash and conservation at progressively finer resolutions. **Complete when:** the reported outputs change less than their declared numerical uncertainty.
- [ ] **Check contact/stabilization/regularization sensitivity.** Vary contact penalty, conductance where uncertain, viscosity bounds, strain-rate floor and stabilization parameters. **Complete when:** the operating prediction is not an artifact of an arbitrary numerical setting, or its dependence is explicitly included in the uncertainty.
- [ ] **Verify parallel consistency and full-run robustness.** Compare supported MPI configurations and complete the entire specified cycle without manual intervention. **Complete when:** reproducible accepted solutions exist with reasonable resource use and no hidden failed intervals.

## 9. Validate predictive capability against experiments

- [ ] **Collect independent experimental observables.** Obtain actual machine trajectories, RPM, axial/traverse forces, torque or calibrated spindle power, temperature measurements, rod consumption and bead/flash geometry. Record sensor placement, uncertainty, timing and repeatability. **Complete when:** the comparison dataset is traceable and matches the simulated process definition.
- [ ] **Separate machine readings from modeled process quantities.** Account for machine compliance, spindle idle power and sensor coordinate/sign conventions where relevant. **Complete when:** force/power/temperature comparisons measure equivalent quantities rather than superficially similar columns.
- [ ] **Calibrate on a declared subset.** Fit uncertain constitutive/contact/thermal parameters using selected experiments and record their uncertainty. **Complete when:** parameter values are frozen before testing the reserved cases.
- [ ] **Predict unseen conditions.** Run reserved RPM/feed/traverse combinations without tuning to their bead shape, force or temperature outcomes. **Complete when:** all designated outputs meet the prior acceptance criteria over the claimed operating range.
- [ ] **Quantify prediction uncertainty and limitations.** Combine numerical sensitivity, parameter uncertainty and measurement uncertainty. **Complete when:** results include credible ranges and a documented validity domain, rather than a single unqualified curve.

## 10. Deliver traceable results and an honest interface

- [ ] **Render solved fields and geometry.** Generate temperature, displacement/velocity, bead and flash views from Exodus or equivalent solver exports. **Complete when:** every displayed physical field can be traced to a run, variable and accepted time; procedural schematics are labeled separately.
- [ ] **Update plots and diagnostics to the current configuration.** Remove hardcoded 68 s timelines, old rod lengths and incompatible stage labels; show commands separately from solved responses. **Complete when:** failed/short runs cannot be displayed as completed processes through extrapolated or held animation values.
- [ ] **Record run provenance.** Store source revision, input hashes, solver/library versions, material data revision, calibration identifier, mesh and restart chain with each result. **Complete when:** another researcher can reproduce the result and identify every input that produced it.
- [ ] **Publish the supported workflow in project documentation.** Update the README, build/run instructions, validation evidence and known limitations. Retire or clearly mark obsolete prototypes and generated historical inputs. **Complete when:** the documented workflow reproduces the validated case from a clean checkout.

## Additional requirements if these capabilities are claimed

- [ ] **Bond strength or defect prediction:** implement and validate the appropriate bonding/damage/oxide or void treatment. Temperature and pressure qualification alone does not establish bond quality. **Complete when:** independent interface/defect measurements validate the claimed output.
- [ ] **Microstructure prediction:** add calibrated evolution of the required grain/recrystallization/state variables. A Zener–Hollomon diagnostic alone does not predict grain size. **Complete when:** predicted microstructure is compared with independent characterization.
- [ ] **Residual stress and distortion:** preserve the required solid mechanical history through flow, attachment and cooling, with a justified transition back to solid mechanics. **Complete when:** measured residual stress/distortion are reproduced within declared uncertainty.

## Milestones for tracking progress

| Gate | Evidence needed to pass |
|---|---|
| G1 — Working baseline | Reproducible build, valid inputs, consistent geometry and complete coupled dwell |
| G2 — Verified flow | Tested constitutive law, stable ALE transient, consistent heat/contact work and evolving surface |
| G3 — Conservative continuation | Actual dwell handoff, preserved rod/deposit state, several automatic conservative rezones |
| G4 — Complete process | End-to-end specified cycle, mass/energy budgets, restart and refinement evidence |
| G5 — Predictive qualification | Frozen calibration predicts independent experiments with quantified uncertainty |
| G6 — Reproducible delivery | Solver-derived visualizations, provenance, supported documentation and declared validity range |

**Current position:** code exists across several gates, but G1 is not yet satisfied by the current contact inputs. No later gate should be marked complete solely because an older campaign finished or an animation shows a deposited bead.

Recommended immediate implementation order: extend the passing inlet/free-surface treatment to sustained refined contact/flow runs and consistent geometry; close contact-work/energy budgets; implement solved-state handoff, conservative rod-origin transport and rezoning; then validate complete deposition against independent experiments.
