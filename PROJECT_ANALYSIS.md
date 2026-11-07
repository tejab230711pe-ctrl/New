# Coupled friction stir additive manufacturing: source and MOOSE analysis

Reviewed on 7 November 2026. Project revision: `38e4692`. Local MOOSE revision: `72570b9a2f`.

Scope clarification after this review: the user identifies `scratch/final.edp` as incomplete reference material only. Comparisons to it below are historical observations, not requirements or correctness criteria. `PROCESS_MECHANICS.md` records the intended mechanics; `test/verification/BASELINE_PROGRESS.md` records subsequent implementation changes.

This project is an evolving AA5083 friction-deposition research application. It contains a substantial coupled solid-contact implementation, an external geometry/state-transfer workflow, and a separate experimental ALE viscoplastic-flow model. It does **not yet demonstrate a working, conservative, end-to-end prediction of rod consumption, deposited geometry, and retained flash**.

The analysis follows the implementation rather than accepting the README's feature claims. Authored C++ sources and headers, input decks, Python and shell scripts, scratch examples, and the 2,403-line FreeFEM predecessor were examined. Generated campaign inputs were compared structurally; manifests and CSV histories were inspected. Large log files were sampled at their ends, with the ALE log read in full. Binary libraries, every mesh element, and every line of the multi-gigabyte logs were not individually audited. This is a source review with limited executable checks, not experimental validation or a completed new simulation campaign.

Only analysis documents were added; the model implementation was not repaired during this review.

## 1. What is actually in the project

| Layer | Main files | Actual role |
|---|---|---|
| MOOSE application | `src/main.C`, `src/RotatingDiskDepositionApp.*`, `Makefile` | Starts MOOSE, registers project objects, links physics modules |
| Solid-contact formulation | `input/deposition.i` | Temperature and finite-strain displacement solve, J2 plasticity, Coulomb contact, contact conduction, friction and plastic heat |
| Remesh workflow | `scripts/create_afsd_remesh_stages.py`, `scripts/render_afsd_remesh_stage.py` | Creates geometry from supplied profiles and constructs sequential MOOSE decks with selected state interpolation |
| ALE formulation | `input/afsd_ale_flow_stage.i`, `src/AA5083ALEViscoplasticMaterial.*`, `src/ALEViscoplasticDissipationHeat.*` | Coupled incompressible viscoplastic flow, energy transport, and mesh displacement prototype |
| Older C++ prototype | `AA5083ThermalProperties`, `MushyFraction`, `FrictionHeatSource`, `NormalServo` | Early migration helpers; most do not drive the current contact deck |
| FreeFEM predecessor | `scratch/final.edp` | Explicit sequential process controller, contact iteration, rod/plate flow and thermal solves, height/transport/ALE updates |
| Experimental decks | `scratch/*.i`, `test/test_finite_strain.i` | Mesh, boundary, mechanics, and coupling experiments; not a comprehensive regression suite |
| Presentation tooling | `scripts/process_schematic.py`, `scripts/simulation_renderer.py`, `scripts/generate_simulation_videos.py` | Procedural illustrations and CSV-driven telemetry animations |
| Scalar result plotting | `scripts/visualize_results.py`, `scripts/watch_afsd_campaign.py` | Plots and monitors CSV histories, with some outdated assumptions |
| Historical artifacts | `remesh_stages/`, `*.log`, plots, summary text | Results from different model generations; not interchangeable with the current source |

`input/edm_2d_ti6al4v.in` is an unrelated LAMMPS-style electrical-discharge-machining input. It is not part of this MOOSE application.

## 2. How MOOSE is used

The application does not implement a finite-element solver from scratch. MOOSE supplies mesh/variable management, quadrature, assembly, nonlinear and linear solver integration, contact actions, material state storage, parallel execution, and outputs. The project chooses framework objects in input files and adds a small number of process-specific C++ objects.

The startup path is:

```text
main.C
  -> Moose::main<RotatingDiskDepositionApp>()
  -> application validParams / constructor
  -> Registry::registerObjectsTo(project label)
  -> ModulesApp registration + NavierStokesApp registration
  -> parse .i file and execute Actions
  -> create mesh, variables, materials, kernels, BCs and postprocessors
  -> transient nonlinear solves through PETSc/libMesh
  -> CSV and Exodus outputs
```

The project Makefile enables `CONTACT`, `HEAT_TRANSFER`, `NAVIER_STOKES`, and `SOLID_MECHANICS`, and includes MOOSE's `build.mk`, `moose.mk`, `modules.mk`, and `app.mk`. Defaults point to `/home/teja/projects/moose` and `/home/teja/miniforge3/envs/moose`. The executable present here is `rotating_disk_deposition-opt`.

