# Test coupled thermo-mechanical simulation with clean boundaries
[Mesh]
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 8
    ny = 12
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

  [bead_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 10
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

  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_id bead_id'
  []

  [break_boundary]
    type = BreakBoundaryOnSubdomainGenerator
    input = combine
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

[Functions]
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 5.6, 0.0, if(t < 45.6, 0.005 * (t - 5.6), 0.200))'
  []
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 45.6, -0.005, if(t < 48.0, -0.005 * (1.0 - (t - 45.6)/2.4), 0.0)))'
  []
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 5.6, -0.005 - 0.003 * (t - 1.6) / 4.0, if(t < 45.6, -0.008 - 0.032 * (t - 5.6) / 40.0, -0.040 + 0.005 * min(1.0, (t - 45.6)/2.4))))'
  []

  # Hardening curves extended to 500% strain
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
[]

[Physics/SolidMechanics/QuasiStatic]
  displacements = 'Ux Uy Uz'
  [all]
    displacements = 'Ux Uy Uz'
    strain = FINITE
    decomposition_method = HughesWinget
    volumetric_locking_correction = true
    add_variables = false
    block = 'plate rod'
    generate_output = 'stress_xx stress_yy stress_zz vonmises_stress plastic_strain_xx plastic_strain_yy plastic_strain_zz'
  []
[]

[AuxVariables]
  [contact_pressure]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
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
  [is_deposited]
    order = CONSTANT
    family = MONOMIAL
    initial_condition = 0.0
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
  # Heat source applied to plate, rod, and bead!
  [heat_source]
    type = CoupledForce
    variable = T
    v = friction_heat
    block = 'plate rod bead'
  []
[]

[AuxKernels]
  [tool_rpm_aux]
    type = ParsedAux
    variable = tool_rpm
    use_xyzt = true
    expression = 'if(t < 1.6, 1200.0 * t / 1.6, if(t < 45.6, 1200.0, if(t < 48.0, 1200.0 * (1.0 - (t - 45.6)/2.4), 0.0)))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []
  [contact_pressure_aux]
    type = ParsedAux
    variable = contact_pressure
    use_xyzt = true
    coupled_variables = 'mushy_fraction'
    expression = 'if(t >= 1.6 & t < 45.6 & z >= 0.015 & z <= 0.035,
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) < 0.015,
                       if(t < 5.6, 4.5e6 * (t - 1.6) / 4.0, 4.5e6) *
                       (1.0 - (sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) / 0.015)^2)^2 *
                       (1.0 - 0.4 * mushy_fraction),
                       0.0),
                    0.0)'
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
    type = ParsedAux
    variable = friction_heat
    coupled_variables = 'T contact_pressure tool_rpm mushy_fraction'
    use_xyzt = true
    expression = 'if(contact_pressure > 1.0e4 & tool_rpm > 10.0,
                    2.2 * 0.85 * if((0.70 - 0.45 * (T - 293.15)/571.0) > 0.25, (0.70 - 0.45 * (T - 293.15)/571.0), 0.25) *
                    contact_pressure * (tool_rpm * 2.0 * 3.14159265 / 60.0) *
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) > 0.002,
                       sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2), 0.002) *
                    if((1.0 - mushy_fraction) > 0.05, (1.0 - mushy_fraction), 0.05) / 0.008,
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []
  # Dual-gate solid-state deposition (temperature 350-525 °C AND pressure >= 0.25 MPa)
  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    coupled_variables = 'T contact_pressure is_deposited'
    use_xyzt = true
    expression = 'if(is_deposited > 0.5, 1.0,
                    if(t >= 5.6 & contact_pressure >= 0.25e6 & T >= 623.15 & T <= 798.15 &
                       y <= (if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)) + 0.015),
                       1.0, 0.0))'
    execute_on = 'TIMESTEP_END'
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
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))
                  + if(T > 673.15 & T < 864.15, 387000.0 / 191.0, 0.0)'
  []
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
    block = 'plate rod'
  []
  [temp_dep_hardening]
    type = TemperatureDependentHardeningStressUpdate
    hardening_functions = 'hf_293K hf_450K hf_623K hf_723K hf_798K hf_850K'
    temperatures = '293.15 450.0 623.15 723.15 798.15 850.0'
    temperature = T
    relative_tolerance = 1.0e-6
    absolute_tolerance = 1.0e-3
    block = 'plate rod'
  []
  [radial_return_stress]
    type = ComputeMultipleInelasticStress
    tangent_operator = elastic
    inelastic_models = 'temp_dep_hardening'
    block = 'plate rod'
  []
[]

[BCs]
  # 1. Backing plate clamped to steel table at z = 0 (back_to_plate)
  [fix_plate_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'back_to_plate'
    value = 0.0
  []
  [fix_plate_bottom_y]
    type = DirichletBC
    variable = Uy
    boundary = 'back_to_plate'
    value = 0.0
  []
  [fix_plate_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'back_to_plate'
    value = 0.0
  []

  # 2. Tool rod TOP face (front_to_rod at z = 0.075)
  [rod_top_x]
    type = DirichletBC
    variable = Ux
    boundary = 'front_to_rod'
    value = 0.0
  []
  [rod_top_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'front_to_rod'
    function = rod_motion_y
  []
  [rod_top_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'front_to_rod'
    function = rod_motion_z_top
  []

  # 3. Tool rod BOTTOM face (back_to_rod at z = 0.025)
  [rod_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'back_to_rod'
    value = 0.0
  []
  [rod_bottom_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'back_to_rod'
    function = rod_motion_y
  []
  [rod_bottom_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'back_to_rod'
    function = rod_motion_z_bottom
  []

  # 4. Thermal BC: Anvil table heat dissipation at plate base (z = 0)
  [plate_base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'back_to_plate'
    T_infinity = 293.15
    coefficient = 250.0
  []

  # 5. Natural convective cooling on all outer exposed surfaces
  [convective_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'bottom_to_plate top_to_plate left_to_plate right_to_plate left_to_rod right_to_rod bottom_to_rod top_to_rod front_to_bead left_to_bead right_to_bead top_to_bead bottom_to_bead'
    T_infinity = 293.15
    coefficient = 25.0
  []
[]

[Postprocessors]
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  [T_rod_tip]
    type = PointValue
    variable = T
    point = '0.0 0.050 0.025'
  []
  [sigma_vm_max]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
  []
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'
  petsc_options_value = 'hypre boomeramg 100'
  line_search = 'none'

  nl_rel_tol = 1.0e-3
  nl_abs_tol = 1.0e-1
  l_tol = 1.0e-3
  l_max_its = 100
  nl_max_its = 30

  start_time = 0.0
  end_time = 15.0
  dt = 0.5
  dtmin = 0.05
  dtmax = 1.0
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 0.5
    optimal_iterations = 8
    iteration_window = 3
    growth_factor = 1.25
    cutback_factor = 0.5
  []
[]

[Outputs]
  csv = true
  file_base = scratch/test_coupled_out
[]
