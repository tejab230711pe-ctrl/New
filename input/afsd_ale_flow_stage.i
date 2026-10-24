# Sharp-interface ALE viscoplastic AFSD stage (MOOSE-only)
#
# This deck is deliberately separate from input/deposition.i.  Run the latter
# for the 0--4 s solid/solid rotating-contact dwell.  A rezone script transfers
# the qualified plastic region to this connected flow mesh at t = 4 s.
#
# The flow domain is a connected AA5083 body. The underside is bonded to the
# plate, the top face receives the consuming-rod velocity, and its exposed
# sides/top are material free surfaces. They move with the solved velocity via
# INSADDisplaceBoundaryBC. Flash is therefore retained in the mesh, never
# discarded as an assumed percentage.

[Mesh]
  type = GeneratedMesh
  dim = 3
  xmin = -0.030
  xmax =  0.030
  ymin =  0.000
  ymax =  0.015
  zmin =  0.010
  zmax =  0.016
  nx = 12
  ny = 3
  nz = 3
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
    initial_condition = 623.15
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
  # 1200 RPM shoulder: spindle axis at the current stage's y-centre.
  [shoulder_vx]
    type = ParsedFunction
    expression = '-125.663706143592 * (y - 0.0075)'
  []
  [shoulder_vy]
    type = ParsedFunction
    expression = '125.663706143592 * x + 0.00178571428571429'
  []
  # 75 mm/min rod consumption, supplied as a material inlet velocity.
  [shoulder_vz]
    type = ConstantFunction
    value = -0.00125
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
    type = INSADEnergySUPG
    variable = T
    velocity = velocity
    use_displaced_mesh = true
  []
  [plastic_heat]
    type = ALEViscoplasticDissipationHeat
    variable = T
    velocity = velocity
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
    boundary = bottom
    function_x = 0
    function_y = 0
    function_z = 0
  []
  [shoulder_inlet]
    type = ADVectorFunctionDirichletBC
    variable = velocity
    boundary = top
    function_x = shoulder_vx
    function_y = shoulder_vy
    function_z = shoulder_vz
  []
  # Fix the plate interface of the mesh. The free sides/front/back move with
  # the material; their deformation is the sharp free surface.
  [fix_mesh_x_bottom]
    type = DirichletBC
    variable = mesh_x
    boundary = bottom
    value = 0
  []
  [fix_mesh_y_bottom]
    type = DirichletBC
    variable = mesh_y
    boundary = bottom
    value = 0
  []
  [fix_mesh_z_bottom]
    type = DirichletBC
    variable = mesh_z
    boundary = bottom
    value = 0
  []
  # Sharp material free surfaces. The ALE update is implicit Euler:
  # x_mesh^(n+1) = x_mesh^n + dt * v_material^(n+1).
  # These faces are open to geometric expansion, so retained sideward flow
  # becomes bead/flash geometry rather than a prescribed bead width.
  [move_free_x]
    type = INSADDisplaceBoundaryBC
    boundary = 'left right front back'
    variable = mesh_x
    velocity = velocity
    component = 0
    associated_subdomain = 0
  []
  [move_free_y]
    type = INSADDisplaceBoundaryBC
    boundary = 'left right front back'
    variable = mesh_y
    velocity = velocity
    component = 1
    associated_subdomain = 0
  []
  [move_free_z]
    type = INSADDisplaceBoundaryBC
    boundary = 'left right front back'
    variable = mesh_z
    velocity = velocity
    component = 2
    associated_subdomain = 0
  []
  # Populate the off-diagonal mesh/velocity Jacobian entries required by the
  # monolithic ALE Newton solve.
  [move_free_x_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = 'left right front back'
    variable = mesh_x
    velocity = velocity
    component = 0
  []
  [move_free_y_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = 'left right front back'
    variable = mesh_y
    velocity = velocity
    component = 1
  []
  [move_free_z_dummy]
    type = INSADDummyDisplaceBoundaryIntegratedBC
    boundary = 'left right front back'
    variable = mesh_z
    velocity = velocity
    component = 2
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
  line_search = bt
  start_time = 4.0
  end_time = 8.0
  dtmin = 1.e-6
  dtmax = 1.e-4
  nl_rel_tol = 1.e-5
  nl_abs_tol = 1.e-6
  nl_max_its = 20
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
    file_base = ale_flow_stage
    execute_on = FINAL
    output_material_properties = true
    show_material_properties = 'plastic_fraction effective_strain_rate mu'
  []
  csv = true
[]