The CMake file is an old, incomplete alternative: it names `TensorMechanics`, omits `main.C`, and omits several essential newer source files. It should not be treated as the authoritative build recipe. No clean rebuild was performed during this analysis.

| MOOSE concept | Meaning in this project |
|---|---|
| `validParams()` | Declares required/optional input parameters and inherits framework parameters |
| `registerMooseObject(...)` | Makes a C++ class selectable through `type = ClassName` |
| Constructor | Retrieves coupled fields, functions and material properties; saves references |
| `Material` | Computes constitutive/thermal properties at quadrature points |
| `Kernel` | Adds a volume weak-form residual to an equation |
| `IntegratedBC` | Adds a surface weak-form residual, appropriate for W/m² interface heating |
| `AuxKernel` | Computes a diagnostic or derived field; it does not automatically add a conservation equation |
| `UserObject` | Supplies reusable services/data, including reading predecessor solutions |
| `InitialCondition` | Initializes fields on the next mesh |
| Physics/Contact Actions | Generate multiple lower-level objects from compact input syntax |
| `Executioner` | Controls transient solution, nonlinear solver and timestep policy |
| `Postprocessor` | Computes scalar integrals, extrema, reactions or derived quantities |

In a custom residual, `_qp` selects the integration point; `_i` selects the test function and `_j` the trial function. MOOSE supplies the integration weights and assembles element contributions globally. A heating source normally enters a residual written as storage plus diffusion minus source with a negative sign.

`ADReal` carries automatic derivatives through supported operations. The ALE material and heat kernel exploit this. The contact heat BC and solid plastic heat kernel use ordinary `Real`, so relevant Jacobian terms must be supplied manually or are absent. Merely setting `SMP/full = true` does not invent missing derivatives.

## 3. Process definition and geometry

The current generator specifies:

| Quantity | Value |
|---|---:|
| Rod diameter | 25 mm |
| Initial rod length | 200 mm |
| Plate | 50 × 100 × 10 mm |
| Spindle speed | 1,200 rpm = 125.663706 rad/s |
| Dwell | 0–4 s |
| Axial consumption | 35 mm at 75 mm/min = 1.25 mm/s |
| Traverse | 50 mm in the same 28 s = 1.785714 mm/s |
| End time | 32 s |
| Final commanded rod length | 165 mm |
| Machine/model axis mapping | Machine X becomes simulation Y |

The nominal total consumed volume is π(12.5 mm)²(35 mm), approximately 17,180.6 mm³. The generator validates `V_feed = V_bead + V_flash` within `max(1 mm³, 2% of V_feed)` using supplied cumulative profile volumes.

However, the unrendered `input/deposition.i` defines a different geometry: a 120 × 300 × 20 mm plate, a **square** 25 × 25 × 50 mm rod, a rod base 5 mm above the plate, and a pre-existing 25 × 200 × 3 mm bead. Combining bodies does not itself bond their coincident surfaces. The bead is excluded from the main displacement variables and solid-mechanics blocks in this template. Its thermal presence is not material birth.

The stage renderer replaces this mesh with the generated cylindrical rod and conformal plate/deposit geometry. Therefore the template, a rendered stage deck, and historical campaign inputs are different simulation configurations.

## 4. Solid-contact model: equations and input walkthrough

The principal unknowns are `T`, `Ux`, `Uy`, and `Uz`. Contact pressure is supplied through MOOSE's contact machinery, rather than solved as an independently specified bulk pressure variable.

The intended mechanics are quasi-static equilibrium with finite-strain increments and isotropic J2 plasticity:

```text
div(sigma) = 0
sigma_equivalent <= sigma_y(T, equivalent_plastic_strain)
```

The input supplies six true-stress/plastic-strain curves at 293.15, 450, 623.15, 723.15, 798.15 and 850 K. The room-temperature initial yield value is 255.21 MPa; at 798.15 K it is 28 MPa. The selected MOOSE model interpolates these curves and performs a radial return. There is no Johnson–Cook strain-rate term in this active solid material. Temperature-dependent plasticity is not, by itself, a rate-dependent viscoplastic constitutive law.

The thermal terms correspond to conduction/storage with bulk plastic work and interface friction:

```text
rho cp dT/dt = div(k grad(T)) + q_plastic
q_plastic = 0.90 max(0, sigma : Delta(eps_plastic) / dt)
q_friction_surface = partition * efficiency * mu_contact * max(p_contact,0) * omega * radius
```

The surface and volume sources have different units and integration domains. The main deck uses solid-state heat capacity without latent heat. The `mushy_fraction` auxiliary variable is a temperature indicator, not a liquid fraction feeding a phase-change equation.

