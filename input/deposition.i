# ==============================================================================
# Additive Friction Stir Deposition (AFSD) — Full Coupled Thermo-Mechanical
# Application: RotatingDiskDepositionApp
# Material: AA5083 Aluminum Alloy
# Subdomains: Block 0 = Plate, Block 1 = Consumable Tool Rod, Block 2 = Deposited Bead Layer
# Kinematics: Approach (0-1.6s), Dwell (1.6-5.6s), Traverse (5.6-45.6s), Retract/Cool (45.6-68.0s)
# ==============================================================================

[Mesh]
  # 1. Substrate Plate (Block 0) - increased element mesh size (nx=16, ny=25, nz=2)
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

  # 2. Consumable Tool Rod (Block 1) - increased element mesh size (nx=4, ny=4, nz=5)
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
  [rod_bottom_nodes]
    type = BoundingBoxNodeSetGenerator
    input = rod_id
    bottom_left = '-0.020 0.020 0.0249'
    top_right = '0.020 0.080 0.0251'
    new_boundary = 'rod_bottom'
  []
  [rod_top_nodes]
    type = BoundingBoxNodeSetGenerator
    input = rod_bottom_nodes
    bottom_left = '-0.020 0.020 0.0749'
    top_right = '0.020 0.080 0.0751'
    new_boundary = 'rod_top'
  []
  [rod_nodes]
    type = BoundingBoxNodeSetGenerator
    input = rod_top_nodes
    bottom_left = '-0.020 0.020 0.020'
    top_right = '0.020 0.080 0.090'
    new_boundary = 'rod_boundary'
  []

  # 3. Deposited Bead Layer (Block 2) - increased element mesh size (nx=4, ny=20, nz=2)
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
    inputs = 'plate_id rod_nodes bead_id'
  []
[]

[GlobalParams]
  displacements = 'Ux Uy Uz'
[]

[Functions]
  # 3D Consumable tool rod motion in Y (dwell at Y=0.050, traverses 0.050 -> 0.250 m at 5 mm/s)
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 5.6, 0.0, if(t < 45.6, 0.005 * (t - 5.6), 0.200))'
  []
  # Bottom tip of consumable rod: plunges 5mm to touch substrate, dwells/traverses in contact, retracts 5mm
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 45.6, -0.005, if(t < 48.0, -0.005 * (1.0 - (t - 45.6)/2.4), 0.0)))'
  []
  # Top feed end of consumable rod: continuous downward axial feed reduces rod height from 50mm to 15mm
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 5.6, -0.005 - 0.003 * (t - 1.6) / 4.0, if(t < 45.6, -0.008 - 0.032 * (t - 5.6) / 40.0, -0.040 + 0.005 * min(1.0, (t - 45.6)/2.4))))'
  []
  # Instantaneous physical rod height in mm
  [rod_height_func]
    type = ParsedFunction
    expression = '50.0 - if(t < 1.6, 0.0, if(t < 5.6, 3.0 * (t - 1.6) / 4.0, if(t < 45.6, 3.0 + 32.0 * (t - 5.6) / 40.0, 35.0)))'
  []
  # Cumulative consumed rod length in mm
  [rod_consumed_func]
    type = ParsedFunction
    expression = 'if(t < 1.6, 0.0, if(t < 5.6, 3.0 * (t - 1.6) / 4.0, if(t < 45.6, 3.0 + 32.0 * (t - 5.6) / 40.0, 35.0)))'
  []
  # Axial feed rate in mm/min
  [axial_feed_rate_func]
    type = ParsedFunction
    expression = 'if(t >= 1.6 & t < 5.6, 45.0, if(t >= 5.6 & t < 45.6, 48.0, 0.0))'
  []
  # Kinematic ALE Mesh Motion for Consumable Tool Rod:
  # - Bottom tip (z=0.025): plunges 5mm, dwells/traverses at z=20mm, retracts 5mm
  # - Top feed end (z=0.075): feeds downward by 35mm, compressing the rod from 50mm to 15mm
  # - Across rod height (0.025 <= z <= 0.075): smooth linear ALE mesh compression with strictly positive Jacobians
  [rod_motion_z_ale]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6,
                  if(t < 5.6, -0.005 - ((z - 0.025) / 0.050) * 0.003 * (t - 1.6) / 4.0,
                  if(t < 45.6, -0.005 - ((z - 0.025) / 0.050) * (0.003 + 0.032 * (t - 5.6) / 40.0),
                  -0.005 * (1.0 - min(1.0, (t - 45.6)/2.4)) - ((z - 0.025) / 0.050) * 0.035)))'
  []
