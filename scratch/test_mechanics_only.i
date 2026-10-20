# Task 2.1: Test mechanics-only (rod block) with J2 plasticity and HughesWinget
[Mesh]
  [rod_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 4
    nz = 8
    xmin = -0.0125
    xmax =  0.0125
    ymin = -0.0125
    ymax =  0.0125
    zmin =  0.000
    zmax =  0.050
  []
  [rod_id]
    type = SubdomainBoundingBoxGenerator
    input = rod_mesh
    bottom_left = '-0.0125 -0.0125 0.000'
    top_right = '0.0125 0.0125 0.050'
    block_id = 1
    block_name = 'rod'
  []
  [break_boundary]
    type = BreakBoundaryOnSubdomainGenerator
    input = rod_id
  []
[]

[Variables]
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

[Functions]
  # Top actuator feeds downward from 0 to -15 mm (30% compressive strain)
  [actuator_feed]
    type = ParsedFunction
    expression = '-0.015 * min(1.0, t / 10.0)'
  []

  # Hot softened AA5083 hardening curve (450 °C / 723 K)
  [hf_hot]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00 2.00 5.00'
    y = '52.0e6 56.0e6 62.0e6 69.0e6 76.0e6 82.0e6 85.0e6 90.0e6 95.0e6'
  []
[]

[Physics/SolidMechanics/QuasiStatic]
  displacements = 'Ux Uy Uz'
  [all]
    displacements = 'Ux Uy Uz'
    strain = FINITE
    decomposition_method = HughesWinget
    volumetric_locking_correction = false
    add_variables = false
    generate_output = 'stress_zz vonmises_stress plastic_strain_zz'
  []
[]

[Materials]
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
  []
  [hardening]
    type = IsotropicPlasticityStressUpdate
    hardening_function = hf_hot
    yield_stress = 52.0e6
    relative_tolerance = 1.0e-6
    absolute_tolerance = 1.0e-3
  []
  [radial_return_stress]
    type = ComputeMultipleInelasticStress
    tangent_operator = nonlinear
    inelastic_models = 'hardening'
  []
[]

[BCs]
  # Bottom face resting on plate (z = 0: back_to_rod)
  [rod_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'back_to_rod'
    value = 0.0
  []

  # Top face fed downward by actuator (z = 0.050: front_to_rod)
  [rod_top_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'front_to_rod'
    function = actuator_feed
  []

  # Symmetry planes or center pin to eliminate rigid body modes without locking lateral plastic flow:
  # x = 0 plane (rod_left is at x = -0.0125, rod_right at +0.0125)
  # For this test, fix Ux on rod_left and rod_right symmetrically or pin a point
  [pin_center_x]
    type = DirichletBC
    variable = Ux
    boundary = 'left_to_rod'
    value = 0.0
  []
  [pin_center_y]
    type = DirichletBC
    variable = Uy
    boundary = 'bottom_to_rod'
    value = 0.0
  []
[]

[Postprocessors]
  [sigma_vm_max]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
  []
  [Uz_top]
    type = PointValue
    variable = Uz
    point = '0.0 0.0 0.050'
  []
  [plastic_strain_max]
    type = ElementExtremeValue
    variable = plastic_strain_zz
    value_type = min
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'
  line_search = 'none'

  nl_rel_tol = 1.0e-4
  nl_abs_tol = 1.0e-1
  l_tol = 1.0e-4

  start_time = 0.0
  end_time = 10.0
  dt = 0.5
  dtmin = 0.01
  dtmax = 1.0

  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 0.5
    optimal_iterations = 6
    iteration_window = 2
    growth_factor = 1.25
    cutback_factor = 0.5
  []
[]

[Outputs]
  csv = true
  file_base = scratch/test_mechanics_out
[]