| Lines of `input/deposition.i` | Interpretation |
|---|---|
| 1–42 | Intended equations and comments; several claims exceed the actual implementation |
| 44–127 | Three generated meshes, block labels, combination and boundary splitting |
| 129–213 | CNC commands, rotation functions, and six hardening curves |
| 215–241 | Temperature everywhere; displacements on plate and rod |
| 243–248 | Creates property helper UserObject, although current heat BC does not consume it |
| 250–270 | Mechanical residual reaction tag and finite-strain solid-mechanics action |
| 272–336 | Diagnostic auxiliary fields, including command traces and deposition indicator |
| 338–361 | Thermal storage, conduction, nonnegative plastic heating |
| 363–477 | RPM, temperature indicator, friction flux diagnostic, reactions, qualification, command diagnostics |
| 479–564 | Parsed thermal properties, thermal eigenstrain, elasticity, plastic update, stress update and plastic-work material |
| 567–582 | Node/face Coulomb contact with tangential penalty and constant friction coefficient 0.35 |
| 587–595 | Contact-slip damper for nonlinear iteration stability |
| 599–608 | Gap heat transfer between rod and plate |
| 610–703 | Plate clamp, driven rod top and bottom tangential motion, cooling and friction heat |
| 705–876 | Temperatures, stresses, strains, forces, torque, power and command/qualification outputs |
| 878–914 | Coupled preconditioning, transient PJFNK solve and adaptive timestep |
| 916–937 | Console, Exodus and CSV outputs |

The contact formulation is not the mortar model described in the README. The coefficient is constant, not the legacy `mu(T)` helper. The documented shear-yield cap `min(mu p, sigma_y/sqrt(3))` is not implemented by the custom heat flux.

The temperature-to-mechanics loop contains temperature-dependent hardening. The mechanics-to-temperature loop contains pressure-derived friction heating and plastic work. Thermal expansion is declared but currently disconnected: neither `eigenstrain_names = thermal_eigenstrain` nor `automatic_eigenstrain_names = true` is set on the mechanics action. The installed action defaults automatic collection to false. This was checked against local framework source, not assumed from an older MOOSE API.

## 5. Every custom C++ class

### Application and entry point

`main.C:1–9` delegates application startup to MOOSE. `RotatingDiskDepositionApp.h:1–14` declares the application and registration methods. `RotatingDiskDepositionApp.C:8–16` selects framework compatibility/scaling settings; lines 18–37 construct the app and register project/module objects. Registration makes classes available; it does not activate their physics until an input instantiates them.

### AA5083ThermalProperties

`AA5083ThermalProperties.C:7–35` constructs a `GeneralUserObject` and initializes seven temperature points and thermal property arrays. Lines 39–71 implement constant lower extrapolation, linear internal interpolation, and unbounded last-slope upper extrapolation. Lines 73–82 expose thermal/yield getters; lines 85–101 calculate clamped temperature-dependent friction, from 0.70 toward 0.25. The header's initialize/execute/finalize methods are intentionally empty because this is a lookup service.

The yield array contains **11 values against only seven temperature points**. Inside the interpolation interval only the corresponding first seven entries are sampled; the upper-end branch instead uses the final two values. This is not a valid reproduction of the FreeFEM yield curve and creates a discontinuity at the final thermal breakpoint. `_Tliq` is declared but not used to cap extrapolation. `_mu_vals` is also unused. The main contact deck instead defines its actual thermal coefficients using `ParsedMaterial`, and its plastic curves independently.

### MushyFraction

`MushyFraction.C:8–20` declares parameters. Lines 22–39 bind the temperature/property service and declare four material properties. Lines 42–79 loop over quadrature points, calculate a piecewise-linear fraction and derivative, then set `cp_eff = cp + Lf df/dT` and `k_eff = (1-f) k + f k_liquid`.

Its thresholds are 615.75 and 787.05 K because it uses `273.15 + factor*(Tsol - 293.15)`. This differs both from the current 623.15–798.15 K diagnostic interval and the FreeFEM expression using `Tsol - 273.15`. This object is not instantiated in the current contact or ALE deck. Its latent-heat regularization must not be presented as current solid-state AFSD physics.

### FrictionHeatSource

`FrictionHeatSource.C:8–27` declares and binds temperature, pressure, material service, radius, RPM and governor. Lines 31–53 compute uniform-pressure disk torque, multiply by angular velocity, then return a volume-kernel residual.

The computed quantity is **total power in watts**, but the kernel treats it as a local volumetric source without a volume normalization. The positive residual sign also opposes a positive source in the usual heat-equation convention. It has no manually implemented coupled Jacobians. It is a legacy object; the current contact deck uses `ContactFrictionHeatFlux` instead.

### NormalServo

`NormalServo.C:7–26` stores a coupled displacement and constant input parameters. Lines 29–49 calculate a ramp from `_current_time`, multiply stiffness by preload force, and return a negative volume residual.