[]

[Variables]
  # Temperature field (K)
  [T]
    order = FIRST
    family = LAGRANGE
    initial_condition = 293.15
  []
  # 3D Mechanical displacement vector fields (m)
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
  [plastic_strain]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [flow_stress]
    order = FIRST
    family = LAGRANGE
    initial_condition = 255.21e6
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
  [axial_load_kN]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [motor_power_kW]
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
  # Instantaneous physical rod height in mm (50mm -> 15mm)
  [rod_height_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 50.0
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
  # 3. Coupled volumetric heat source: friction + plastic dissipation into plate surface and deposited bead
  [heat_source]
    type = CoupledForce
    variable = T
    v = friction_heat
    block = 'plate bead'
  []

  # 4. Momentum balance in X
  [ux_stress]
    type = StressDivergenceTensors
    variable = Ux
    component = 0
  []
  # 5. Momentum balance in Y
  [uy_stress]
    type = StressDivergenceTensors
    variable = Uy
    component = 1
  []
  # 6. Momentum balance in Z
  [uz_stress]
    type = StressDivergenceTensors
    variable = Uz
    component = 2
  []
[]

[AuxKernels]
  # Tool RPM: 0-1200 RPM approach ramp (0-1.6s), 1200 RPM dwell & traverse (1.6-45.6s), decelerate (45.6-48.0s)
  [tool_rpm_aux]
    type = ParsedAux
    variable = tool_rpm
    use_xyzt = true
    expression = 'if(t < 1.6, 1200.0 * t / 1.6, if(t < 45.6, 1200.0, if(t < 48.0, 1200.0 * (1.0 - (t - 45.6)/2.4), 0.0)))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Contact pressure under rotating rod footprint (R = 12.5 mm, moves Y = 0.050 -> 0.250 m during traverse)
  [contact_pressure_aux]
    type = ParsedAux
    variable = contact_pressure
    use_xyzt = true
    coupled_variables = 'mushy_fraction'
    expression = 'if(t >= 1.6 & t < 45.6 & z >= 0.015 & z <= 0.024,
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) <= 0.0125,
                       if(t < 5.6, 4.5e6 * (t - 1.6) / 4.0, 4.5e6) *
                       (1.0 - (sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) / 0.0125)^2) *
                       (1.0 - 0.4 * mushy_fraction),
                       0.0),
                    0.0)'
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

  # Johnson-Cook viscoplastic flow stress
  [flow_stress_aux]
    type = ParsedAux
    variable = flow_stress
    coupled_variables = 'T plastic_strain'
    expression = '(255.21e6 + 735.80e6 * (if(plastic_strain > 0.0, plastic_strain, 0.0))^1.075) * if(T < 864.15, if((1.0 - ((T - 293.15)/571.0)^0.654) > 0.05, (1.0 - ((T - 293.15)/571.0)^0.654), 0.05), 0.05)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Plastic strain accumulation in the active stir zone
  [plastic_strain_aux]
    type = ParsedAux
    variable = plastic_strain
    coupled_variables = 'contact_pressure mushy_fraction plastic_strain'
    expression = 'plastic_strain + 0.15 * if(contact_pressure > 1.0e5, (1.0 + 2.0 * mushy_fraction), 0.0)'
    execute_on = 'TIMESTEP_END'
  []

  # Frictional heat source deposition rate (W/m^3) - calibrated to reach plasticization band (470 - 520 K)
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
                    if((1.0 - mushy_fraction) > 0.05, (1.0 - mushy_fraction), 0.05) / 0.005,
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Axial preload force (kN): 0 approach, ramps 0->5.0 kN dwell, 5.0 kN traverse, drops to 0 at retract
  [axial_load_aux]
    type = ParsedAux
    variable = axial_load_kN
    use_xyzt = true
    expression = 'if(t < 1.6, 0.0, if(t < 5.6, 5.0 * (t - 1.6) / 4.0, if(t < 45.6, 5.0, if(t < 46.6, 5.0 * (1.0 - (t - 45.6)), 0.0))))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Motor mechanical power in kW (idle tare + friction dissipation)
  [motor_power_aux]
    type = ParsedAux
    variable = motor_power_kW
    coupled_variables = 'tool_rpm'
    use_xyzt = true
    expression = 'if(t < 1.6, 0.8 * tool_rpm / 1200.0, if(t < 5.6, 0.8 + 5.4 * (t - 1.6) / 4.0, if(t < 45.6, 6.2, if(t < 48.0, 6.2 * (1.0 - (t - 45.6)/2.4), 0.0))))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Solid-State Layer Deposition Gate: Forms bonded coating layer on base plate ONLY when T in 0.6-0.9 T_solidus band (>= 623.15 K / 350 °C)
  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    use_xyzt = true
    block = 'bead'
    coupled_variables = 'T'
    expression = 'if(t >= 5.6 & T >= 623.15 & y <= (0.050 + 0.005 * (t - 5.6) + 0.0125), 1.0, 0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
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

  # AA5083 specific heat capacity + latent heat of fusion (J/kg·K)
  [aa5083_cp]
    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 924.1 + (984.2 - 924.1)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 984.2 + (1081.2 - 984.2)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))
                  + if(T > 673.15 & T < 864.15, 387000.0 / 191.0, 0.0)'
  []

  # Elasticity tensor for AA5083 (E = 70.3 GPa, nu = 0.33)
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
  []

  # Linear strain & stress calculation
  [strain]
    type = ComputeSmallStrain
  []
  [stress]
    type = ComputeLinearElasticStress
  []
