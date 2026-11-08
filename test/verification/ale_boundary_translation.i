# Manufactured translation: every mesh node must move at (1,2,3) m/s.
[Mesh]
 type = GeneratedMesh
 dim = 3
 nx = 1
 ny = 1
 nz = 1
 displacements = 'mx my mz'
[]
[Variables]
 [v]
  family = LAGRANGE_VEC
  order = FIRST
 []
 [mx]
 []
 [my]
 []
 [mz]
 []
[]
[Kernels]
 [v]
  type = ADVectorDiffusion
  variable = v
 []
 [mx]
  type = Diffusion
  variable = mx
 []
 [my]
  type = Diffusion
  variable = my
 []
 [mz]
  type = Diffusion
  variable = mz
 []
[]
[BCs]
 [velocity]
  type = ADVectorFunctionDirichletBC
  variable = v
  boundary = 'left right top bottom front back'
  function_x = 1
  function_y = 2
  function_z = 3
 []
 [move_x]
  type = AFSDDisplaceBoundaryBC
  variable = mx
  boundary = 'left right top bottom front back'
  velocity = v
  component = 0
  associated_subdomain = 0
 []
 [dummy_x]
  type = INSADDummyDisplaceBoundaryIntegratedBC
  variable = mx
  boundary = 'left right top bottom front back'
  velocity = v
  component = 0
 []
 [move_y]
  type = AFSDDisplaceBoundaryBC
  variable = my
  boundary = 'left right top bottom front back'
  velocity = v
  component = 1
  associated_subdomain = 0
 []
 [dummy_y]
  type = INSADDummyDisplaceBoundaryIntegratedBC
  variable = my
  boundary = 'left right top bottom front back'
  velocity = v
  component = 1
 []
 [move_z]
  type = AFSDDisplaceBoundaryBC
  variable = mz
  boundary = 'left right top bottom front back'
  velocity = v
  component = 2
  associated_subdomain = 0
 []
 [dummy_z]
  type = INSADDummyDisplaceBoundaryIntegratedBC
  variable = mz
  boundary = 'left right top bottom front back'
  velocity = v
  component = 2
 []
[]
[Executioner]
 type = Transient
 solve_type = NEWTON
 scheme = bdf2
 dt = .1
 end_time = .3
 nl_abs_tol = 1e-12
 nl_rel_tol = 1e-10
 petsc_options_iname = '-pc_type'
 petsc_options_value = 'lu'
[]
[Preconditioning]
 [smp]
  type = SMP
  full = true
 []
[]
[Postprocessors]
 [mx]
  type = NodalExtremeValue
  value_type = max
  variable = mx
 []
 [my]
  type = NodalExtremeValue
  value_type = max
  variable = my
 []
 [mz]
  type = NodalExtremeValue
  value_type = max
  variable = mz
 []
[]
[Outputs]
 csv = true
[]