It is not an actual feedback servo: `_disp` is unused, `_current_time` is a constant parameter defaulting to zero rather than MOOSE's evolving `_t`, and stiffness in Pa/m multiplied by force in N does not produce a volumetric force in N/m³. Integration does not implicitly divide by volume as the comment claims. This object is not active in the current contact deck.

### ContactFrictionHeatFlux

`ContactFrictionHeatFlux.C:7–19` declares its interface; lines 21–31 bind contact pressure, angular velocity, coefficient, partition, efficiency and center function. Lines 34–42 compute radial distance and return `-test*q` as a surface residual. This is dimensionally appropriate for a heat flux in W/m².

However, it uses commanded `omega*r`, not the solved relative tangential slip velocity or solved tangential traction. Matching the Coulomb coefficient does **not** make this exactly equal to mechanical dissipation during sticking, partial slip, substrate motion or traverse. The header's exact-dissipation claim is too strong. It also has no explicit pressure/displacement Jacobian implementation.

### NonnegativePlasticHeatEnergy

`NonnegativePlasticHeatEnergy.C:11–38` declares coupling, handles optional material-name prefixes, retrieves plastic-work properties and validates one displacement per mesh dimension. Lines 43–46 apply the clamped heating source. Lines 49–65 supply displacement derivatives only on the positive-work branch.

This prevents a negative plastic-work contribution from cooling the material. It does not repair an inconsistent remesh state, establish energy conservation, or include all temperature sensitivities of plastic work. Clipping should be accompanied by a diagnostic recording how much negative work was suppressed.

### RemeshSolutionIC

`RemeshSolutionIC.C:9–28` extends `SolutionIC` with inherited-block selection and an outside value. Lines 31–37 resolve target block IDs. Lines 40–50 inspect the current element and either sample the predecessor solution or return the virgin-state default.

This handles newly introduced material outside the old mesh. Shared continuous nodes can still receive competing inherited/virgin contributions during projection. It is interpolation/projection, not a conservative enthalpy or mass transfer algorithm. It does not supply a material-coordinate map between deformed and rezoned configurations.

### RemeshTemperatureDependentHardeningStressUpdate

`RemeshTemperatureDependentHardeningStressUpdate.C:10–21` adds optional source functions to MOOSE's J2 material. Lines 24–43 bind a scalar and optionally six tensor components. Lines 46–78 initialize inherited state, clamp effective plastic strain nonnegative, reconstruct a symmetric tensor in xx/yy/zz/xy/yz/zx order, and rebuild hardening.

It transfers part of the constitutive history. It does **not** transfer elastic strain, stress, deformation gradient, contact state or stored elastic energy. The hardening rebuild calls a base method that adds old effective strain to its argument; initialization must be regression-tested to establish correct old/current state behavior and no double-counting. No such test exists here. Tensor interpolation also needs checks of trace, invariants and orientation after rezone.

### AA5083ALEViscoplasticMaterial

`AA5083ALEViscoplasticMaterial.C:10–29` defines the constitutive constants. Lines 32–55 bind AD temperature/velocity gradient, declare `rho`, `cp`, `k`, `mu`, `plastic_fraction`, `effective_strain_rate`, and validate selected parameters. Lines 58–95 compute them.

The actual formulas are:

```text
D = (grad(v) + grad(v)^T)/2
rate = sqrt(2 D:D + rate_regularization^2)
logZ = log(rate) + Q/(R T)
sigma_formula = asinh(exp((logZ - logA)/n))/alpha
mu = clamp(sigma_formula/(3 rate), mu_min, mu_max)
rho = 2650
cp = 900 + 0.45(T - 293.15)
k = 122 + 0.08(T - 293.15)
```

Constants are Q = 174,700 J/mol, n = 5.23, logA = 24.98, alpha = 0.015 MPa⁻¹ = 1.5e-8 Pa⁻¹, rate regularization = 1e-3 s⁻¹, and viscosity bounds 1e4–1e10 Pa·s. `plastic_fraction` is a clamped smoothstep over 623.15–798.15 K; it does not gate the constitutive law or create material.

The strain-rate convention needs correction or explicit calibration justification. For incompressible J2 flow, equivalent strain rate is `sqrt((2/3) D:D)`, whereas the implemented rate is `sqrt(2 D:D)`. Pairing the latter with `mu = sigma/(3 rate)` gives a von Mises stress of `sigma_formula/sqrt(3)` in the unregularized limit. A simple-shear/uniaxial material test should establish the intended convention before fitting data.

The thermal coefficients differ from the solid-contact model. No temperature-positivity check protects Q/(RT), and several constitutive constants have no range checks. Hard viscosity clamps remove derivatives outside bounds; this is a deliberate regularization with consequences for Newton convergence.

