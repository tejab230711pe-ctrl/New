# Uniform 0.01 K heating of a 10 mm elastic cube.
# Small temperature increment makes the linear analytical reference applicable
# to this FINITE-strain regression with relative tolerance 1e-5.
[Mesh]
  type = GeneratedMesh
  dim = 3
  nx = 2
  ny = 2
  nz = 2
  xmax = 0.01
  ymax = 0.01
  zmax = 0.01
[]
[GlobalParams]
  displacements = 'ux uy uz'
[]
[AuxVariables]
  [T]
    initial_condition = 293.16
  []
[]
[Physics/SolidMechanics/QuasiStatic]
  [all]
    strain = FINITE
    decomposition_method = HughesWinget
    add_variables = true
    eigenstrain_names = thermal_eigenstrain
    temperature = T
    generate_output = 'stress_xx stress_yy stress_zz'
  []
[]
[Materials]
  [elasticity]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
  []
  [thermal_expansion]
    type = ComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 2.38e-5
    temperature = T
    stress_free_temperature = 293.15
    eigenstrain_name = thermal_eigenstrain
  []
  [stress]
    type = ComputeFiniteStrainElasticStress
  []
[]
[BCs]
  [x]
    type = DirichletBC
    variable = ux
    boundary = left
    value = 0
  []
  [y]
    type = DirichletBC
    variable = uy
    boundary = bottom
    value = 0
  []
  [z]
    type = DirichletBC
    variable = uz
    boundary = back
    value = 0
  []
[]
[Postprocessors]
  [ux_right]
    type = SideAverageValue
    variable = ux
    boundary = right
  []
  [uy_top]
    type = SideAverageValue
    variable = uy
    boundary = top
  []
  [uz_front]
    type = SideAverageValue
    variable = uz
    boundary = front
  []
  [sxx]
    type = ElementAverageValue
    variable = stress_xx
  []
  [syy]
    type = ElementAverageValue
    variable = stress_yy
  []
  [szz]
    type = ElementAverageValue
    variable = stress_zz
  []
[]
[Executioner]
  type = Transient
  solve_type = NEWTON
  num_steps = 1
  dt = 1
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu petsc'
[]
[Outputs]
  csv = true
[]
