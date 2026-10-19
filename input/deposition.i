# deposition.i
# ------------------------------------------------------------
# Rotating Disk Friction Deposition Simulation (MOOSE)
# ------------------------------------------------------------
# This input file reproduces the physics of the original FreeFEM script
# using MOOSE components:
#   - GeneratedMesh (hexahedral) for plate and rod
#   - AA5083ThermalProperties UserObject (temperature‑dependent cp, k, rho, yield, mu)
#   - MushyFraction material (latent‑heat, effective cp/k)
#   - J2Plasticity (Johnson‑Cook) linked to temperature‑dependent yield
#   - FrictionHeatSource kernel (friction heat source)
#   - NormalServo kernel (preload spring)
#   - Mortar contact (penalty contact)
#   - ALE mesh motion via MeshModifier
#   - CSV outputs matching the original script

# ------------------------------------------------------------
# 1. Global parameters (can be overridden on the command line)
# ------------------------------------------------------------
[GlobalParams]
  # Geometry
  plateLx = 0.150   # m
  plateLy = 0.150   # m
  plateT  = 0.006   # m (plate thickness)
  rodRadius = 0.0125   # m
  rodHeight = 0.300    # m

  # Process parameters
  rpm = 1200          # revolutions per minute
  dwellPreloadForce = 5000.0   # N (example value)
  normalServoBaseStiffness = 1.0e8   # Pa/m
  contactPenaltyStiffness = 1.0e9   # Pa/m
  heatGovernor = 1.0   # placeholder (can be made temperature dependent later)

  # Mesh resolution (default, can be changed via command line)
  nx = 20
  ny = 20
  nz = 16
  rodNx = 12
  rodNy = 24
  rodNz = 16

  # Time stepping
  dt = 0.25          # s
  totalTime = 10.0   # s (example; adjust as needed)
  outputEvery = 2   # write CSV every N timesteps
  aleMoveEvery = 2   # ALE mesh update interval

[]

# ------------------------------------------------------------
# 2. Meshes
# ------------------------------------------------------------
[Mesh]
  type = GeneratedMesh
  dim = 3
  nx = ${nx}
  ny = ${ny}
  nz = ${nz}
  xmax = ${plateLx}
  ymax = ${plateLy}
  zmax = ${plateT}
  name = plate_mesh
[]

[Mesh]
  type = GeneratedMesh
  dim = 3
  nx = ${rodNx}
  ny = ${rodNy}
  nz = ${rodNz}
  xmin = -${rodRadius}
  xmax =  ${rodRadius}
  ymin = -${rodRadius}
  ymax =  ${rodRadius}
  zmin = ${plateT}
  zmax = ${plateT + rodHeight}
  name = rod_mesh
[]

# ------------------------------------------------------------
# 3. Variables
# ------------------------------------------------------------
[Variables]
  # Temperature (K)
  [./T]
    order = FIRST
    family = LAGRANGE
  [../]

  # Z‑direction displacement (m) – used for momentum & ALE
  [./Uz]
    order = FIRST
    family = LAGRANGE
  [../]

  # Contact pressure scalar field (Pa)
  [./lambda_contact]
  order = FIRST
  family = LAGRANGE
  [../]
[]

# ------------------------------------------------------------
# 4. UserObject – material properties
# ------------------------------------------------------------
[UserObject]
  type = AA5083ThermalProperties
  name = material_props
[]

# ------------------------------------------------------------
# 5. Materials
# ------------------------------------------------------------
# Mushy zone (latent heat and effective conductivity)
[Material]
  type = MushyFraction
  name = mushy_mat
  temperature = T
  material_props = material_props
  # optional overrides (use defaults from the material implementation)
[]

