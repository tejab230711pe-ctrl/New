# ==============================================================================
# AFSD STAGE 1: DWELL & CONTACT FRICTION HEATING (MOOSE NATIVE INPUT)
# Geometry: Cylindrical Consumable Rod (D=25mm, L=200mm) & Workpiece Plate (50x100x10mm)
# Physics: Finite-Strain Quasi-Static Solid Mechanics + Thermal Conduction + Contact
# ==============================================================================

[Mesh]
  [file_mesh]
    type = FileMeshGenerator
    file = dwell.msh
  []
  parallel_type = distributed
  patch_update_strategy = iteration
  displacements = 'Ux Uy Uz'
  [thermal_primary]
    type = LowerDBlockFromSidesetGenerator
    input = file_mesh
    sidesets = workpiece_top
    new_block_name = thermal_primary
  []
  [thermal_secondary]
    type = LowerDBlockFromSidesetGenerator
    input = thermal_primary
    sidesets = rod_bottom
    new_block_name = thermal_secondary
  []
[]

[Functions]
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, 0.00178571428571429 * (t - 4.0), 0.050))'
  []
  [rod_center_y]
    type = ParsedFunction
    symbol_names = 'travel'
    symbol_values = 'rod_motion_y'
    expression = '0.050 + travel'
  []
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = '0.0'
  []
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, -0.00125 * (t - 4.0), -0.035))'
  []
  [rod_height_func]
    type = ParsedFunction
    expression = '200.0 - if(t < 4.0, 0.0, if(t < 32.0, 35.0 * (t - 4.0) / 28.0, 35.0))'
  []
  [rod_consumed_func]
    type = ParsedFunction
    expression = 'if(t < 4.0, 0.0, if(t < 32.0, 35.0 * (t - 4.0) / 28.0, 35.0))'
  []
  [axial_feed_rate_func]
    type = ParsedFunction
    expression = 'if(t >= 4.0 & t < 32.0, 75.0, 0.0)'
  []
  [rod_spin_ux]
    type = ParsedFunction
    expression = 'x * (cos(125.663706143592 * (t - 0)) - 1.0) - (y - 0.0125) * sin(125.663706143592 * (t - 0))'
  []
  [rod_spin_uy]
    type = ParsedFunction
    symbol_names = translation
    symbol_values = rod_stage_translation_y
    expression = 'x * sin(125.663706143592 * (t - 0)) + (y - 0.0125) * (cos(125.663706143592 * (t - 0)) - 1.0) + translation'
  []

  [hf_293K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '255.21e6 270.0e6 295.0e6 330.0e6 380.0e6 440.0e6 480.0e6 520.0e6 550.0e6'
  []
  [hf_450K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '190.0e6 205.0e6 225.0e6 255.0e6 290.0e6 325.0e6 345.0e6 370.0e6 390.0e6'
  []
  [hf_623K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '95.0e6 102.0e6 112.0e6 125.0e6 140.0e6 152.0e6 160.0e6 170.0e6 180.0e6'
  []
  [hf_723K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '52.0e6 56.0e6 62.0e6 69.0e6 76.0e6 82.0e6 85.0e6 90.0e6 95.0e6'
  []
  [hf_798K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '28.0e6 30.5e6 33.5e6 36.5e6 39.5e6 41.5e6 42.5e6 45.0e6 48.0e6'
  []
  [hf_850K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '15.0e6 16.5e6 18.0e6 20.0e6 22.0e6 23.5e6 24.5e6 26.0e6 28.0e6'
  []
  [rod_stage_center_y]
    type = ConstantFunction
    value = 0.0125
  []
  [rod_stage_translation_y]
    type = ConstantFunction
    value = 0.0
  []
  [rod_stage_translation_z]
    type = ConstantFunction
    value = 0.0
  []
[]

[Variables]
  [Ux]
    order = FIRST
    family = LAGRANGE
  []
  [Uy]
    order = FIRST
    family = LAGRANGE
  []
  [Uz]
    order = FIRST
    family = LAGRANGE
  []
  [T]
    order = FIRST
    family = LAGRANGE
    initial_condition = 293.15
  []
[]

[Problem]
  extra_tag_vectors = 'reaction'
[]

[Physics/SolidMechanics/QuasiStatic]
  displacements = 'Ux Uy Uz'
  [all]
    displacements = 'Ux Uy Uz'
    strain = FINITE
    eigenstrain_names = thermal_eigenstrain
    temperature = T
    decomposition_method = HughesWinget
    volumetric_locking_correction = false
    add_variables = false
    extra_vector_tags = 'reaction'
    block = 'plate rod'
    generate_output = 'stress_xx stress_yy stress_zz stress_xy stress_yz stress_zx vonmises_stress plastic_strain_xx plastic_strain_yy plastic_strain_zz plastic_strain_xy plastic_strain_yz plastic_strain_zx strain_xx strain_yy strain_zz'
  []
[]

[AuxVariables]
  [tool_center_y]
    order = FIRST
    family = LAGRANGE
  []
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
  [spindle_reaction_x]
    order = FIRST
    family = LAGRANGE
  []
  [spindle_reaction_y]
    order = FIRST
    family = LAGRANGE
  []
  [spindle_reaction_z]
    order = FIRST
    family = LAGRANGE
  []
  [negative_contact_heat_power]
    order = FIRST
    family = LAGRANGE
  []
[]

[Kernels]
  [heat_time]
    block = 'plate rod'
    type = HeatConductionTimeDerivative
    variable = T
    density_name = density
    specific_heat = specific_heat
  []
  [heat_conduction]
    block = 'plate rod'
    type = HeatConduction
    variable = T
    thermal_conductivity = thermal_conductivity
  []
  [plastic_heat]
    type = NonnegativePlasticHeatEnergy
    variable = T
    displacements = 'Ux Uy Uz'
    coeff = 0.90
    block = 'plate rod'
  []
[]

[NodalKernels]
  [friction_heat_nodal]
    type = CoupledForceNodalKernel
    variable = T
    v = friction_heat
    boundary = workpiece_top
    coef = 1
  []
[]

[AuxKernels]
  [tool_center_y_aux]
    type = FunctionAux
    variable = tool_center_y
    function = rod_stage_center_y
    execute_on = 'INITIAL TIMESTEP_BEGIN NONLINEAR TIMESTEP_END'
  []
  [mushy_aux]
    type = ParsedAux
    variable = mushy_fraction
    coupled_variables = 'T'
    expression = 'if(T <= 623.15, 0.0, if(T >= 798.15, 1.0, (T - 623.15) / 175.0))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []
  [friction_heat_aux]
    type = PenaltyContactHeatPowerAux
    variable = friction_heat
    boundary = workpiece_top
    paired_boundary = rod_bottom
    contact_stiffness = ${Contact/rod_plate/penalty}
    efficiency = 0.9
    execute_on = 'NONLINEAR TIMESTEP_END'
  []
  [spindle_reaction_x_aux]
    type = ReactionForceAux
    block = 'plate rod'
    variable = spindle_reaction_x
    v = Ux
    vector_tag = reaction
  []
  [spindle_reaction_y_aux]
    type = ReactionForceAux
    block = 'plate rod'
    variable = spindle_reaction_y
    v = Uy
    vector_tag = reaction
  []
  [spindle_reaction_z_aux]
    type = ReactionForceAux
    block = 'plate rod'
    variable = spindle_reaction_z
    v = Uz
    vector_tag = reaction
  []
  [negative_contact_heat_power]
    type = PenaltyContactHeatPowerAux
    variable = negative_contact_heat_power
    boundary = workpiece_top
    paired_boundary = rod_bottom
    contact_stiffness = ${Contact/rod_plate/penalty}
    efficiency = 0.9
    report_negative = true
    execute_on = 'NONLINEAR TIMESTEP_END'
  []
[]

[Materials]
  [aa5083_k]
    block = 'plate rod'
    type = ParsedMaterial
    property_name = thermal_conductivity
    coupled_variables = 'T'
    expression = '122.0 + 0.08 * (T - 293.15)'
  []
  [aa5083_rho]
    block = 'plate rod'
    type = ParsedMaterial
    property_name = density
    coupled_variables = 'T'
    expression = '2650.0'
  []
  [aa5083_cp]
    block = 'plate rod'
    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = '900.0 + 0.45 * (T - 293.15)'
  []
  [thermal_expansion]
    type = ComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 2.38e-5
    temperature = T
    stress_free_temperature = 293.15
    eigenstrain_name = thermal_eigenstrain
    block = 'plate rod'
  []
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
    block = 'plate rod'
  []
  [temp_dep_hardening]
    type = RemeshTemperatureDependentHardeningStressUpdate
    hardening_functions = 'hf_293K hf_450K hf_623K hf_723K hf_798K hf_850K'
    temperatures = '293.15 450.0 623.15 723.15 798.15 850.0'
    temperature = T
    relative_tolerance = 1.0e-8
    absolute_tolerance = 1.0e-4
    max_inelastic_increment = 1.0e-2
    output_properties = 'effective_plastic_strain'
    outputs = exodus
    block = 'plate rod'
  []
  [radial_return_stress]
    type = ComputeMultipleInelasticStress
    tangent_operator = nonlinear
    inelastic_models = 'temp_dep_hardening'
    block = 'plate rod'
  []
  [plastic_work]
    type = ComputePlasticHeatEnergy
    block = 'plate rod'
  []
[]

[Contact]
  [rod_plate]
    primary = rod_bottom
    secondary = workpiece_top
    model = coulomb
    formulation = penalty
    displacements = 'Ux Uy Uz'
    friction_coefficient = 0.35
    penalty = 1.0e7
  []
[]

[Constraints]
  [thermal_contact_transfer]
    type = AFSDConservativeContactHeat
    primary_boundary = workpiece_top
    secondary_boundary = rod_bottom
    primary_subdomain = thermal_primary
    secondary_subdomain = thermal_secondary
    variable = T
    conductance = 1.0e7
  []
[]

[BCs]
  [fix_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'workpiece_base'
    value = 0.0
  []
  [fix_bottom_y]
    type = DirichletBC
    variable = Uy
    boundary = 'workpiece_base'
    value = 0.0
  []
  [fix_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'workpiece_base'
    value = 0.0
  []
  [rod_top_x]
    type = FunctionDirichletBC
    variable = Ux
    boundary = 'rod_top'
    function = rod_spin_ux
  []
  [rod_top_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'rod_top'
    function = rod_spin_uy
  []
  [rod_top_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_top'
    function = rod_stage_translation_z
  []
  [plate_base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'workpiece_base'
    T_infinity = 293.15
    coefficient = 250.0
  []
  [convective_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'workpiece_top rod_top'
    T_infinity = 293.15
    coefficient = 25.0
  []
[]

[Postprocessors]
  [T_min]
    type = NodalExtremeValue
    variable = T
    value_type = min
  []
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  [rod_max_vonmises_stress]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
    block = 'rod'
  []
  [max_effective_plastic_strain]
    type = ElementExtremeValue
    variable = effective_plastic_strain
    value_type = max
    block = 'plate rod'
  []
  [max_contact_pressure]
    type = NodalExtremeValue
    variable = contact_pressure
    value_type = max
  []
  [friction_power_W]
    type = NodalSum
    variable = friction_heat
    boundary = workpiece_top
  []
  [spindle_reaction_x_N]
    type = NodalSum
    variable = spindle_reaction_x
    boundary = rod_top
  []
  [spindle_reaction_y_N]
    type = NodalSum
    variable = spindle_reaction_y
    boundary = rod_top
  []
  [spindle_reaction_z_N]
    type = NodalSum
    variable = spindle_reaction_z
    boundary = rod_top
  []
  [spindle_torque_Nm]
    type = MovingAxisTorqueReaction
    boundary = rod_top
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
  petsc_options_iname = '-ksp_type -pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'gmres lu mumps'
  line_search = 'bt'
  nl_rel_tol = 1.0e-7
  nl_abs_tol = 1.0e-8
  l_tol = 1.0e-6
  l_max_its = 100
  nl_max_its = 40
  start_time = 0.0
  end_time = 0.000075
  dtmin = 1.0e-6
  dtmax = 2.5e-05
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 2.5e-05
  []
[]

[Outputs]
  [exodus]
    type = Exodus
    file_base = dwell_out
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [csv]
    type = CSV
    file_base = dwell_out
  []
[]
