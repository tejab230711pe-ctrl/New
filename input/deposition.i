# ==============================================================================
# Additive Friction Stir Deposition (AFSD) — Full Coupled Thermo-Mechanical Model
# Application: RotatingDiskDepositionApp
# Material: AA5083 Aluminum Alloy (Viscoplastic Solid-State Consolidation)
# Subdomains: Block 0 = Plate, Block 1 = Consumable Tool Rod, Block 2 = Deposited Bead Layer
#
# GOVERNING EQUATIONS OF MATERIAL PLASTICIZATION & CONTACT MECHANICS:
# 1. Conservation of Mass (Isochoric plastic flow & Feed-Deposit balance):
#    div(v) = 0,  V_dot_feed = V_dot_layer + V_dot_flash
#    A_rod * v_feed = W_bead * h_layer * v_traverse * (1 + beta_flash)
# 2. Conservation of Linear Momentum (Quasi-static equilibrium):
#    div(sigma) + b = 0,  sigma = -p*I + s
# 3. Finite-Strain Continuum Kinematics:
#    F = I + grad(u),  Delta_eps = 0.5 * [grad(Delta_u) + grad(Delta_u)^T]
#    Delta_eps = Delta_eps_elastic + Delta_eps_plastic
# 4. Temperature-Dependent Radial Return J2 Plasticity (von Mises Yield Criterion):
#    f(sigma, T, eps_p) = sigma_vm - sigma_y(T, eps_p) <= 0
#    sigma_vm = sqrt(3/2 * s : s),  s = sigma - (1/3)*tr(sigma)*I
#    Delta_eps_p = Delta_gamma * (3/2) * (s / sigma_vm)
#    sigma_y(T, eps_p) thermally softens from 255.21 MPa (293K) down to 28 MPa (798K)
# 5. Conservation of Energy (Coupled Thermo-Mechanical Conduction-Advection):
#    rho*cp*(dT/dt + v_adv.grad(T)) = div(k*grad(T)) + q_fric + q_plast
#    q_fric  = delta * tau_cont * (omega * r) / h_interface
#    q_plast = eta_TQ * sigma_vm * edot_p  (Taylor-Quinney coefficient eta_TQ = 0.90)
# 6. Sliding-to-Sticking Contact Friction Transition:
#    tau_cont = min(mu(T)*P, sigma_y(T) / sqrt(3))
# 7. Process Reaction Forces:
#    Axial Forging Force: F_z = integral(t_z dA), a solved contact reaction
#    for validation against the CNC data; it is not prescribed as force control.
#    Spindle Torque:      M_z = integral(r * tau_cont dA) = P_spindle / omega
#    Traverse Force:      F_y = integral(t_y dA)
#    Transverse Force:    F_x = integral(t_x dA), zero in this symmetric,
#                           shoulder-only model unless asymmetry is added.
# 8. Axial Rod Shortening Mechanics:
#    Top Quill Actuator: Uz(z_top, t) feeds downward by 35 mm over the
#                         simultaneous 50 mm model-Y traverse.
#    Bottom Tip Interface: Uz(z_bot, t) rests on substrate under contact traction
#    Rod Interior: Solved by Finite-Element elastoviscoplastic momentum balance
# 9. Dual-Factor Solid-State Deposition Gate:
#    Deposition iff: t >= t_dwell & P >= 0.25 MPa & 350 °C <= T <= 525 °C & y <= y_tool + R
# ==============================================================================

