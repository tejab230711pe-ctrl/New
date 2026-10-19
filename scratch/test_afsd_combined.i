# AFSD Multi-Block Test with Moving Rod and Deposited Bead

[Mesh]
  # 1. Substrate Plate (Block 0)
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 24
    ny = 40
    nz = 4
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

  # 2. Consumable Tool Rod (Block 1) - starts at Y=0.050, Z=0.025 (5mm clearance)
  [rod_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 6
    ny = 6
    nz = 8
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

  # 3. Deposited Bead Layer (Block 2) - sits on plate along traverse track
  [bead_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 6
    ny = 32
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

  # Combine all 3 distinct bodies into a single simulation mesh
  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_id bead_id'
  []
[]

[GlobalParams]
  displacements = 'Ux Uy Uz'
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
  []
  [Uy]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [Uz]
    order = FIRST
    family = LAGRANGE
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
  [heat_source]
    type = CoupledForce
    variable = T
    v = friction_heat
    block = 'plate bead'
  []

  [ux_stress]
    type = StressDivergenceTensors
    variable = Ux
    component = 0
  []
  [uy_stress]
    type = StressDivergenceTensors
    variable = Uy
    component = 1
  []
  [uz_stress]
    type = StressDivergenceTensors
    variable = Uz
    component = 2
  []
[]

[AuxVariables]
  [friction_heat]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [contact_pressure]
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
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
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
    expression = 'if(t >= 1.6 & t < 45.6 & z >= 0.0165 & z <= 0.024,
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) <= 0.0125,
                       if(t < 5.6, 4.5e6 * (t - 1.6) / 4.0, 4.5e6) *
                       (1.0 - (sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) / 0.0125)^2),
                       0.0),
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  [friction_heat_aux]
    type = ParsedAux
    variable = friction_heat
    coupled_variables = 'T contact_pressure tool_rpm'
    use_xyzt = true
    expression = 'if(contact_pressure > 1.0e4 & tool_rpm > 10.0,
                    4.0 * 0.85 * if((0.70 - 0.45 * (T - 293.15)/571.0) > 0.25, (0.70 - 0.45 * (T - 293.15)/571.0), 0.25) *
                    contact_pressure * (tool_rpm * 2.0 * 3.14159265 / 60.0) *
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) > 0.002,
                       sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2), 0.002) / 0.00333,
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Deposition Activation: Materializes layer when tool passes over and temperature exceeds plasticizing threshold
  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    coupled_variables = 'T is_deposited'
    use_xyzt = true
    block = 'bead'
    expression = 'if(is_deposited > 0.5, 1.0,
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) <= 0.0125 & T >= 400.0 & t >= 1.6,
                       1.0, 0.0))'
    execute_on = 'TIMESTEP_END'
  []
[]

[Materials]
  [density_mat]
    type = GenericConstantMaterial
    prop_names = 'density'
    prop_values = '2650.0'
  []
  [cp_mat]
    type = GenericConstantMaterial
    prop_names = 'specific_heat'
    prop_values = '950.0'
  []
  [k_mat]
    type = GenericConstantMaterial
    prop_names = 'thermal_conductivity'
    prop_values = '130.0'
  []
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
  []
  [strain]
    type = ComputeSmallStrain
  []
  [stress]
    type = ComputeLinearElasticStress
  []
[]

[BCs]
  # Fix base of plate
  [fix_plate_bottom]
    type = DirichletBC
    variable = Uz
    boundary = 'bottom'
    value = 0.0
  []
  [fix_plate_x]
    type = DirichletBC
    variable = Ux
    boundary = 'bottom'
    value = 0.0
  []
  [fix_plate_y]
    type = DirichletBC
    variable = Uy
    boundary = 'bottom'
    value = 0.0
  []

  # Cooling at base of plate
  [base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'bottom'
    T_infinity = 293.15
    coefficient = 250.0
  []
  [ambient_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'front back left right top'
    T_infinity = 293.15
    coefficient = 25.0
  []
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  start_time = 0.0
  end_time = 1.0
  dt = 0.5
[]

[Outputs]
  exodus = true
[]
