# Solved penalty-contact heating qualification variant.
# Heat = eta * tangential force dot irreversible slip / dt, in nodal watts.
# Recoverable tangential penalty-spring motion is excluded; negative discarded
# power is reported explicitly. All heat enters the secondary side; gap transfer
# couples the bodies. Heat partition and total energy closure require verification.
# Only fixed unnormalized penalty is supported. Do not override heat stiffness
# independently of Contact/rod_plate/penalty or change the contact formulation.

[Mesh]
  [file_mesh]
    type = FileMeshGenerator
    file = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/confirmed_geometry/dwell.msh
  []
  parallel_type = distributed
  patch_update_strategy = iteration
  displacements = 'Ux Uy Uz'
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
    y = '12.0e6 13.0e6 14.5e6 15.8e6 16.9e6 17.6e6 18.0e6 19.0e6 20.0e6'
  []

  [rod_stage_translation_y]
    type = ConstantFunction
    value = 0.0
  []
  [rod_stage_translation_z]
    type = ConstantFunction
    value = 0.0
  []
  [rod_stage_center_y]
    type = ConstantFunction
    value = 0.0125
  []
[]

[Variables]
  [T]
    order = FIRST
    family = LAGRANGE
    initial_condition = 293.15
  []
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
  [aa5083_properties]
    type = AA5083ThermalProperties
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
  [tool_rpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
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
  [is_deposited]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [rod_height_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 200.0
  []
  [consumed_length_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [axial_feed_rate_mmpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [zener_hollomon_lnZ]
    order = FIRST
    family = LAGRANGE
    initial_condition = 55.0
  []
  [negative_contact_heat_power]
    order = FIRST
    family = LAGRANGE
  []
[]

[Kernels]
  [heat_time]
    type = HeatConductionTimeDerivative
    variable = T
    density_name = density
    specific_heat = specific_heat
  []
  [heat_conduction]
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

[AuxKernels]
  [tool_center_y_aux]
    type = FunctionAux
    variable = tool_center_y
    function = rod_stage_center_y
    execute_on = 'INITIAL TIMESTEP_BEGIN NONLINEAR TIMESTEP_END'
  []
  [tool_rpm_aux]
    type = ParsedAux
    variable = tool_rpm
    use_xyzt = true
    expression = 'if(t <= 32.0, 1200.0, 0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
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

  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    use_xyzt = true
    block = 'rod'
    coupled_variables = 'T contact_pressure is_deposited tool_center_y'
    expression = 'if(is_deposited > 0.5, 1.0,
                    if(t >= 4.0 & contact_pressure >= 2.5e5 & T >= 623.15 & T <= 798.15 &
                       y <= (tool_center_y + 0.0125),
                       1.0, 0.0))'
    execute_on = 'TIMESTEP_END'
  []

  [rod_height_aux]
    type = FunctionAux
    variable = rod_height_mm
    function = rod_height_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  [consumed_length_aux]
    type = FunctionAux
    variable = consumed_length_mm
    function = rod_consumed_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  [axial_feed_rate_aux]
    type = FunctionAux
    variable = axial_feed_rate_mmpm
    function = axial_feed_rate_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []


  [zener_hollomon_aux]
    type = ParsedAux
    variable = zener_hollomon_lnZ
    coupled_variables = 'T'
    expression = '7.313 + 145000.0 / (8.314 * max(300.0, T))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
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
    type = ParsedMaterial
    property_name = thermal_conductivity
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 112.5 + (122.7 - 112.5)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 122.7 + (142.3 - 122.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 142.3 + (177.2 - 142.3)*((T - 273.15) - 280.0)/300.0, 177.2)))'
  []

  [aa5083_rho]
    type = ParsedMaterial
    property_name = density
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 2673.9 + (2642.7 - 2673.9)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 2642.7 + (2611.5 - 2642.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 2611.5 + (2549.2 - 2611.5)*((T - 273.15) - 280.0)/300.0, 2549.2)))'
  []

  [aa5083_cp]
    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 924.1 + (984.2 - 924.1)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 984.2 + (1081.2 - 984.2)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))'
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
    penalty = 10000000.0
  []
[]

