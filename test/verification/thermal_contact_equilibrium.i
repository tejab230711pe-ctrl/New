# Partial footprint: uniform temperature must remain uniform with no sources.
[Mesh]
 [lower]
  type = GeneratedMeshGenerator
  dim = 3
  nx = 4
  ny = 4
  nz = 2
 []
 [lower_id]
  type = SubdomainIDGenerator
  input = lower
  subdomain_id = 0
 []
 [upper]
  type = GeneratedMeshGenerator
  dim = 3
  nx = 2
  ny = 2
  nz = 2
  xmin = 0.25
  xmax = 0.75
  ymin = 0.25
  ymax = 0.75
  zmin = 1.00001
  zmax = 1.5
 []
 [upper_id]
  type = SubdomainIDGenerator
  input = upper
  subdomain_id = 1
 []
 [combine]
  type = CombinerGenerator
  inputs = 'lower_id upper_id'
 []
 [names]
  type = RenameBlockGenerator
  input = combine
  old_block = '0 1'
  new_block = 'lower upper'
 []
 [boundaries]
  type = BreakBoundaryOnSubdomainGenerator
  input = names
 []
[]
[Variables]
 [T]
  initial_condition = 293.15
 []
[]
[Kernels]
 [time]
  type = HeatConductionTimeDerivative
  variable = T
 []
 [conduction]
  type = HeatConduction
  variable = T
 []
[]
[Materials]
 [properties]
  type = GenericConstantMaterial
  prop_names = 'thermal_conductivity density specific_heat'
  prop_values = '1 1 1'
 []
[]
[ThermalContact]
 [interface]
  type = GapHeatTransfer
  variable = T
  primary = back_to_upper
  secondary = front_to_lower
  gap_conductance = 1000
  quadrature = true
 []
[]
[Postprocessors]
 [minimum]
  type = NodalExtremeValue
  variable = T
  value_type = min
 []
 [maximum]
  type = NodalExtremeValue
  variable = T
  value_type = max
 []
[]
[Executioner]
 type = Transient
 num_steps = 1
 dt = 0.001
 solve_type = NEWTON
 nl_abs_tol = 1e-10
 nl_rel_tol = 1e-10
 petsc_options_iname = '-pc_type'
 petsc_options_value = 'lu'
[]
[Outputs]
 csv = true
[]
