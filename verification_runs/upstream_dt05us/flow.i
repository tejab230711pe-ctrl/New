# Standalone hot-flow qualification; temperature is prescribed, not transferred from dwell.
# Experimental ALE viscoplastic AFSD stage (MOOSE-only).
# This rectangular prototype is separate from the solid-contact dwell model.
# A conservative solved-state handoff/rezone driver is NOT yet implemented.
# scripts/create_afsd_circular_flow_case.py creates the circular qualification case.
# Its fixed-inlet-rim/free-surface nodal motion currently FAILS the feed-volume
# screen. Do not interpret generated shapes as validated deposition predictions.
# No latent heat or solid-liquid transition is modeled.

[Mesh]
 [file]
  type = FileMeshGenerator
  file = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/upstream_dt05us/flow.msh
 []
 [free_nodes]
  type = ParsedGenerateNodeset
  input = file
  new_nodeset_name = free_nodes
  expression = '1'
  included_nodesets = free_surface
  excluded_nodesets = 'rod_inlet plate'
 []
 displacements = 'mesh_x mesh_y mesh_z'
[]

[Variables]
  [velocity]
    family = LAGRANGE_VEC
    order = FIRST
  []
  [pressure]
    family = LAGRANGE
    order = FIRST
  []
  [T]
    family = LAGRANGE
    order = FIRST
    initial_condition = 723.15
  []
  [mesh_x]
    family = LAGRANGE
    order = FIRST
  []
  [mesh_y]
    family = LAGRANGE
    order = FIRST
  []
  [mesh_z]
    family = LAGRANGE
    order = FIRST
  []
[]

[Functions]
 [center_y]
  type = ParsedFunction
  expression = '0.0125 + 0.00178571428571429*(t-4)'
 []
 [inlet_mesh_x]
  type = ParsedFunction
  expression = 'x*(cos(125.663706143592*(t-4))-1)-(y-0.0125)*sin(125.663706143592*(t-4))'
 []
 [inlet_mesh_y]
  type = ParsedFunction
  expression = 'x*sin(125.663706143592*(t-4))+(y-0.0125)*(cos(125.663706143592*(t-4))-1)+0.00178571428571429*(t-4)'
 []
 [shoulder_vx]
  type = ParsedFunction
  symbol_names = center
  symbol_values = center_y
  expression = '-125.663706143592*(y-center)'
 []
 [shoulder_vy]
  type = ParsedFunction
  expression = '125.663706143592*x + 0.00178571428571429'
 []
 [shoulder_vz]
  type = ConstantFunction
  value = -0.00125
 []
  [initial_vx]
    type = ParsedFunction
    expression = '-125.663706143592*(y-0.0125)*(min(z-0.010,0.006))/0.006 + 3*0.00125*(min(z-0.010,0.006))*(max(0.016-z,0))/0.006^3*x'
  []
  [initial_vy]
    type = ParsedFunction
    expression = '(125.663706143592*x + 0.00178571428571429)*(min(z-0.010,0.006))/0.006 + 3*0.00125*(min(z-0.010,0.006))*(max(0.016-z,0))/0.006^3*(y-0.0125)'
  []
  [initial_vz]
    type = ParsedFunction
    expression = '-0.00125*(3*((min(z-0.010,0.006))/0.006)^2 - 2*((min(z-0.010,0.006))/0.006)^3)'
  []
[]

[Kernels]
  [mass]
    type = INSADMass
    variable = pressure
    use_displaced_mesh = true
  []
  [mass_pspg]
    type = INSADMassPSPG
    variable = pressure
    use_displaced_mesh = true
  []
  [momentum_time]
    type = INSADMomentumTimeDerivative
    variable = velocity
    use_displaced_mesh = true
  []
  [momentum_advection]
    type = INSADMomentumAdvection
    variable = velocity
    use_displaced_mesh = true
  []
  [momentum_mesh_advection]
    type = INSADMomentumMeshAdvection
    variable = velocity
    disp_x = mesh_x
    disp_y = mesh_y
    disp_z = mesh_z
    use_displaced_mesh = true
  []
  [momentum_viscous]
    type = INSADMomentumViscous
    variable = velocity
    viscous_form = traction
    use_displaced_mesh = true
  []
  [momentum_pressure]
    type = INSADMomentumPressure
    variable = velocity
    pressure = pressure
    integrate_p_by_parts = true
    use_displaced_mesh = true
  []
  [momentum_supg]
    type = INSADMomentumSUPG
    variable = velocity
    material_velocity = relative_velocity
    use_displaced_mesh = true
  []
  [temperature_time]
    type = INSADHeatConductionTimeDerivative
    variable = T
    use_displaced_mesh = true
  []
  [temperature_advection]
    type = INSADEnergyAdvection
    variable = T
    use_displaced_mesh = true
  []
  [temperature_mesh_advection]
    type = INSADEnergyMeshAdvection
    variable = T
    disp_x = mesh_x
    disp_y = mesh_y
    disp_z = mesh_z
    use_displaced_mesh = true
  []
  [temperature_conduction]
    type = ADHeatConduction
    variable = T
    thermal_conductivity = k
    use_displaced_mesh = true
  []
  [temperature_supg]
    type = AFSDEnergySUPG
    variable = T
    material_velocity = relative_velocity
    use_displaced_mesh = true
  []
  [plastic_heat]
    type = ALEViscoplasticDissipationHeat
    variable = T
    use_displaced_mesh = true
  []
  # Harmonic mesh extension; free-surface displacement conditions below
  # determine the actual exposed boundary motion.
  [mesh_x_smoothing]
    type = Diffusion
    variable = mesh_x
  []
  [mesh_y_smoothing]
    type = Diffusion
    variable = mesh_y
  []
  [mesh_z_smoothing]
    type = Diffusion
    variable = mesh_z
  []