[Dampers]
  inactive = 'rod_plate_slip'
  [rod_plate_slip]
    type = ContactSlipDamper
    primary = 'rod_bottom'
    secondary = 'workpiece_top'
    max_iterative_slip = 5.0e-4
    min_damping_factor = 0.05
  []
[]

[ThermalContact]
  [rod_plate]
    type = GapHeatTransfer
    quadrature = true
    variable = T
    primary = rod_bottom
    secondary = workpiece_top
    displacements = 'Ux Uy Uz'
    gap_conductance = 10000000.0
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
  [T_min]
    type = NodalExtremeValue
    variable = T
    value_type = min
  []
  [T_mean]
    type = ElementAverageValue
    variable = T
  []
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  [T_core]
    type = PointValue
    variable = T
    point = '0.0 0.0125 0.009'
  []
  [rod_max_vonmises_stress]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
    block = 'rod'
  []
  [rod_avg_vonmises_stress]
    type = ElementAverageValue
    variable = vonmises_stress
    block = 'rod'
  []
  [rod_axial_stress_zz]
    type = ElementAverageValue
    variable = stress_zz
    block = 'rod'
  []
  [rod_max_plastic_strain_zz]
    type = ElementExtremeValue
    variable = plastic_strain_zz
    value_type = min
    block = 'rod'
  []
  [max_effective_plastic_strain]
    type = ElementExtremeValue
    variable = effective_plastic_strain
    value_type = max
    block = 'plate rod'
  []
  [rod_avg_plastic_strain_zz]
    type = ElementAverageValue
    variable = plastic_strain_zz
    block = 'rod'
  []
  [max_contact_pressure]
    type = NodalExtremeValue
    variable = contact_pressure
    value_type = max
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
    reaction_force_variables = 'spindle_reaction_x spindle_reaction_y spindle_reaction_z'
    center_y = rod_stage_center_y
    direction_vector = '0 0 1'
  []
  [current_rpm]
    type = AverageNodalVariableValue
    variable = tool_rpm
  []
  [friction_power_W]
    type = NodalSum
    variable = friction_heat
    boundary = workpiece_top
  []
  [friction_power_kW]
    type = ParsedPostprocessor
    pp_names = 'friction_power_W'
    expression = 'friction_power_W / 1000.0'
  []
  [power_kW]
    type = ParsedPostprocessor
    pp_names = 'spindle_torque_Nm'
    expression = 'spindle_torque_Nm * 1200.0 * 2.0 * 3.14159265 / (60.0 * 1000.0)'
  []
  [force_kN]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_z_N'
    expression = 'abs(spindle_reaction_z_N) / 1000.0'
  []
  [deposited_bead_pct]
    type = ElementAverageValue
    variable = is_deposited
    block = 'rod'
  []
  [rod_height_mm]
    type = ElementAverageValue
    variable = rod_height_mm
    block = 'rod'
  []
  [consumed_length_mm]
    type = ElementAverageValue
    variable = consumed_length_mm
    block = 'rod'
  []
  [feed_rate_mmpm]
    type = ElementAverageValue
    variable = axial_feed_rate_mmpm
    block = 'rod'
  []
  [traverse_force_N]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_y_N'
    expression = '-spindle_reaction_y_N'
  []
  [transverse_force_N]
    type = ParsedPostprocessor
    pp_names = 'spindle_reaction_x_N'
    expression = '-spindle_reaction_x_N'
  []
  [ln_Zener_Hollomon]
    type = ElementAverageValue
    variable = zener_hollomon_lnZ
    block = 'rod'
  []
  [discarded_negative_contact_power_W]
    type = NodalSum
    variable = negative_contact_heat_power
    boundary = workpiece_top
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
    optimal_iterations = 8
    iteration_window = 4
    growth_factor = 1.25
    cutback_factor = 0.5
    cutback_factor_at_failure = 0.25
  []
[]

[Outputs]
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
    file_base = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/confirmed_geometry_3steps/dwell
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [csv]
    type = CSV
    file_base = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/confirmed_geometry_3steps/dwell
  []
[]

[NodalKernels]
  [solved_contact_heat]
    type = CoupledForceNodalKernel
    variable = T
    v = friction_heat
    boundary = workpiece_top
    coef = 1
  []
[]