### ALEViscoplasticDissipationHeat

`ALEViscoplasticDissipationHeat.C:6–21` binds AD velocity gradient, viscosity and Taylor–Quinney coefficient. Lines 24–29 return `-test * 2 * beta * mu * D:D`. This gives a nonnegative bulk source for positive viscosity and beta. AD propagates temperature and velocity sensitivities through viscosity. The header omits beta in its shorthand description.

The custom source does not register itself with `INSADObjectTracker` as a thermal source. Inspection of `INSAD3Eqn`/`INSADStabilized3Eqn` shows that their stabilized strong energy residual includes only tracked sources. Thus the Galerkin heating and SUPG strong residual are not fully consistent as currently wired. The temperature-dependent conductivity's `grad_k` is also not supplied to that strong residual.

## 6. ALE deck: what it solves and what is missing

The prototype mesh spans x = ±30 mm, y = 0–15 mm, z = 10–16 mm with 12 × 3 × 3 elements. It starts at t = 4 s with **uniform T = 623.15 K**, not a transferred dwell result. Unknowns are vector velocity, pressure, temperature and three mesh-displacement components.

Mass, momentum and energy use MOOSE INSAD kernels. PSPG stabilizes equal-order velocity/pressure interpolation; SUPG stabilizes transport. Separate material-advection and mesh-advection terms combine into ALE-relative transport:

```text
div(v) = 0
rho [dv/dt + (v-w)·grad(v)] = -grad(p) + div(2 mu D)
rho cp [dT/dt + (v-w)·grad(T)] = div(k grad(T)) + 2 beta mu D:D
Laplacian(mesh_displacement_component) = 0 inside the mesh
```

For the generated 3D mesh, `back` and `front` are the z-min and z-max faces. `bottom`/`top` are y-min/y-max. The plate interface (`back`) has zero velocity and fixed mesh displacement. The entire rectangular `front` face receives rotational, traverse and downward feed velocity. That inlet is not a 25 mm circular shoulder footprint. The four side faces move through `INSADDisplaceBoundaryBC`, using implicit Euler `d_new = d_old + dt*v_new`, with companion dummy integrated BCs for coupling allocation. The front mesh interior has no corresponding explicit inlet-plane position condition.

There is no explicit thermal inlet temperature, substrate heat-transfer condition, exposed-surface cooling, dwell-to-flow transfer, free-surface export, automatic quality-triggered remeshing, or campaign driver invoking this deck. Initializing the whole domain at a plasticization threshold skips the thermal transition rather than predicting it.

The existing `ale_flow_stage.log` shows repeated `FACTOR_NUMERIC_ZEROPIVOT`, then failure at dtmin on the very first step. The root cause is not proven by the log alone. Diagnose matrix blocks, scaling/preconditioner selection, mesh/velocity boundary coupling and pressure treatment before changing physics. In particular, the absence of a pressure Dirichlet condition alone does not prove a pressure nullspace when natural traction boundaries are present.

