# Manufactured shear: momentum_y = -6 * d(mu)/dx. No transient solve.

[Mesh]
 type = GeneratedMesh
 dim = 3
 elem_type = TET4
[]
[Problem]
 solve = false
[]
[Executioner]
 type = Transient
 num_steps = 1
 dt = 1
[]
[Outputs]
 csv = true
[]

[Functions]
 [temperature]
  type = ParsedFunction
  expression = '723.15 + .001*x'
 []
 [vx]
  type = ParsedFunction
  expression = '6*y'
 []
[]
[Variables]
 [pressure]
 []
 [T]
 []
 [velocity]
  family = LAGRANGE_VEC
  order = FIRST
 []
[]
[AuxVariables]
 [momentum_y]
  family = MONOMIAL
  order = CONSTANT
 []
 [gradient]
  family = MONOMIAL
  order = CONSTANT
 []
[]
[ICs]
 [T]
  type = FunctionIC
  variable = T
  function = temperature
 []
 [velocity]
  type = VectorFunctionIC
  variable = velocity
  function_x = vx
  function_y = 0
  function_z = 0
 []
[]
[Materials]
 [stabilization]
  type = AFSDStabilized3Eqn
  velocity = velocity
  pressure = pressure
  temperature = T
 []
 [flow]
  type = AA5083ALEViscoplasticMaterial
  temperature = T
  velocity = velocity
  
 []
[]
[AuxKernels]
 [momentum_y]
  type = ADMaterialRealVectorValueAux
  variable = momentum_y
  property = momentum_strong_residual
  component = 1
 []
 [gradient]
  type = ADMaterialRealVectorValueAux
  variable = gradient
  property = grad_mu_temperature
  component = 0
 []
[]
[Postprocessors]
 [momentum_y]
  type = ElementAverageValue
  variable = momentum_y
 []
 [gradient]
  type = ElementAverageValue
  variable = gradient
 []
[]

[Kernels]
 [mass]
  type = INSADMass
  variable = pressure
 []
 [viscous]
  type = INSADMomentumViscous
  variable = velocity
  viscous_form = traction
 []
 [heat]
  type = ADHeatConduction
  variable = T
  thermal_conductivity = k
 []
[]