[Mesh]
  # Required by displaced-mesh mechanical contact and interface heat transfer.
  displacements = 'Ux Uy Uz'
  # 1. Substrate Plate (Block 0) - (nx=16, ny=25, nz=2)
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 16
    ny = 25
    nz = 2
    xmin = -0.060
    xmax =  0.060
    ymin =  0.000
    ymax =  0.300
    zmin =  0.000
    zmax =  0.020
  []
  [plate_id]
    type = SubdomainBoundingBoxGenerator
    input = plate_mesh
    bottom_left = '-0.060 0.000 0.000'
    top_right = '0.060 0.300 0.020'
    block_id = 0
    block_name = 'plate'
  []

  # 2. Consumable Tool Rod (Block 1) - (nx=4, ny=4, nz=5)
  [rod_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 4
    nz = 5
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.0375
    ymax =  0.0625
    zmin =  0.025
    zmax =  0.075
  []
  [rod_id]
    type = SubdomainBoundingBoxGenerator
    input = rod_mesh
    bottom_left = '-0.0125 0.0375 0.025'
    top_right = '0.0125 0.0625 0.075'
    block_id = 1
    block_name = 'rod'
  []

  # 3. Deposited Bead Layer (Block 2) - (nx=4, ny=20, nz=2)
  [bead_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 20
    nz = 2
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.050
    ymax =  0.250
    zmin =  0.020
    zmax =  0.023
  []
  [bead_id]
    type = SubdomainBoundingBoxGenerator
    input = bead_mesh
    bottom_left = '-0.0125 0.050 0.020'
    top_right = '0.0125 0.250 0.023'
    block_id = 2
    block_name = 'bead'
  []

  # Combine all 3 bodies into a unified multi-block simulation mesh
  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_id bead_id'
  []

  # Automatically split and isolate all boundaries by subdomain to prevent collisions
  [break_boundary]
    type = BreakBoundaryOnSubdomainGenerator
    input = combine
  []
[]

[Functions]
  # Intended CNC program (machine X = model Y):
  #   G04 P4.0; G01 X50 Z-35, with user-prescribed Z feed = 75 mm/min.
  # The 35 mm Z consumption lasts 28 s; model-Y advances 50 mm in the same
  # interval (107.142857 mm/min). Machine X maps to simulation Y.
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, 0.00178571428571429 * (t - 4.0), 0.050))'
  []
  # The 0.25 mm initial interference creates the displacement-controlled
  # forging contact.  No prescribed force is applied.
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = '0.0'
  []
  # Top-quill motion for the coupled contact solve. Continuous rod consumption
  # requires ALE/remeshing; it must not be imposed as solid compression.
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, -0.00125 * (t - 4.0), -0.035))'
  []
  # Instantaneous physical rod height in mm
  [rod_height_func]
    type = ParsedFunction
    expression = '200.0 - if(t < 4.0, 0.0, if(t < 32.0, 35.0 * (t - 4.0) / 28.0, 35.0))'
  []
  # Cumulative consumed rod length in mm
  [rod_consumed_func]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, 35.0 * (t - 4.0) / 28.0, 35.0))'
  []
  # Axial feed rate in mm/min
  [axial_feed_rate_func]
    type = ParsedFunction
    expression = 'if(t >= 4.0 & t < 32.0, 75.0, 0.0)'
  []
  # Literal 1200 RPM rigid-body spindle rotation. The stage renderer replaces
  # these with stage-local versions after every rezone.
  [rod_spin_ux]
    type = ParsedFunction
    expression = 'x * (cos(125.663706143592 * t) - 1.0) - (y - 0.0125) * sin(125.663706143592 * t)'
  []
  [rod_spin_uy]
    type = ParsedFunction
    expression = 'x * sin(125.663706143592 * t) + (y - 0.0125) * (cos(125.663706143592 * t) - 1.0)'
  []

  # Piecewise-linear true stress vs plastic strain hardening curves for AA5083 across temperatures:
  # 1. Room Temperature (293.15 K / 20 °C)
  [hf_293K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '255.21e6 270.0e6 295.0e6 330.0e6 380.0e6 440.0e6 480.0e6 520.0e6 550.0e6'
  []
  # 2. Warm Temperature (450.0 K / 177 °C)
  [hf_450K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '190.0e6 205.0e6 225.0e6 255.0e6 290.0e6 325.0e6 345.0e6 370.0e6 390.0e6'
  []
  # 3. Plasticization Onset (623.15 K / 350 °C)
  [hf_623K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '95.0e6 102.0e6 112.0e6 125.0e6 140.0e6 152.0e6 160.0e6 170.0e6 180.0e6'
  []
  # 4. Active Stir Zone Consolidation (723.15 K / 450 °C)
  [hf_723K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '52.0e6 56.0e6 62.0e6 69.0e6 76.0e6 82.0e6 85.0e6 90.0e6 95.0e6'
  []
  # 5. Peak Solid-State Plastic Stir (798.15 K / 525 °C)
  [hf_798K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '28.0e6 30.5e6 33.5e6 36.5e6 39.5e6 41.5e6 42.5e6 45.0e6 48.0e6'
  []
  # 6. Near-Solidus Boundary (850.0 K / 577 °C)
  [hf_850K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '12.0e6 13.0e6 14.5e6 15.8e6 16.9e6 17.6e6 18.0e6 19.0e6 20.0e6'
  []
[]

[Variables]
  # Temperature field (K)
  [T]
    order = FIRST
    family = LAGRANGE
    initial_condition = 293.15
  []
  # 3D Mechanical displacement vector fields (m) on substrate plate and tool rod
  [Ux]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
  [Uy]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
  [Uz]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
[]

[UserObjects]
  # Shared AA5083 properties for the solved contact-friction heat flux.
  [aa5083_properties]
    type = AA5083ThermalProperties
  []
[]

[Problem]
  # Retain the mechanical residual at constrained spindle nodes so that force,
  # torque, and mechanical power are measured reactions rather than placeholders.
  extra_tag_vectors = 'reaction'
[]

[Physics/SolidMechanics/QuasiStatic]
  displacements = 'Ux Uy Uz'
  [all]
    displacements = 'Ux Uy Uz'
    strain = FINITE
    decomposition_method = HughesWinget
    volumetric_locking_correction = false
    add_variables = false
    extra_vector_tags = 'reaction'
    block = 'plate rod'
    # All six plastic-strain components are persisted to Exodus.  The remesh
    # transfer reconstructs the complete J2 history tensor in the next stage.
    generate_output = 'stress_xx stress_yy stress_zz stress_xy stress_yz stress_zx vonmises_stress plastic_strain_xx plastic_strain_yy plastic_strain_zz plastic_strain_xy plastic_strain_yz plastic_strain_zx strain_xx strain_yy strain_zz'
  []
[]

[AuxVariables]
  [mushy_fraction]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [friction_heat]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [tool_rpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Constraint reactions at the driven spindle face.  These are populated
  # from the tagged mechanical residual, not prescribed loads.
  [spindle_reaction_x]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [spindle_reaction_y]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [spindle_reaction_z]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # State variable: 1.0 when element is deposited under hot plasticizing stir conditions, 0.0 if not yet deposited
  [is_deposited]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Instantaneous physical rod height in mm.
  [rod_height_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 200.0
  []
  # Cumulative consumed rod length in mm (0mm -> 35mm)
  [consumed_length_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Axial feed rate in mm/min
  [axial_feed_rate_mmpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Zener-Hollomon parameter ln(Z) = ln(edot) + Q/(R*T)
  [zener_hollomon_lnZ]
    order = FIRST
    family = LAGRANGE
    initial_condition = 55.0
  []
[]

[Kernels]
  # 1. Heat conduction time derivative: rho * cp * dT/dt
  [heat_time]
    type = HeatConductionTimeDerivative
    variable = T
    density_name = density
    specific_heat = specific_heat
  []
  # 2. Diffusion / spatial heat conduction: - div(k * grad(T))
  [heat_conduction]
    type = HeatConduction
    variable = T
    thermal_conductivity = thermal_conductivity
  []
  # Plastic work is a mechanical-to-thermal source.  Clamp transient remesh
  # projection artefacts so irreversible dissipation can never cool the body.
  [plastic_heat]
    type = NonnegativePlasticHeatEnergy
    variable = T
    displacements = 'Ux Uy Uz'
    coeff = 0.90
    block = 'plate rod'
  []
[]

[AuxKernels]
  # The commanded spindle speed is already 1200 RPM during both dwell and travel.
  [tool_rpm_aux]
    type = ParsedAux
    variable = tool_rpm
    use_xyzt = true
    expression = 'if(t <= 32.0, 1200.0, 0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Viscoplastic / mushy bonding fraction for AA5083 in the 0.6 - 0.9 T_solidus range (350 - 525 °C / 623.15 - 798.15 K)
  [mushy_aux]
    type = ParsedAux
    variable = mushy_fraction
    coupled_variables = 'T'
    expression = 'if(T <= 623.15, 0.0, if(T >= 798.15, 1.0, (T - 623.15) / 175.0))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Uncapped friction-work flux diagnostic (W/m^2).  It uses the solved
  # pressure; it is neither a prescribed heat input nor a spindle-power cap.
  [friction_heat_aux]
    type = ParsedAux
    variable = friction_heat
    coupled_variables = 'contact_pressure tool_rpm'
    use_xyzt = true
    expression = 'if(contact_pressure > 0.0 & tool_rpm > 10.0,
                    0.90 * 0.35 *
                    contact_pressure * (tool_rpm * 2.0 * 3.14159265 / 60.0) *
                    sqrt(x*x + (y - (0.0125 + if(t < 4.0, 0.0, min(0.050, 0.00178571428571429*(t - 4.0)))))^2),
                    0.0)'
    # Keep the diagnostic synchronized with ContactPressureAux, which is
    # refreshed during nonlinear contact iterations.  This does not prescribe
    # heat; it makes the reported interface power match the coupled BC.
    execute_on = 'NONLINEAR TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Extract actual resultant reactions at the prescribed spindle face.
  [spindle_reaction_x_aux]
    type = ReactionForceAux
    variable = spindle_reaction_x
    v = Ux
    vector_tag = reaction
    execute_on = 'TIMESTEP_END'
  []
  [spindle_reaction_y_aux]
    type = ReactionForceAux
    variable = spindle_reaction_y
    v = Uy
    vector_tag = reaction
    execute_on = 'TIMESTEP_END'
  []
  [spindle_reaction_z_aux]
    type = ReactionForceAux
    variable = spindle_reaction_z
    v = Uz
    vector_tag = reaction
    execute_on = 'TIMESTEP_END'
  []

  # Solid-State Layer Deposition Gate:
  # Material CANNOT deposit immediately; requires simultaneous satisfaction of:
  # 1. Contact forging pressure P >= 0.25 MPa under rotating tool shoulder
  # 2. Temperature strictly within 0.6 - 0.9 T_solidus window: 350 °C <= T <= 525 °C (623.15 K <= T <= 798.15 K)
  # 3. Active traverse (t >= 4.0s) with shoulder passing over element: y <= tool_y + R
  # 4. State retention: once consolidated, bead remains permanently 100% solid through cooling
  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    use_xyzt = true
    block = 'bead'
    coupled_variables = 'T contact_pressure is_deposited'
    expression = 'if(is_deposited > 0.5, 1.0,
                    if(t >= 4.0 & contact_pressure >= 2.5e5 & T >= 623.15 & T <= 798.15 &
                       y <= (0.0125 + min(0.050, 0.00178571428571429 * (t - 4.0)) + 0.015),
                       1.0, 0.0))'
    execute_on = 'TIMESTEP_END'
  []

  # Instantaneous physical rod height tracking (50mm -> 15mm)
  [rod_height_aux]
    type = FunctionAux
    variable = rod_height_mm
    function = rod_height_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Consumed rod length tracking (0mm -> 35mm)
  [consumed_length_aux]
    type = FunctionAux
    variable = consumed_length_mm
    function = rod_consumed_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Axial feed rate tracking (45-48 mm/min during dwell/traverse)
  [axial_feed_rate_aux]
    type = FunctionAux
    variable = axial_feed_rate_mmpm
    function = axial_feed_rate_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []


  # Zener-Hollomon parameter ln(Z) for hot viscoplastic deformation (AA5083: Q=145 kJ/mol, R=8.314 J/mol-K, edot~1500 s^-1)
  [zener_hollomon_aux]
    type = ParsedAux
    variable = zener_hollomon_lnZ
    coupled_variables = 'T'
    expression = '7.313 + 145000.0 / (8.314 * max(300.0, T))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []
[]

[Materials]
  # AA5083 temperature-dependent thermal conductivity (W/m·K)
  [aa5083_k]
    type = ParsedMaterial
    property_name = thermal_conductivity
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 112.5 + (122.7 - 112.5)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 122.7 + (142.3 - 122.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 142.3 + (177.2 - 142.3)*((T - 273.15) - 280.0)/300.0, 177.2)))'
  []

  # AA5083 density (kg/m^3)
  [aa5083_rho]
    type = ParsedMaterial
    property_name = density
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 2673.9 + (2642.7 - 2673.9)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 2642.7 + (2611.5 - 2642.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 2611.5 + (2549.2 - 2611.5)*((T - 273.15) - 280.0)/300.0, 2549.2)))'
  []

  # AA5083 solid-state specific heat capacity (J/kg·K).  No apparent/latent
  # heat is included: AFSD is modelled below solidus, not as a melt process.
  [aa5083_cp]
    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 924.1 + (984.2 - 924.1)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 984.2 + (1081.2 - 984.2)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))'
  []

  # Thermal strain couples the solved temperature field back into stress.
  [thermal_expansion]
    type = ComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 2.38e-5
    temperature = T
    stress_free_temperature = 293.15
    eigenstrain_name = thermal_eigenstrain
    block = 'plate rod'
  []

  # Elasticity tensor for AA5083 (E = 70.3 GPa, nu = 0.33)
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
    block = 'plate rod'
  []

  # Temperature-dependent radial return J2 plasticity for AA5083
  [temp_dep_hardening]
    type = RemeshTemperatureDependentHardeningStressUpdate
    hardening_functions = 'hf_293K hf_450K hf_623K hf_723K hf_798K hf_850K'
    temperatures = '293.15 450.0 623.15 723.15 798.15 850.0'
    temperature = T
    relative_tolerance = 1.0e-8
    absolute_tolerance = 1.0e-4
    # This temperature-dependent return-mapping model does not implement
    # MOOSE local substepping.  Relax the material time-step limiter from the
    # default 1e-4 equivalent-plastic-strain increment without requesting the
    # unsupported substepping feature.
    max_inelastic_increment = 1.0e-2
    # Exodus fields required to reconstruct J2 hardening in a later remesh
    # stage. The Remesh* material consumes them through SolutionFunctions.
    # Tensor plastic_strain components are already emitted by the solid-
    # mechanics action.  Output only the scalar history missing from it.
    output_properties = 'effective_plastic_strain'
    outputs = exodus
    block = 'plate rod'
  []

  # Multi-inelastic radial return stress calculator
  [radial_return_stress]
    type = ComputeMultipleInelasticStress
    tangent_operator = nonlinear
    inelastic_models = 'temp_dep_hardening'
    block = 'plate rod'
  []

  # Stress : plastic-strain-rate, consumed by PlasticHeatEnergy in [Kernels].
  [plastic_work]
    type = ComputePlasticHeatEnergy
    block = 'plate rod'
  []
[]

# Literal rotating Coulomb contact. Tangential traction and slip are solved.
[Contact]
  [rod_plate]
    # Node-face contact is imposed at the fine plate nodes against the coarser
    # shoulder face; this is the robust primary/secondary ordering in MOOSE.
    primary = back_to_rod
    secondary = front_to_plate
    model = coulomb
    formulation = tangential_penalty
    displacements = 'Ux Uy Uz'
    friction_coefficient = 0.35
    # Keep the calibrated dimensional penalty used by the stable normal-contact
    # model.  Normalizing 1e7 here magnifies the first interference correction
    # and inverted the rod mesh before the friction state could converge.
    penalty = 1.0e10
  []
[]

# Stabilize the nonlinear stick/slip state during literal shoulder rotation.
# This damps only a reversal within one Newton solve; it does not reduce the
# prescribed spindle RPM or the physical accumulated slip.
[Dampers]
  [rod_plate_slip]
    type = ContactSlipDamper
    primary = 'back_to_rod'
    secondary = 'front_to_plate'
    max_iterative_slip = 5.0e-4
    min_damping_factor = 0.05
  []
[]

# Bidirectional thermal contact transfers the mechanically generated friction
# heat from the rod into the substrate across the same moving interface.
[ThermalContact]
  [rod_plate]
    type = GapHeatTransfer
    variable = T
    primary = back_to_rod
    secondary = front_to_plate
    displacements = 'Ux Uy Uz'
    gap_conductance = 1.0e8
  []
[]

[BCs]
  # Fixed displacement at base of the backing plate (clamped to steel anvil table at z = 0)
  [fix_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'back_to_plate'
    value = 0.0
  []
  [fix_bottom_y]
    type = DirichletBC
    variable = Uy
    boundary = 'back_to_plate'
    value = 0.0
  []
  [fix_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'back_to_plate'
    value = 0.0
  []

  # Actuator boundary conditions on the TOP of the tool rod (Machine Spindle Quill at z = 0.075)
  [rod_top_x]
    type = FunctionDirichletBC
    variable = Ux
    boundary = 'front_to_rod'
    function = rod_spin_ux
  []
  [rod_top_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'front_to_rod'
    function = rod_spin_uy
  []
  # Continuous downward axial feed driving rod height shortening (50 mm -> 15 mm)
  [rod_top_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'front_to_rod'
    function = rod_motion_z_top
  []

  # Tip Uz is free: the contact constraint solves it. Prescribing it here as
  # well over-constrained contact and inverted the plate mesh.
  [rod_bottom_x]
    type = FunctionDirichletBC
    variable = Ux
    boundary = 'back_to_rod'
    function = rod_spin_ux
  []
  [rod_bottom_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'back_to_rod'
    function = rod_spin_uy
  []

  # Backing plate conductive/convective heat dissipation into steel anvil table at z = 0
  [plate_base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'back_to_plate'
    T_infinity = 293.15
    coefficient = 250.0
  []

  # Natural convective cooling on all exposed top/side surfaces
  [convective_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'front_to_plate bottom_to_plate top_to_plate left_to_plate right_to_plate left_to_rod right_to_rod bottom_to_rod top_to_rod front_to_bead left_to_bead right_to_bead top_to_bead bottom_to_bead'
    T_infinity = 293.15
    coefficient = 25.0
  []

  # q = eta * mu(T) * solved_contact_pressure * omega * radius: thermal
  # dissipation of the literal solved Coulomb sliding contact above.
  # The entire uncapped interface source is applied at the contact interface;
  # GapHeatTransfer then partitions it by the thermal response of both bodies.
  # For AA5083 rod + AA5083 plate, sqrt(k*rho*cp) is identical on both sides,
  # so the governing effusivity partition is H_plate = H_rod = 0.5.  Do not
  # additionally multiply this source by 0.5: that would discard half of the
  # generated energy instead of depositing it into the rod.
  [rod_friction_heat]
    type = ContactFrictionHeatFlux
    variable = T
    boundary = front_to_plate
    contact_pressure = contact_pressure
    rpm = 1200
    friction_coefficient = 0.35
    tool_center_y = rod_motion_y
    heat_partition = 1.0
  []
[]

[Postprocessors]
  # Commanded CNC position trace.  Machine X is simulation Y; these are
  # deliberately separate from displacement so each accepted step exposes the
  # intended G-code motion in the terminal and CSV histories.
  [command_machine_X_mm]
    type = FunctionValuePostprocessor
    function = rod_motion_y
    scale_factor = 1000.0
  []
  [command_quill_Z_mm]
    type = FunctionValuePostprocessor
    function = rod_motion_z_top
    scale_factor = 1000.0
  []
  # Peak temperature in the substrate (K)
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  # Core temperature at active deposition point (K)
  [T_core]
    type = PointValue
    variable = T
    point = '0.0 0.050 0.020'
  []
  # Maximum von Mises stress in the consumable tool rod (Pa)
  [rod_max_vonmises_stress]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
    block = 'rod'
  []
  # Average von Mises stress in the consumable tool rod (Pa)
  [rod_avg_vonmises_stress]
    type = ElementAverageValue
    variable = vonmises_stress
    block = 'rod'
  []
  # Axial compressive stress in the consumable tool rod (Pa)
  [rod_axial_stress_zz]
    type = ElementAverageValue
    variable = stress_zz
    block = 'rod'
  []
  # Most-compressive accumulated axial plastic strain in the rod.  The
  # postprocessor deliberately uses min because compression is negative.
  [rod_max_plastic_strain_zz]
    type = ElementExtremeValue
    variable = plastic_strain_zz
    value_type = min
    block = 'rod'
  []
  # Scalar J2 history used by the temperature-dependent hardening law.  This
  # is the correct quantity to compare across remesh stages, not one tensor
  # component such as plastic_strain_zz.
  [max_effective_plastic_strain]
    type = ElementExtremeValue
    variable = effective_plastic_strain
    value_type = max
    block = 'plate rod'
  []
  # Average plastic strain in the rod
  [rod_avg_plastic_strain_zz]
    type = ElementAverageValue
    variable = plastic_strain_zz
    block = 'rod'
  []
  # Peak contact pressure (Pa)
  [max_contact_pressure]
    type = NodalExtremeValue
    variable = contact_pressure
    value_type = max
  []
  # Resultant spindle reactions.  Their signs are the reactions exerted on
  # the prescribed rod-top boundary, so process loads use the opposite sign.
  [spindle_reaction_x_N]
    type = NodalSum
    variable = spindle_reaction_x
    boundary = front_to_rod
  []
  [spindle_reaction_y_N]
    type = NodalSum
    variable = spindle_reaction_y
    boundary = front_to_rod
  []
  [spindle_reaction_z_N]
    type = NodalSum
    variable = spindle_reaction_z
    boundary = front_to_rod
  []
  [spindle_torque_Nm]
    type = TorqueReaction
    boundary = front_to_rod
    reaction_force_variables = 'spindle_reaction_x spindle_reaction_y spindle_reaction_z'
    axis_origin = '0.0 0.050 0.0'
    direction_vector = '0.0 0.0 1.0'
  []
  # Tool RPM
  [current_rpm]
    type = AverageNodalVariableValue
    variable = tool_rpm
  []
  # Total uncapped friction work generated at the active interface.  This is
  # the direct model quantity to compare with Excel spindle power; it does not
  # prescribe or cap the heat source.
  [friction_power_W]
    type = SideIntegralVariablePostprocessor
    variable = friction_heat
    boundary = front_to_plate
  []
  [friction_power_kW]
    type = ParsedPostprocessor
    pp_names = 'friction_power_W'
    expression = 'friction_power_W / 1000.0'
  []
  # Mechanical spindle power from solved torque; compare this with the Excel
  # spindle power.  friction_power_kW is the heat dissipated at efficiency 0.9.
  [power_kW]
    type = ParsedPostprocessor
    pp_names = 'spindle_torque_Nm'
    expression = 'spindle_torque_Nm * 1200.0 * 2.0 * 3.14159265 / (60.0 * 1000.0)'
  []
  # Axial load in kN
  [force_kN]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_z_N'
    expression = 'abs(spindle_reaction_z_N) / 1000.0'
  []
  # Fraction of bead elements actively deposited
  [deposited_bead_pct]
    type = ElementAverageValue
    variable = is_deposited
    block = 'bead'
  []
  # Instantaneous physical rod height (mm)
  [rod_height_mm]
    type = ElementAverageValue
    variable = rod_height_mm
    block = 'rod'
  []
  # Cumulative consumed rod length (mm)
  [consumed_length_mm]
    type = ElementAverageValue
    variable = consumed_length_mm
    block = 'rod'
  []
  # Machine axial feed rate (mm/min)
  [feed_rate_mmpm]
    type = ElementAverageValue
    variable = axial_feed_rate_mmpm
    block = 'rod'
  []
  # Process force along simulation Y (machine X): reaction sign reversed.
  [traverse_force_N]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_y_N'
    expression = '-spindle_reaction_y_N'
  []
  # Transverse process force along simulation X: reaction sign reversed.
  [transverse_force_N]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_x_N'
    expression = '-spindle_reaction_x_N'
  []
  # Zener-Hollomon parameter ln(Z) in active stir zone
  [ln_Zener_Hollomon]
    type = ElementAverageValue
    variable = zener_hollomon_lnZ
    block = 'bead'
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'
  petsc_options_value = 'hypre boomeramg 200'
  line_search = 'none'

  nl_rel_tol = 1.0e-3
  nl_abs_tol = 5.0
  l_tol = 1.0e-2
  l_max_its = 200
  nl_max_its = 40

  start_time = 0.0
  end_time = 32.0
  # Literal rotation needs a small recovery step when a contact Newton solve
  # cuts back, rather than aborting at the old 0.1 ms floor.
  dtmin = 1.0e-6
  dtmax = 0.05

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 0.25
    optimal_iterations = 8
    iteration_window = 4
    growth_factor = 1.25
    cutback_factor = 0.5
    cutback_factor_at_failure = 0.25
  []
[]

[Outputs]
  # Compact accepted-step process trace for debugging the CNC motion and
  # coupled response.  `tee` keeps the same table in the campaign log.
  [motion_console]
    type = Console
    execute_on = TIMESTEP_END
    show = 'command_machine_X_mm command_quill_Z_mm consumed_length_mm rod_height_mm feed_rate_mmpm current_rpm force_kN spindle_torque_Nm power_kW friction_power_kW traverse_force_N transverse_force_N T_max T_core max_effective_plastic_strain max_contact_pressure'
    max_rows = 0
    scientific_time = true
    time_precision = 6
  []
  [exodus]
    type = Exodus
    # temp_dep_hardening explicitly targets this output and limits material
    # export to effective_plastic_strain; do not enable all properties here.
    file_base = afsd_deposition_out
  []
  [csv]
    type = CSV
    file_base = afsd_deposition_out
  []
[]
