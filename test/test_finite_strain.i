# Test Finite Strain Syntax Check
[Mesh]
  type = GeneratedMeshGenerator
  dim = 3
  nx = 2
  ny = 2
  nz = 2
  xmin = 0.0
  xmax = 0.01
  ymin = 0.0
  ymax = 0.01
  zmin = 0.0
  zmax = 0.01
[]

[GlobalParams]
  displacements = 'Ux Uy Uz'
[]

[Variables]
  [Ux]
  []
  [Uy]
  []
  [Uz]
  []
[]

[Kernels]
  [ux_stress]
    type = StressDivergenceTensors
    variable = Ux
    component = 0
    use_displaced_mesh = true
  []
  [uy_stress]
    type = StressDivergenceTensors
    variable = Uy
    component = 1
    use_displaced_mesh = true
  []
  [uz_stress]
    type = StressDivergenceTensors
    variable = Uz
    component = 2
    use_displaced_mesh = true
  []
[]

[Materials]
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
  []
  [strain]
    type = ComputeFiniteStrain
  []
  [stress]
    type = ComputeFiniteStrainElasticStress
  []
[]

[BCs]
  [fix_z]
    type = DirichletBC
    variable = Uz
    boundary = 'bottom'
    value = 0.0
  []
[]

[Executioner]
  type = Transient
  num_steps = 1
  dt = 0.1
[]
