[GlobalParams]
  displacements = 'Ux Uy Uz'
[]

[Mesh]
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 6
    ny = 10
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
    nz = 6
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

  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_nodes'
  []
[]

[Variables]
  [Ux]
  []
  [Uy]
  []
  [Uz]
  []
[]

[Functions]
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 5.6, 0.0, if(t < 45.6, 0.005 * (t - 5.6), 0.200))'
  []
  # Bottom tip of consumable rod: plunges 5mm at approach, dwells/traverses at contact z=20mm, retracts 5mm
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 45.6, -0.005, if(t < 48.0, -0.005 * (1.0 - (t - 45.6)/2.4), 0.0)))'
  []
  # Top feed end of consumable rod: continuous downward axial feed reduces rod height from 50mm to 15mm
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 5.6, -0.005 - 0.003 * (t - 1.6) / 4.0, if(t < 45.6, -0.008 - 0.032 * (t - 5.6) / 40.0, -0.040 + 0.005 * min(1.0, (t - 45.6)/2.4))))'
  []
[]

[Kernels]
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

[Materials]
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

  # Rod kinematics
  [rod_move_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'rod_boundary'
    function = rod_motion_y
  []
  [rod_move_x]
    type = DirichletBC
    variable = Ux
    boundary = 'rod_boundary'
    value = 0.0
  []
  [rod_bottom_z_bc]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_bottom'
    function = rod_motion_z_bottom
  []
  [rod_top_z_bc]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_top'
    function = rod_motion_z_top
  []
[]

[Executioner]
  type = Transient
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  start_time = 0.0
  end_time = 6.0
  dt = 1.0
[]

[Outputs]
  exodus = true
  file_base = scratch/test_rod_deformation_out
[]