[]

[Materials]
  [aa5083_ale]
    type = AA5083ALEViscoplasticMaterial
    temperature = T
    velocity = velocity
    use_displaced_mesh = true
  []
  [stabilization]
    type = INSADStabilized3Eqn
    velocity = velocity
    pressure = pressure
    temperature = T
    use_displaced_mesh = true
  []
[]

[BCs]
  # No-slip bonded plate interface. It remains solid-contact material outside
  # this re-zoned plastic domain.
  [plate_no_slip]
    type = ADVectorFunctionDirichletBC
    variable = velocity
    boundary = plate
    function_x = 0
    function_y = 0
    function_z = 0
  []
  [shoulder_inlet]
    type = ADVectorFunctionDirichletBC
    variable = velocity
    boundary = rod_inlet
    function_x = shoulder_vx
    function_y = shoulder_vy
    function_z = shoulder_vz
    use_displaced_mesh = true
  []
  # Fix the plate interface of the mesh. The free sides/front/back move with
  # the material; their deformation is the sharp free surface.
  [fix_mesh_x_bottom]
    type = DirichletBC
    variable = mesh_x
    boundary = plate
    value = 0
  []
  [fix_mesh_y_bottom]
    type = DirichletBC
    variable = mesh_y
    boundary = plate
    value = 0
  []
  [fix_mesh_z_bottom]
    type = DirichletBC
    variable = mesh_z
    boundary = plate
    value = 0
  []
  # Sharp material free surfaces. The ALE update is implicit Euler:
  # x_mesh^(n+1) = x_mesh^n + dt * v_material^(n+1).
  # These faces are open to geometric expansion, so retained sideward flow
  # becomes bead/flash geometry rather than a prescribed bead width.
  [move_free_x]
    type = INSADDisplaceBoundaryBC
    boundary = free_nodes
    variable = mesh_x
    velocity = velocity
    component = 0
    associated_subdomain = flow
  []
  [move_free_y]
    type = INSADDisplaceBoundaryBC
    boundary = free_nodes
    variable = mesh_y
    velocity = velocity
    component = 1
    associated_subdomain = flow
  []
  [move_free_z]
    type = INSADDisplaceBoundaryBC
    boundary = free_nodes
    variable = mesh_z
    velocity = velocity
    component = 2
    associated_subdomain = flow
  []
  # Populate the off-diagonal mesh/velocity Jacobian entries required by the
  # monolithic ALE Newton solve.
  [move_free_x_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = free_surface
    variable = mesh_x
    velocity = velocity
    component = 0
  []
  [move_free_y_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = free_surface
    variable = mesh_y
    velocity = velocity
    component = 1
  []
  [move_free_z_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = free_surface
    variable = mesh_z
    velocity = velocity
    component = 2
  []
  [inlet_mesh_x]
    type = FunctionDirichletBC
    variable = mesh_x
    boundary = rod_inlet
    function = inlet_mesh_x
  []
  [inlet_mesh_y]
    type = FunctionDirichletBC
    variable = mesh_y
    boundary = rod_inlet
    function = inlet_mesh_y
  []
  [inlet_mesh_z]
    type = FunctionDirichletBC
    variable = mesh_z
    boundary = rod_inlet
    function = 0
  []
  [inlet_temperature]
    type = DirichletBC
    variable = T
    boundary = rod_inlet
    value = 723.15
  []
  [free_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = free_surface
    coefficient = 25
    T_infinity = 293.15
    use_displaced_mesh = true
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  # Pivoting direct solver for the coupled saddle-point system.
  petsc_options_iname = '-ksp_type -pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'preonly lu mumps'
  line_search = bt
  start_time = 4.0
  end_time = 4.000003
  dtmin = 1.e-6
  dtmax = 1.e-4
  automatic_scaling = true
  off_diagonals_in_auto_scaling = true
  nl_rel_tol = 1.e-7
  nl_abs_tol = 1.e-12
  nl_max_its = 60
  l_max_its = 100
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.e-5
    optimal_iterations = 8
    cutback_factor_at_failure = 0.5
  []
[]

[Outputs]
  [exodus]
    type = Exodus
    file_base = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/upstream_dt05us/flow
    execute_on = 'INITIAL TIMESTEP_END'
    output_material_properties = true
    show_material_properties = 'plastic_fraction effective_strain_rate mu'
  []
  csv = true
  file_base = /home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/verification_runs/upstream_dt05us/flow
[]

[ICs]
 [initial_velocity]
  type = VectorFunctionIC
  variable = velocity
  function_x = initial_vx
  function_y = initial_vy
  function_z = initial_vz
 []
[]

[Postprocessors]
 [volume]
  type = VolumePostprocessor
  use_displaced_mesh = true
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [T_min]
  type = NodalExtremeValue
  variable = T
  value_type = min
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [T_max]
  type = NodalExtremeValue
  variable = T
  value_type = max
  execute_on = 'INITIAL TIMESTEP_END'
 []
 [inlet_area]
  type = FunctionSideIntegral
  function = 1
  boundary = rod_inlet
  use_displaced_mesh = true
  execute_on = 'INITIAL TIMESTEP_END'
 []
[]
