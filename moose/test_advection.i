[Mesh]
  [gmg]
    type = GeneratedMeshGenerator
    dim = 2
    nx = 2
    ny = 2
  []
[]

[Variables]
  [c]
  []
  [velocity]
    family = LAGRANGE_VEC
  []
[]

[Kernels]
  [time]
    type = TimeDerivative
    variable = c
  []
  [vel_time]
    type = VectorTimeDerivative
    variable = velocity
  []
  [adv]
    type = ADConservativeAdvection
    variable = c
    velocity = velocity
  []
[]

[Executioner]
  type = Transient
  num_steps = 1
[]