Official documentation confirms the implicit-Euler boundary update and warns that Laplacian smoothing does not prevent mesh inversion: [INSADDisplaceBoundaryBC](https://openpronghorn.inl.gov/source/bcs/INSADDisplaceBoundaryBC.html). The local implementation was also inspected.

## 7. Remeshing and state-transfer workflow

`create_afsd_remesh_stages.py` uses an external CSV containing `feed_end_mm,width_mm,height_mm,bead_volume_mm3,flash_volume_mm3`. `read_profile()` parses dimensions/volumes; `stage_schedule()` creates 1, 2.5 or 5 mm feed increments and checks cumulative volume balance. `dwell_stage()` defines the initial stationary phase. `geo_text()` writes OpenCASCADE/Gmsh geometry; `main()` optionally meshes it and records predecessor/output paths in JSON.

The geometry is an **equal-volume rectangular bead envelope**. Height is recalculated as `V_bead/(width*length)` rather than using the profile crest height. The previous and fresh deposit boxes are fragmented with the plate; a separate cylinder represents the rod. The code assumes physical volume tags survive fragmentation as expected, so generated tags need checking after geometry changes.

Flash appears in the volume ledger but is not generated as a physical volume. Consequently a profile's bookkeeping can balance while the new computational domain omits flash mass and energy. Changes to profile width/height also reshape inherited deposit material without a corresponding material-coordinate transformation.

`render_afsd_remesh_stage.py` replaces the mesh, changes block/boundary names, inserts local motion functions, splits history and virgin constitutive materials, and appends `SolutionUserObject`, `SolutionFunction` and `RemeshSolutionIC` blocks. It uses textual replacement rather than a structured HIT parser, so formatting changes can silently defeat substitutions.

The renderer treats the **whole rod and fresh deposit as virgin at every stage**. Only plate and prior deposit inherit temperature, deposition indicator and plastic history. New temperature defaults to 293.15 K. This discards the remaining rod's thermal/plastic history and introduces new deposit cold, even though it represents material transferred from a heated rod. Without an energy/mass transfer model this is not physically conservative.

Mesh geometry is built at stage end; local Y displacement moves the rod backward at stage start and then forward. The stage Z function is fixed at zero. Rod shortening occurs through discrete geometry replacement, not resolved material flow during that stage. The CNC feed/length outputs are commanded kinematics, not independently measured material-consumption results.

`source_state_variables()` searches binary `strings` output to decide whether all tensor components exist, and permits a scalar-only legacy fallback. This is not a complete Exodus schema validation. It assumes temperature, indicator and effective strain exist without proving their block/time coverage.

`run_low_ram_afsd_campaign.sh` renders and runs each predecessor-dependent stage sequentially. It is hardcoded to seven feed stages and therefore does not directly support the generator's 14- or 35-stage schedules. Its dt ceiling is 25 microseconds: at that maximum dt a 32 s campaign requires at least 1,280,000 accepted steps, excluding cutbacks. This explains the practical cost of literal 1,200 rpm rotation.

`run_low_ram_dwell.sh` limits threads, selects the matching MPICH launcher, applies a virtual-memory limit and, when available, a systemd memory/swap scope. These guards address resource usage, not physics accuracy. The low-RAM renderer changes contact penalty from 1e10 to 1e7 and gap conductance from 1e8 to 1e7 as well as solver settings. It is consequently a different numerical/physical contact configuration, not just a storage optimization.

Two old launch preparation scripts (`make_low_ram_afsd_trial.sh`, `make_coarse_afsd_trial.sh`) omit the now-required `--bead-profile-csv` argument. `make_literal_rotation_afsd_trial.sh` supplies it through `AFSD_BEAD_PROFILE`. The old smoke-test output-path substitution also does not match the nested `feed_5mm` output path, risking output-name reuse when that script is repaired.

## 8. FreeFEM-to-MOOSE migration

The actual predecessor is available at `scratch/final.edp`; it is not equivalent to the older description in the README.

| FreeFEM region | Function |
|---|---|
| 1–~200 | Process constants, tabulated properties, temperature/plasticization functions |
| ~200–450 | Johnson–Cook functions, torque/power model, machine limits, geometry, meshes and FE spaces |
| ~450–740 | State fields, output schemas, process and energy bookkeeping |
| ~740–1100 | Time-loop commands, compliant penalty contact, friction/effusivity calculations and rod mechanics |
| ~1100–1250 | Rod heat equation with advection/SUPG and ambient inflow |
| ~1250–1500 | Mixed plate velocity/pressure Picard solve and contact-force updates |
| ~1500–1710 | Incremental small-strain plastic update, dissipation and plate energy solve |
| ~1710–1920 | Qualification, transported rod density, level set, deposition height, rod volume and mesh motion |
| ~1920–2403 | Energy/limit histories, snapshots, state updates and final field export |

In FreeFEM, the `Ux/Uy/Uz` fields represent **velocities** in the mixed flow solve. In the solid MOOSE deck they represent **displacements**. Confusing these meanings would invalidate transfer and equation comparisons.

The predecessor implements explicit sequential coupling, a compliant axis with a preload and force cap, Johnson–Cook functions, heat-governor and spindle-budget caps, apparent heat capacity, rod/plate thermal solves, transported rod density, a level set and height-driven ALE movement. It explicitly sets flash height to zero and makes deposition efficiency unity by construction for transferred volume. Its level set does not turn this into a fully resolved retained-flash model.

The MOOSE contact implementation instead uses finite-strain J2 return mapping with tabulated hardening, displacement control, framework Coulomb contact, uncapped pressure-derived friction heat, and no latent heat. The new ALE formulation uses a hyperbolic-sine constitutive law. These are substantial changes in model formulation, not merely language translation.

FreeFEM results are therefore not a direct validation target until geometry, commands, coefficients, constitutive law, heat sources, thermal boundary conditions and time discretization are made comparable. The predecessor itself contains approximations and must not be treated as an experimental truth standard.

## 9. Visualization and result provenance

`visualize_results.py` plots actual CSV columns when available, but assumes an older 68 s, 200 mm traverse schedule, 50-to-15 mm rod, old force/temperature labels and inconsistent plasticization thresholds. Its default candidate CSV names do not locate staged histories. The 58 mm rod-axis limit would hide the current 200 mm rod trace. Its fallback FreeFEM CSV name has a different schema from the expected MOOSE `time`/`T_max` columns.

`watch_afsd_campaign.py` displays campaign scalar histories. Despite its low-memory description, `read_rows()` loads the whole CSV on every refresh. It chooses the last row without fully validating a partially written row. Stage order is hardcoded to seven.

`generate_3d_animation.py` calls `generate_all_simulation_videos()`. The video generator interpolates scalar histories onto a hardcoded 0–68 s timeline. `numpy.interp` holds endpoint values outside the available data range, which can visually extend a short/failed solve. It independently constructs approach/dwell/traverse/retraction, rod shortening and deposit length. It computes mushrooming from a chosen smoothstep/load/torque heuristic.

`simulation_renderer.py` batches polygons and draws a plate, rod, bead and collar with lighting. Bead height is fixed at 4.4 mm, half-width at 0.98 times rod radius; ripples and flash profiles are analytical shapes. Its temperature appearance is a radial falloff from a scalar peak. The multiview temperature contour is a **constructed Gaussian field**, not sampled `T(x,y,z)` from Exodus.

`process_schematic.py` is a standalone illustration generator. Its selected plate dimensions are 100 × 120 × 12 mm and rod height 80 mm; dormant dimension-label code contains other hardcoded dimensions. It does not read solver results.

These tools can explain the process, but labels such as “3D finite element kinematics”, “exact physical states” and “publication-quality simulation” are not evidence of solved geometry, temperature distribution, recrystallization, bond quality or flash prediction.

## 10. Findings that matter most

| Priority | Finding | Evidence / consequence |
|---|---|---|
| Blocking | Current contact decks fail input validation | `ReactionForceAux/execute_on` is private in the linked MOOSE build; reproduced for template and literal dwell |
| Blocking for prediction | No integrated dwell → ALE → free-surface export → conservative rezone loop | ALE input is standalone, starts uniformly hot, and campaign renderer uses contact template |
| High | Thermal expansion is not connected | Material exists, but mechanics action has no eigenstrain list and automatic collection defaults false |
| High | Friction heat is not actual solved slip dissipation | Uses constant mu, normal pressure and commanded omega*r regardless of sticking |
| High | Partial, nonconservative state transfer | Whole rod/fresh bead reset; elastic state not transferred; no enthalpy conservation |
| High | Flash is omitted from generated geometry | Scalar ledger records flash, but Gmsh emits plate/deposit/rod only |
| High | Current template geometry/kinematics disagree | Square rod, initial 5 mm gap, spin center y=12.5 mm vs rod center y=50 mm, heat center lacks initial offset; base spin Uy omits traverse translation |
| High | ALE model has no demonstrated accepted step | Saved log fails with numerical zero pivot at first step |
| High | ALE strain-rate/viscosity convention mismatch | sqrt(2 D:D) paired with sigma/(3 rate), rather than equivalent J2 rate |
| High | Reaction-based spindle power may omit driven work | Both rod top and rod bottom have tangential displacement BCs; reported spindle reaction/torque includes top only |
| Medium | Torque axis does not follow traverse | Renderer sets fixed stage-end center while center moves within stage; offset changes moment when resultant transverse force is nonzero |
| Medium | Temperature, friction and hardening constants vary by implementation | Solid parsed properties, UserObject tables, ALE fit and FreeFEM are not identical |
| Medium | “Low RAM” changes model parameters | Large penalty/conductance changes require sensitivity assessment |
| Medium | Profile input validation is incomplete | No explicit finite-number/duplicate-row/monotonic-cumulative-volume validation; NaN can evade ordinary comparisons |
| Medium | Scripts and generated inputs have drifted | Missing required profile arguments; all eight existing manifests lack current profile provenance |
| Medium | Stabilized ALE energy residual omits custom heating | Custom source is not registered with INSAD source tracker |
| Legacy defect | Yield-property lookup uses mismatched vector sizes | 11 yield stresses vs 7 thermal temperatures |
| Legacy defect | Volumetric friction kernel has wrong normalization/sign | Total W used as W/m³ with positive source residual |
| Legacy defect | Servo helper is static and dimensionally inconsistent | Constant time, unused displacement, stiffness × force |

The current thermal heat-flux boundary and its diagnostic also need a consistent reference/current-coordinate convention. The source deck supplies different center offsets to the BC and diagnostic. Even after repairing the centers, verify displaced integration areas and fields under large motion.

The deposition qualification field is diagnostic. It does not prove bonding or create mass. In the base deck it is evaluated on a separate bead while contact pressure is associated with plate/rod contact; in rendered stages it targets fresh deposit rather than the actual contact secondary surface. Pressure availability at the qualification nodes needs direct verification.

## 11. What the available checks establish

Performed with the existing binary, without compiling or running a new physical campaign:

| Check | Result |
|---|---|
| `rotating_disk_deposition-opt -i input/afsd_ale_flow_stage.i --check-input` | Passed: `Syntax OK` |
| `rotating_disk_deposition-opt -i input/deposition.i --check-input` | Failed at the three `ReactionForceAux/execute_on` settings |
| Same check on literal-rotation `dwell_low_ram.i` | Failed for the same three private parameters |
| Python AST parsing of all eight project Python scripts | Passed |
| `bash -n` for six script-directory shell scripts and `.git-autopush.sh` | Passed |

Syntax checks do not establish time integration, physical correctness, conservation or agreement with experiments. The private-parameter errors may hide subsequent input problems; removing them is only the first repair.

Historical outputs examined:

| Campaign | Available evidence |
|---|---|
| `feed_5mm_literal_rotation/feed_5mm` | Dwell CSV contains only t=0; no accepted physical evolution established |
| `feed_5mm_dt100ms/feed_5mm` | Dwell CSV ends near 0.695874 s |
| `feed_5mm_dt1s/feed_5mm` | Older campaign CSVs extend through 52.826222 s, but multiple traverse-stage peak-temperature columns are below ambient, e.g. stage 1 peak ~175.53 K |
| `feed_5mm_low_ram/feed_5mm` | Dwell reaches 4 s; stage 3 ends near 18.539163 s; stage 1 peak ~192.85 K is unphysical for the stated ambient/source setup |
| `feed_5mm_dt1s_z75/feed_5mm` | Dwell CSV ends at 1 s; stage 1 CSV only has its initial t=4 row |
| ALE | First-step zero-pivot failure in saved log |

The below-ambient histories are evidence of serious problems in those historical outputs, not proof of a unique cause and not measurements from a new run of current source. Several older stage decks still use unclamped `PlasticHeatEnergy`. Completed timestamps are not equivalent to valid physics.

All eight existing manifests lack `bead_geometry_source`; their deposition durations differ (35 s, ~48.8262 s or 28 s). There are 20 generated input decks and 99 generated geometry files. They represent successive experiments, not one consistently regenerated campaign.

The root summary's 701.27 K, 5 kN, 6.2 kW and 95% deposition refer to an older 68 s run. The source CSV/Exodus files named by that summary are not present at the project root. Those figures cannot validate the current literal-rotation/ALE implementation.

## 12. Usage and development sequence

The intended local build route is the MOOSE Makefile with the matching MOOSE environment. The intended input checks are:

```bash
./rotating_disk_deposition-opt -i input/deposition.i --check-input
./scripts/check_ale_flow_stage.sh
```

The first currently fails as described above. After repairing and validating the model, profile-driven preparation would use:

```bash
AFSD_BEAD_PROFILE=/absolute/path/to/validated_profile.csv \
  ./scripts/make_literal_rotation_afsd_trial.sh
./scripts/run_low_ram_afsd_campaign.sh 0
```

These commands describe the existing workflow, not a recommendation to launch the currently incomplete campaign. Preparation regenerates campaign files; archive scientifically important prior runs first. The full driver is expensive and does not invoke the ALE flow deck.

A defensible development sequence is:

1. Repair current input compatibility and establish one documented build/input combination.
2. Unify geometry, coordinate frames, motion, thermal coefficients and constitutive data provenance.
3. Connect thermal eigenstrain; verify heating, thermal expansion and plasticity separately with meaningful reference problems.
4. Make interface heat consistent with solved traction and slip, and account for work on every driven boundary.
5. Validate constitutive invariants, derivatives and unit conventions with simple loading cases.
6. Obtain converged ALE motion/energy tests, then add thermal inlet/substrate conditions and mass/energy budgets.
7. Implement actual dwell-state transfer and free-surface geometry export, retaining flash and appropriate internal state.
8. Validate remesh conservation and continuity before chaining stages; regenerate manifests/decks from one version.
9. Perform mesh/timestep/contact-penalty sensitivity studies and compare independent temperature, force, torque and bead-profile measurements.
10. Produce spatial visualizations from Exodus and clearly label procedural illustrations.

The small test deck currently provided is a finite-strain syntax experiment, not a complete verification test: only Uz is fixed on one named face and rigid modes remain for a mechanics solve. Scratch files explore older prescribed motion, pressure and heating approaches; their names containing “ALE” do not necessarily imply an ALE material-transport formulation.

MOOSE's existing radial-return machinery is the foundation of the solid model; the custom extension primarily adds remesh initialization. The official description is consistent with that division of responsibility: [TemperatureDependentHardeningStressUpdate](https://mooseframework.inl.gov/releases/moose/2022-06-10/source/materials/TemperatureDependentHardeningStressUpdate.html). Exact behavior for this checkout was checked in the local MOOSE source rather than inferred solely from the historical documentation.

The application has useful building blocks for coupled AFSD research. Its present status is a partially integrated research model with reproducible input failures and unresolved conservation/geometry issues, rather than a validated predictive deposition solver.
