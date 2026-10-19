# Rotating Disk Friction Deposition (AFSD) – Full MOOSE Input

# ------------------------------------------------------------
# 1. Global parameters (can be overridden on the command line)
# ------------------------------------------------------------
[GlobalParams]
  # Geometry (all units in meters)
  plateLx = 0.150   # Plate length (x)
  plateLy = 0.150   # Plate width (y)
  plateT  = 0.006   # Plate thickness
  rodRadius = 0.0125   # Consumable rod radius
  rodHeight = 0.300    # Consumable rod initial height

  # Process parameters
  rpm = 1200            # Spindle speed (rev/min)
  dwellPreloadForce = 5000.0   # Preload force during dwell (N)
  normalServoBaseStiffness = 1.0e8   # Spring stiffness for preload (Pa/m)
  contactPenaltyStiffness = 1.0e9   # Penalty stiffness for mortar contact (Pa/m)
  heatGovernor = 1.0   # Thermal governor factor (0‑1), can be made T‑dependent later

  # Mesh resolution (can be changed via CLI)
  nx = 20
  ny = 20
  nz = 16
  rodNx = 12
  rodNy = 24
  rodNz = 16

  # Time stepping
  dt = 0.25             # Fixed time step (s)
  totalTime = 10.0      # Total simulation duration (s)
  outputEvery = 2       # Write output every N timesteps
  aleMoveEvery = 2      # ALE mesh update interval (timesteps)
[]

# ------------------------------------------------------------
# 2. Mesh definitions (hex‑ahedral, generated)
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
# 3. Primary variables
# ------------------------------------------------------------
[Variables]
  [./T]
    order = FIRST
    family = LAGRANGE
  [../]

  [./Uz]
    order = FIRST
    family = LAGRANGE
  [../]

  [./contact_pressure]
    order = FIRST
    family = LAGRANGE
  [../]
[]

# ------------------------------------------------------------
# 4. Material property user object (AA5083)
# ------------------------------------------------------------
[UserObject]
  type = AA5083ThermalProperties
  name = material_props
[]

# ------------------------------------------------------------
# 5. Materials
# ------------------------------------------------------------
# 5.1. Mushy‑zone material – handles latent heat and effective cp/k
[Material]
  type = MushyFraction
  name = mushy_mat
  temperature = T
  material_props = material_props
[]

# 5.2. Johnson‑Cook viscoplasticity (temperature‑dependent yield)
[Material]
  type = J2Plasticity
  name = jc_plasticity
  variable = Uz
  temperature = T
  yield = material_props/yieldStress
  elastic_modulus = 71.0e9   # Young's modulus (Pa)
  poisson = 0.33
  # Johnson‑Cook parameters (taken from the original FreeFEM script)
  hardening_A = 255.21e6
  hardening_B = 735.80e6
  hardening_n = 1.075
  strain_rate_coefficient = 0.0028
  strain_rate_exponent = 1.0
  thermal_softening_exponent = 0.654
[]

# ------------------------------------------------------------
# 6. Kernels
# ------------------------------------------------------------
# 6.1. Heat conduction with effective cp/k from mushy_mat
[Kernel]
  type = HeatConduction
  name = heat_cond
  variable = T
  conductivity = mushy_mat/k_eff
  specific_heat = mushy_mat/cp_eff
  density = material_props/rho
[]

# 6.2. Frictional heat generation at the contact interface
[Kernel]
  type = FrictionHeatSource
  name = friction_heat
  temperature = T
  contact_pressure = contact_pressure
  material_props = material_props
  radius = ${rodRadius}
  rpm = ${rpm}
  heat_governor = ${heatGovernor}
[]

# 6.3. Preload spring (normal servo) applied to Uz
[Kernel]
  type = NormalServo
  name = normal_servo
  disp = Uz
  stiffness = ${normalServoBaseStiffness}
  preload_force = ${dwellPreloadForce}
  ramp_time = 0.5   # seconds (ramp during dwell phase)
[]

# ------------------------------------------------------------
# 7. Contact – mortar formulation
# ------------------------------------------------------------
[Contact]
  type = MortarContact
  name = rod_plate_contact
  mesh = rod_mesh
  secondary_mesh = plate_mesh
  secondary_variable = Uz
  primary_variable = Uz
  penalty = ${contactPenaltyStiffness}
  contact_pressure = contact_pressure
[]

# ------------------------------------------------------------
# 8. ALE mesh motion – moves the rod tip according to feed rate
# ------------------------------------------------------------
[MeshModifier]
  type = ALEMeshModifier
  name = rod_ale
  mesh = rod_mesh
  execute_on = timestep_end
  interval = ${aleMoveEvery}
  # Simple linear feed; for more realism replace with a custom UserObject
[]

# ------------------------------------------------------------
# 9. Executioner – transient solver
# ------------------------------------------------------------
[Executioner]
  type = Transient
  dt = ${dt}
  end_time = ${totalTime}
  # time_stepper = "adaptivity"   # uncomment to enable adaptive stepping
[]

# ------------------------------------------------------------
# 10. Outputs – CSV logs + Exodus file for ParaView
# ------------------------------------------------------------
[Outputs]
  # CSV: global history (same columns as original FreeFEM output)
  [./history]
    type = CSV
    file_base = consumable_rod_history
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time rpm T_max T_avg axial_feed friction_power contact_pressure'
  []

  # CSV: per‑timestep field snapshots (selected variables)
  [./snapshots]
    type = CSV
    file_base = consumable_rod_snapshots
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time T Uz contact_pressure plastic_strain'
  []

  # CSV: geometric tracking of the consumable rod
  [./spatial_frames]
    type = CSV
    file_base = consumable_rod_spatial_frames
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time rod_center_x rod_center_y rod_height'
  []

  # CSV: machine‑limit violations (if any thresholds are crossed)
  [./limit_violations]
    type = CSV
    file_base = consumable_rod_limit_violations
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time rpm axial_force contact_pressure'
  []

  # CSV: energy‑balance validation (friction + latent heat)
  [./heat_validation]
    type = CSV
    file_base = heat_validation_summary
    execute_on = execute
    interval = ${outputEvery}
    variables = 'time Q_fric Q_latent Q_total'
  []

  # Exodus file for full 3‑D field visualisation (ParaView / VisIt)
  [./exodus]
    type = Exodus
    file_base = output
    execute_on = execute
    interval = ${outputEvery}
    variables = 'T Uz contact_pressure plastic_strain'
  []
[]

# End of input file