# Johnson‑Cook plasticity – using the built‑in J2Plasticity material
# Note: we supply the temperature‑dependent yield via a MaterialPropertyUserObject
[Material]
  type = J2Plasticity
  name = jc_plasticity
  variable = Uz
  temperature = T
  yield = material_props/yieldStress
  elastic_modulus = 71.0e9   # E (Pa) – can be temperature dependent via a separate material if needed
  poisson = 0.33
  # Johnson‑Cook parameters (matching the original script)
  hardening_A = 255.21e6
  hardening_B = 735.80e6
  hardening_n = 1.075
  strain_rate_coefficient = 0.0028
  strain_rate_exponent = 1.0   # the log term is handled internally
  thermal_softening_exponent = 0.654
[]

# ------------------------------------------------------------
# 6. Kernels
# ------------------------------------------------------------
# Heat conduction (built‑in) – using effective cp and k from mushy_mat
[MooseVariable]
  type = Variable
  name = T
  order = FIRST
  family = LAGRANGE
[]

[Kernel]
  type = HeatConduction
  name = heat_cond
  variable = T
  conductivity = mushy_mat/k_eff
  specific_heat = mushy_mat/cp_eff
  density = material_props/rho
[]

# Friction heat source kernel
[Kernel]
  type = FrictionHeatSource
  name = friction_heat
  temperature = T
  contact_pressure = lambda_contact
  material_props = material_props
  radius = ${rodRadius}
  rpm = ${rpm}
  heat_governor = ${heatGovernor}
[]

# Normal‑servo preload kernel (applied to Uz)
[Kernel]
  type = NormalServo
  name = normal_servo
  disp = Uz
  stiffness = ${normalServoBaseStiffness}
  preload_force = ${dwellPreloadForce}
  ramp_time = 0.5   # seconds (example; matches the dwell ramp in the original script)
  current_time = time()
[]

# ------------------------------------------------------------
# 7. Contact (mortar)
# ------------------------------------------------------------
[Contact]
  type = ArbitraryLagrangeMultiplierContact
  name = rod_plate_contact
  mesh = rod_mesh
  secondary_mesh = plate_mesh
  secondary_variable = Uz
  primary_variable = Uz
  multiplier_space = LAGRANGE
  multiplier_order = FIRST
  multiplier_name = lambda_contact
[]

# ------------------------------------------------------------
# 8. ALE mesh motion (move the tip of the rod)
# ------------------------------------------------------------
[MeshModifier]
  type = ALEMeshModifier
  name = rod_ale
  mesh = rod_mesh
  execute_on = timestep_end
  interval = ${aleMoveEvery}
  # The actual motion will be calculated in a custom user object or via a simple displacement field.
[]

# ------------------------------------------------------------
# 9. Executioner (transient)
# ------------------------------------------------------------
[Executioner]
  type = Transient
  dt = ${dt}
  end_time = ${totalTime}
  # Use adaptive time stepping if desired:
  # time_stepper = "adaptivity"
[]

# ------------------------------------------------------------
# 10. Outputs – CSV files matching original script columns
# ------------------------------------------------------------
[Outputs]
  [./history]
    type = CSV
    file_base = consumable_rod_history
    execute_on = execute
    interval = ${outputEvery}
    # Columns – order matches the original FreeFEM header (partial list shown; extend as needed)
    variables = 'time rpm T_max T_avg axial_feed friction_power contact_pressure'
  []

  [./snapshots]
    type = CSV
    file_base = consumable_rod_snapshots
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time T Uz contact_pressure'
  []

  [./spatial_frames]
    type = CSV
    file_base = consumable_rod_spatial_frames
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time rod_center_x rod_center_y rod_height'
  []

  [./limit_violations]
    type = CSV
    file_base = consumable_rod_limit_violations
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time rpm axial_force contact_pressure'
  []

  [./heat_validation]
    type = CSV
    file_base = heat_validation_summary
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time Q_fric Q_latent Q_total'
  []
[]

  [./exodus]
    type = Exodus
    file_base = output
    execute_on = execute
    interval = ${outputEvery}
    variables = 'T Uz contact_pressure plastic_strain'
  []

# ------------------------------------------------------------
# End of input file
# ------------------------------------------------------------