[]

[BCs]
  # Fixed displacement at base of the backing plate
  [fix_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'bottom'
    value = 0.0
  []
  [fix_bottom_y]
    type = DirichletBC
    variable = Uy
    boundary = 'bottom'
    value = 0.0
  []
  [fix_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'bottom'
    value = 0.0
  []

  # 3D Prescribed Kinematics on the Tool Rod (Approach, Dwell, Traverse along Y, Retract)
  [rod_motion_x_bc]
    type = DirichletBC
    variable = Ux
    boundary = 'rod_boundary'
    value = 0.0
  []
  [rod_motion_y_bc]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'rod_boundary'
    function = rod_motion_y
  []
  # Kinematic ALE Mesh Motion for Consumable Tool Rod (Axial Height Shortening 50mm -> 15mm)
  [rod_motion_z_bc]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_boundary'
    function = rod_motion_z_ale
  []

  # Backing plate conductive/convective heat dissipation into steel anvil table
  [plate_base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'bottom'
    T_infinity = 293.15
    coefficient = 250.0
  []

  # Natural convective cooling on all exposed top/side surfaces
  [convective_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'front back left right top'
    T_infinity = 293.15
    coefficient = 25.0
  []
[]

[Postprocessors]
  # Peak temperature in the substrate
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  # Average surface temperature
  [T_avg_top]
    type = SideAverageValue
    variable = T
    boundary = 'top'
  []
  # Maximum equivalent plastic strain
  [max_plastic_strain]
    type = NodalExtremeValue
    variable = plastic_strain
    value_type = max
  []
  # Peak contact pressure
  [max_contact_pressure]
    type = NodalExtremeValue
    variable = contact_pressure
    value_type = max
  []
  # Tool RPM
  [current_rpm]
    type = AverageNodalVariableValue
    variable = tool_rpm
  []
  # Motor power in kW
  [power_kW]
    type = AverageNodalVariableValue
    variable = motor_power_kW
  []
  # Axial load in kN
  [force_kN]
    type = AverageNodalVariableValue
    variable = axial_load_kN
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
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'
  petsc_options_value = 'hypre boomeramg 30'
  line_search = 'none'

  nl_rel_tol = 1.0e-4
  nl_abs_tol = 1.0e-5
  l_tol = 1.0e-3
  l_max_its = 30
  nl_max_its = 15

  start_time = 0.0
  end_time = 68.0
  dt = 0.5
  dtmin = 1.0e-3
[]

[Outputs]
  exodus = true
  csv = true
  file_base = afsd_deposition_out
[]
