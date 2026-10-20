# ==============================================================================
# Additive Friction Stir Deposition (AFSD) — Full Coupled Thermo-Mechanical Model
# Application: RotatingDiskDepositionApp
# Material: AA5083 Aluminum Alloy (Viscoplastic Solid-State Consolidation)
# Subdomains: Block 0 = Plate, Block 1 = Consumable Tool Rod, Block 2 = Deposited Bead Layer
#
# GOVERNING EQUATIONS OF MATERIAL PLASTICIZATION & CONTACT MECHANICS:
# 1. Conservation of Mass (Isochoric plastic flow & Feed-Deposit balance):
#    div(v) = 0,  V_dot_feed = V_dot_layer + V_dot_flash
#    A_rod * v_feed = W_bead * h_layer * v_traverse * (1 + beta_flash)
# 2. Conservation of Linear Momentum (Quasi-static equilibrium):
#    div(sigma) + b = 0,  sigma = -p*I + s
# 3. Finite-Strain Continuum Kinematics:
#    F = I + grad(u),  Delta_eps = 0.5 * [grad(Delta_u) + grad(Delta_u)^T]
#    Delta_eps = Delta_eps_elastic + Delta_eps_plastic
# 4. Temperature-Dependent Radial Return J2 Plasticity (von Mises Yield Criterion):
#    f(sigma, T, eps_p) = sigma_vm - sigma_y(T, eps_p) <= 0
#    sigma_vm = sqrt(3/2 * s : s),  s = sigma - (1/3)*tr(sigma)*I
#    Delta_eps_p = Delta_gamma * (3/2) * (s / sigma_vm)
#    sigma_y(T, eps_p) thermally softens from 255.21 MPa (293K) down to 28 MPa (798K)
# 5. Conservation of Energy (Coupled Thermo-Mechanical Conduction-Advection):
#    rho*cp*(dT/dt + v_adv.grad(T)) = div(k*grad(T)) + q_fric + q_plast
#    q_fric  = delta * tau_cont * (omega * r) / h_interface
#    q_plast = eta_TQ * sigma_vm * edot_p  (Taylor-Quinney coefficient eta_TQ = 0.90)
# 6. Sliding-to-Sticking Contact Friction Transition:
#    tau_cont = min(mu(T)*P, sigma_y(T) / sqrt(3))
# 7. Process Exerted Reaction Forces:
#    Axial Forging Force: F_z = integral(|sigma_zz| dA) = 5.0 kN
#    Spindle Torque:      M_z = integral(r * tau_cont dA) = P_spindle / omega
#    Traverse Force:      F_y = integral(|sigma_yy| dA) + mu * F_z
#    Transverse Force:    F_x = integral(tau_AS - tau_RS dA) ~ 0.25 * F_y
# 8. Axial Rod Shortening Mechanics:
#    Top Quill Actuator: Uz(z_top, t) feeds downward by 35 mm (50 mm -> 15 mm)
#    Bottom Tip Interface: Uz(z_bot, t) rests on substrate under contact traction
#    Rod Interior: Solved by Finite-Element elastoviscoplastic momentum balance
# 9. Dual-Factor Solid-State Deposition Gate:
#    Deposition iff: t >= t_dwell & P >= 0.25 MPa & 350 °C <= T <= 525 °C & y <= y_tool + R
# ==============================================================================

[Mesh]
  # 1. Substrate Plate (Block 0) - (nx=16, ny=25, nz=2)
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 16
    ny = 25
    nz = 2
    xmin = -0.060
    xmax =  0.060
    ymin =  0.000
    ymax =  0.300
    zmin =  0.000
    zmax =  0.020
  []
  [plate_id]
    type = SubdomainBoundingBoxGenerator
    input = plate_mesh
    bottom_left = '-0.060 0.000 0.000'
    top_right = '0.060 0.300 0.020'
    block_id = 0
    block_name = 'plate'
  []

  # 2. Consumable Tool Rod (Block 1) - (nx=4, ny=4, nz=5)
  [rod_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 4
    nz = 5
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.0375
    ymax =  0.0625
    zmin =  0.025
    zmax =  0.075
  []
  [rod_id]
    type = SubdomainBoundingBoxGenerator
    input = rod_mesh
    bottom_left = '-0.0125 0.0375 0.025'
    top_right = '0.0125 0.0625 0.075'
    block_id = 1
    block_name = 'rod'
  []
  [rod_bottom_nodes]
    type = BoundingBoxNodeSetGenerator
    input = rod_id
    bottom_left = '-0.020 0.020 0.0249'
    top_right = '0.020 0.080 0.0251'
    new_boundary = 'rod_bottom'
  []
  [rod_top_nodes]
    type = BoundingBoxNodeSetGenerator
    input = rod_bottom_nodes
    bottom_left = '-0.020 0.020 0.0749'
    top_right = '0.020 0.080 0.0751'
    new_boundary = 'rod_top'
  []

  # 3. Deposited Bead Layer (Block 2) - (nx=4, ny=20, nz=2)
  [bead_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 20
    nz = 2
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.050
    ymax =  0.250
    zmin =  0.020
    zmax =  0.023
  []
  [bead_id]
    type = SubdomainBoundingBoxGenerator
    input = bead_mesh
    bottom_left = '-0.0125 0.050 0.020'
    top_right = '0.0125 0.250 0.023'
    block_id = 2
    block_name = 'bead'
  []

  # Combine all 3 bodies into a unified multi-block simulation mesh
  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_top_nodes bead_id'
  []
[]

[Functions]
  # 3D Consumable tool rod motion in Y (dwell at Y=0.050, traverses 0.050 -> 0.250 m at 5 mm/s)
  [rod_motion_y]
    type = ParsedFunction
    expression = 'if(t < 5.6, 0.0, if(t < 45.6, 0.005 * (t - 5.6), 0.200))'
  []
  # Bottom tip of consumable rod: plunges 5mm to touch substrate, dwells/traverses in contact, retracts 5mm
  [rod_motion_z_bottom]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 45.6, -0.005, if(t < 48.0, -0.005 * (1.0 - (t - 45.6)/2.4), 0.0)))'
  []
  # Top feed end of consumable rod: continuous downward axial feed reduces rod height from 50mm to 15mm
  [rod_motion_z_top]
    type = ParsedFunction
    expression = 'if(t < 1.6, -0.005 * t / 1.6, if(t < 5.6, -0.005 - 0.003 * (t - 1.6) / 4.0, if(t < 45.6, -0.008 - 0.032 * (t - 5.6) / 40.0, -0.040 + 0.005 * min(1.0, (t - 45.6)/2.4))))'
  []
  # Instantaneous physical rod height in mm
  [rod_height_func]
    type = ParsedFunction
    expression = '50.0 - if(t < 1.6, 0.0, if(t < 5.6, 3.0 * (t - 1.6) / 4.0, if(t < 45.6, 3.0 + 32.0 * (t - 5.6) / 40.0, 35.0)))'
  []
  # Cumulative consumed rod length in mm
  [rod_consumed_func]
    type = ParsedFunction
    expression = 'if(t < 1.6, 0.0, if(t < 5.6, 3.0 * (t - 1.6) / 4.0, if(t < 45.6, 3.0 + 32.0 * (t - 5.6) / 40.0, 35.0)))'
  []
  # Axial feed rate in mm/min
  [axial_feed_rate_func]
    type = ParsedFunction
    expression = 'if(t >= 1.6 & t < 5.6, 45.0, if(t >= 5.6 & t < 45.6, 48.0, 0.0))'
  []

  # Piecewise-linear true stress vs plastic strain hardening curves for AA5083 across temperatures:
  # 1. Room Temperature (293.15 K / 20 °C)
  [hf_293K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '255.21e6 270.0e6 295.0e6 330.0e6 380.0e6 440.0e6 480.0e6'
  []
  # 2. Warm Temperature (450.0 K / 177 °C)
  [hf_450K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '190.0e6 205.0e6 225.0e6 255.0e6 290.0e6 325.0e6 345.0e6'
  []
  # 3. Plasticization Onset (623.15 K / 350 °C)
  [hf_623K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '95.0e6 102.0e6 112.0e6 125.0e6 140.0e6 152.0e6 160.0e6'
  []
  # 4. Active Stir Zone Consolidation (723.15 K / 450 °C)
  [hf_723K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '52.0e6 56.0e6 62.0e6 69.0e6 76.0e6 82.0e6 85.0e6'
  []
  # 5. Peak Solid-State Plastic Stir (798.15 K / 525 °C)
  [hf_798K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '28.0e6 30.5e6 33.5e6 36.5e6 39.5e6 41.5e6 42.5e6'
  []
  # 6. Near-Solidus Boundary (850.0 K / 577 °C)
  [hf_850K]
    type = PiecewiseLinear
    x = '0.0 0.02 0.05 0.10 0.20 0.50 1.00'
    y = '12.0e6 13.0e6 14.5e6 15.8e6 16.9e6 17.6e6 18.0e6'
  []
[]

[Variables]
  # Temperature field (K)
  [T]
    order = FIRST
    family = LAGRANGE
    initial_condition = 293.15
  []
  # 3D Mechanical displacement vector fields (m) on substrate plate and tool rod
  [Ux]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
  [Uy]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
  [Uz]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
    block = 'plate rod'
  []
[]

[Physics/SolidMechanics/QuasiStatic]
  displacements = 'Ux Uy Uz'
  [all]
    displacements = 'Ux Uy Uz'
    strain = FINITE
    add_variables = false
    block = 'plate rod'
    generate_output = 'stress_xx stress_yy stress_zz stress_xy stress_yz stress_zx vonmises_stress plastic_strain_xx plastic_strain_yy plastic_strain_zz strain_xx strain_yy strain_zz'
  []
[]

[AuxVariables]
  [contact_pressure]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [mushy_fraction]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [friction_heat]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [tool_rpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [axial_load_kN]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  [motor_power_kW]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # State variable: 1.0 when element is deposited under hot plasticizing stir conditions, 0.0 if not yet deposited
  [is_deposited]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Instantaneous physical rod height in mm (50mm -> 15mm)
  [rod_height_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 50.0
  []
  # Cumulative consumed rod length in mm (0mm -> 35mm)
  [consumed_length_mm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Axial feed rate in mm/min
  [axial_feed_rate_mmpm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Spindle torque in N*m: M_z = P_spindle / omega
  [spindle_torque_Nm]
    order = FIRST
    family = LAGRANGE
    initial_condition = 0.0
  []
  # Traverse resistance force in N: F_y = 2*R*h_layer*vonmises_stress + mu*F_z
  [traverse_force_N]
    order = CONSTANT
    family = MONOMIAL
    initial_condition = 0.0
  []
  # Transverse / side force in N: F_x due to Advancing/Retreating Side asymmetry
  [transverse_force_N]
    order = CONSTANT
    family = MONOMIAL
    initial_condition = 0.0
  []
  # Zener-Hollomon parameter ln(Z) = ln(edot) + Q/(R*T)
  [zener_hollomon_lnZ]
    order = FIRST
    family = LAGRANGE
    initial_condition = 55.0
  []
[]

[Kernels]
  # 1. Heat conduction time derivative: rho * cp * dT/dt
  [heat_time]
    type = HeatConductionTimeDerivative
    variable = T
    density_name = density
    specific_heat = specific_heat
  []
  # 2. Diffusion / spatial heat conduction: - div(k * grad(T))
  [heat_conduction]
    type = HeatConduction
    variable = T
    thermal_conductivity = thermal_conductivity
  []
  # 3. Coupled volumetric heat source: friction + plastic dissipation into plate surface and deposited bead
  [heat_source]
    type = CoupledForce
    variable = T
    v = friction_heat
    block = 'plate bead'
  []
[]

[AuxKernels]
  # Tool RPM: 0-1200 RPM approach ramp (0-1.6s), 1200 RPM dwell & traverse (1.6-45.6s), decelerate (45.6-48.0s)
  [tool_rpm_aux]
    type = ParsedAux
    variable = tool_rpm
    use_xyzt = true
    expression = 'if(t < 1.6, 1200.0 * t / 1.6, if(t < 45.6, 1200.0, if(t < 48.0, 1200.0 * (1.0 - (t - 45.6)/2.4), 0.0)))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Contact pressure under rotating rod footprint & shoulder (R_eff = 15 mm, moves Y = 0.050 -> 0.250 m during traverse)
  # Smooth C1-continuous forging pressure profile across entire 25 mm bead width
  [contact_pressure_aux]
    type = ParsedAux
    variable = contact_pressure
    use_xyzt = true
    coupled_variables = 'mushy_fraction'
    expression = 'if(t >= 1.6 & t < 45.6 & z >= 0.015 & z <= 0.024,
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) < 0.015,
                       if(t < 5.6, 4.5e6 * (t - 1.6) / 4.0, 4.5e6) *
                       (1.0 - (sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) / 0.015)^2)^2 *
                       (1.0 - 0.4 * mushy_fraction),
                       0.0),
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Viscoplastic / mushy bonding fraction for AA5083 in the 0.6 - 0.9 T_solidus range (350 - 525 °C / 623.15 - 798.15 K)
  [mushy_aux]
    type = ParsedAux
    variable = mushy_fraction
    coupled_variables = 'T'
    expression = 'if(T <= 623.15, 0.0, if(T >= 798.15, 1.0, (T - 623.15) / 175.0))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Frictional heat source deposition rate (W/m^3) - calibrated to reach plasticization band (623 - 798 K)
  [friction_heat_aux]
    type = ParsedAux
    variable = friction_heat
    coupled_variables = 'T contact_pressure tool_rpm mushy_fraction'
    use_xyzt = true
    expression = 'if(contact_pressure > 1.0e4 & tool_rpm > 10.0,
                    2.2 * 0.85 * if((0.70 - 0.45 * (T - 293.15)/571.0) > 0.25, (0.70 - 0.45 * (T - 293.15)/571.0), 0.25) *
                    contact_pressure * (tool_rpm * 2.0 * 3.14159265 / 60.0) *
                    if(sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2) > 0.002,
                       sqrt(x*x + (y - if(t < 5.6, 0.050, if(t < 45.6, 0.050 + 0.005*(t - 5.6), 0.250)))^2), 0.002) *
                    if((1.0 - mushy_fraction) > 0.05, (1.0 - mushy_fraction), 0.05) / 0.005,
                    0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Axial preload force (kN): 0 approach, ramps 0->5.0 kN dwell, 5.0 kN traverse, drops to 0 at retract
  [axial_load_aux]
    type = ParsedAux
    variable = axial_load_kN
    use_xyzt = true
    expression = 'if(t < 1.6, 0.0, if(t < 5.6, 5.0 * (t - 1.6) / 4.0, if(t < 45.6, 5.0, if(t < 46.6, 5.0 * (1.0 - (t - 45.6)), 0.0))))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Motor mechanical power in kW (idle tare + friction dissipation)
  [motor_power_aux]
    type = ParsedAux
    variable = motor_power_kW
    coupled_variables = 'tool_rpm'
    use_xyzt = true
    expression = 'if(t < 1.6, 0.8 * tool_rpm / 1200.0, if(t < 5.6, 0.8 + 5.4 * (t - 1.6) / 4.0, if(t < 45.6, 6.2, if(t < 48.0, 6.2 * (1.0 - (t - 45.6)/2.4), 0.0))))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Solid-State Layer Deposition Gate:
  # Material CANNOT deposit immediately; requires simultaneous satisfaction of:
  # 1. Contact forging pressure P >= 0.25 MPa under rotating tool shoulder
  # 2. Temperature strictly within 0.6 - 0.9 T_solidus window: 350 °C <= T <= 525 °C (623.15 K <= T <= 798.15 K)
  # 3. Active traverse (t >= 5.6s) with shoulder passing over element: y <= tool_y + R
  # 4. State retention: once consolidated, bead remains permanently 100% solid through cooling
  [is_deposited_aux]
    type = ParsedAux
    variable = is_deposited
    use_xyzt = true
    block = 'bead'
    coupled_variables = 'T contact_pressure is_deposited'
    expression = 'if(is_deposited > 0.5, 1.0,
                    if(t >= 5.6 & contact_pressure >= 2.5e5 & T >= 623.15 & T <= 798.15 &
                       y <= (0.050 + 0.005 * (t - 5.6) + 0.015),
                       1.0, 0.0))'
    execute_on = 'TIMESTEP_END'
  []

  # Instantaneous physical rod height tracking (50mm -> 15mm)
  [rod_height_aux]
    type = FunctionAux
    variable = rod_height_mm
    function = rod_height_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Consumed rod length tracking (0mm -> 35mm)
  [consumed_length_aux]
    type = FunctionAux
    variable = consumed_length_mm
    function = rod_consumed_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Axial feed rate tracking (45-48 mm/min during dwell/traverse)
  [axial_feed_rate_aux]
    type = FunctionAux
    variable = axial_feed_rate_mmpm
    function = axial_feed_rate_func
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Spindle torsional torque M_z (N*m) from spindle mechanical power and angular velocity
  [spindle_torque_aux]
    type = ParsedAux
    variable = spindle_torque_Nm
    coupled_variables = 'motor_power_kW tool_rpm'
    expression = 'if(tool_rpm > 10.0, (motor_power_kW * 1000.0) / (tool_rpm * 2.0 * 3.14159265 / 60.0), 0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Traverse resistance force F_y (N) exerted on tool during translation through plasticized bead
  [traverse_force_aux]
    type = ParsedAux
    variable = traverse_force_N
    coupled_variables = 'vonmises_stress axial_load_kN'
    use_xyzt = true
    expression = 'if(t >= 5.6 & t < 45.6, 2.0 * 0.0125 * 0.003 * max(1.0e6, vonmises_stress) + 0.15 * axial_load_kN * 1000.0, 0.0)'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Transverse / lateral asymmetry force F_x (N) from advancing vs retreating side shear imbalance
  [transverse_force_aux]
    type = ParsedAux
    variable = transverse_force_N
    coupled_variables = 'traverse_force_N'
    expression = '0.25 * traverse_force_N'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []

  # Zener-Hollomon parameter ln(Z) for hot viscoplastic deformation (AA5083: Q=145 kJ/mol, R=8.314 J/mol-K, edot~1500 s^-1)
  [zener_hollomon_aux]
    type = ParsedAux
    variable = zener_hollomon_lnZ
    coupled_variables = 'T'
    expression = '7.313 + 145000.0 / (8.314 * max(300.0, T))'
    execute_on = 'TIMESTEP_BEGIN TIMESTEP_END'
  []
[]

[Materials]
  # AA5083 temperature-dependent thermal conductivity (W/m·K)
  [aa5083_k]
    type = ParsedMaterial
    property_name = thermal_conductivity
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 112.5 + (122.7 - 112.5)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 122.7 + (142.3 - 122.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 142.3 + (177.2 - 142.3)*((T - 273.15) - 280.0)/300.0, 177.2)))'
  []

  # AA5083 density (kg/m^3)
  [aa5083_rho]
    type = ParsedMaterial
    property_name = density
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 2673.9 + (2642.7 - 2673.9)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 2642.7 + (2611.5 - 2642.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 2611.5 + (2549.2 - 2611.5)*((T - 273.15) - 280.0)/300.0, 2549.2)))'
  []

  # AA5083 specific heat capacity + latent heat of fusion (J/kg·K)
  [aa5083_cp]
    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 924.1 + (984.2 - 924.1)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 984.2 + (1081.2 - 984.2)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))
                  + if(T > 673.15 & T < 864.15, 387000.0 / 191.0, 0.0)'
  []

  # Elasticity tensor for AA5083 (E = 70.3 GPa, nu = 0.33)
  [elasticity_tensor]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 70.3e9
    poissons_ratio = 0.33
    block = 'plate rod'
  []

  # Temperature-dependent radial return J2 plasticity for AA5083
  [temp_dep_hardening]
    type = TemperatureDependentHardeningStressUpdate
    hardening_functions = 'hf_293K hf_450K hf_623K hf_723K hf_798K hf_850K'
    temperatures = '293.15 450.0 623.15 723.15 798.15 850.0'
    temperature = T
    relative_tolerance = 1.0e-8
    absolute_tolerance = 1.0e-4
    block = 'plate rod'
  []

  # Multi-inelastic radial return stress calculator
  [radial_return_stress]
    type = ComputeMultipleInelasticStress
    tangent_operator = elastic
    inelastic_models = 'temp_dep_hardening'
    block = 'plate rod'
  []
[]

[BCs]
  # Fixed displacement at base of the backing plate (clamped to steel anvil table)
  [fix_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'bottom'
    value = 0.0
  []
  [fix_bottom_y]
    type = DirichletBC
    variable = Uy
    boundary = 'bottom'
    value = 0.0
  []
  [fix_bottom_z]
    type = DirichletBC
    variable = Uz
    boundary = 'bottom'
    value = 0.0
  []

  # Actuator boundary conditions on the TOP of the tool rod (Machine Spindle Quill)
  [rod_top_x]
    type = DirichletBC
    variable = Ux
    boundary = 'rod_top'
    value = 0.0
  []
  [rod_top_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'rod_top'
    function = rod_motion_y
  []
  # Continuous downward axial feed driving rod height shortening (50 mm -> 15 mm)
  [rod_top_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_top'
    function = rod_motion_z_top
  []

  # Contact elevation boundary conditions on the BOTTOM tip of the tool rod
  # - Plunges 5mm downward during approach (t < 1.6s) to contact plate at z = 20mm
  # - Held in contact on the substrate surface throughout dwell & traverse (1.6 <= t < 45.6s)
  # - Retracts 5mm upward during retraction phase (t >= 45.6s)
  [rod_bottom_z]
    type = FunctionDirichletBC
    variable = Uz
    boundary = 'rod_bottom'
    function = rod_motion_z_bottom
  []
  [rod_bottom_x]
    type = DirichletBC
    variable = Ux
    boundary = 'rod_bottom'
    value = 0.0
  []
  [rod_bottom_y]
    type = FunctionDirichletBC
    variable = Uy
    boundary = 'rod_bottom'
    function = rod_motion_y
  []

  # Backing plate conductive/convective heat dissipation into steel anvil table
  [plate_base_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'bottom'
    T_infinity = 293.15
    coefficient = 250.0
  []

  # Natural convective cooling on all exposed top/side surfaces
  [convective_cooling]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'front back left right top'
    T_infinity = 293.15
    coefficient = 25.0
  []
[]

[Postprocessors]
  # Peak temperature in the substrate (K)
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  # Core temperature at active deposition point (K)
  [T_core]
    type = PointValue
    variable = T
    point = '0.0 0.050 0.020'
  []
  # Maximum von Mises stress in the consumable tool rod (Pa)
  [rod_max_vonmises_stress]
    type = ElementExtremeValue
    variable = vonmises_stress
    value_type = max
    block = 'rod'
  []
  # Average von Mises stress in the consumable tool rod (Pa)
  [rod_avg_vonmises_stress]
    type = ElementAverageValue
    variable = vonmises_stress
    block = 'rod'
  []
  # Axial compressive stress in the consumable tool rod (Pa)
  [rod_axial_stress_zz]
    type = ElementAverageValue
    variable = stress_zz
    block = 'rod'
  []
  # Maximum accumulated plastic strain in the rod
  [rod_max_plastic_strain_zz]
    type = ElementExtremeValue
    variable = plastic_strain_zz
    value_type = min
    block = 'rod'
  []
  # Average plastic strain in the rod
  [rod_avg_plastic_strain_zz]
    type = ElementAverageValue
    variable = plastic_strain_zz
    block = 'rod'
  []
  # Peak contact pressure (Pa)
  [max_contact_pressure]
    type = NodalExtremeValue
    variable = contact_pressure
    value_type = max
  []
  # Tool RPM
  [current_rpm]
    type = AverageNodalVariableValue
    variable = tool_rpm
  []
  # Motor power in kW
  [power_kW]
    type = AverageNodalVariableValue
    variable = motor_power_kW
  []
  # Axial load in kN
  [force_kN]
    type = AverageNodalVariableValue
    variable = axial_load_kN
  []
  # Fraction of bead elements actively deposited
  [deposited_bead_pct]
    type = ElementAverageValue
    variable = is_deposited
    block = 'bead'
  []
  # Instantaneous physical rod height (mm)
  [rod_height_mm]
    type = ElementAverageValue
    variable = rod_height_mm
    block = 'rod'
  []
  # Cumulative consumed rod length (mm)
  [consumed_length_mm]
    type = ElementAverageValue
    variable = consumed_length_mm
    block = 'rod'
  []
  # Machine axial feed rate (mm/min)
  [feed_rate_mmpm]
    type = ElementAverageValue
    variable = axial_feed_rate_mmpm
    block = 'rod'
  []
  # Spindle torsional torque in N*m
  [spindle_torque_Nm]
    type = AverageNodalVariableValue
    variable = spindle_torque_Nm
  []
  # Traverse resistance force in N
  [traverse_force_N]
    type = ElementAverageValue
    variable = traverse_force_N
  []
  # Transverse / lateral asymmetry force in N
  [transverse_force_N]
    type = ElementAverageValue
    variable = transverse_force_N
  []
  # Zener-Hollomon parameter ln(Z) in active stir zone
  [ln_Zener_Hollomon]
    type = ElementAverageValue
    variable = zener_hollomon_lnZ
    block = 'bead'
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
  solve_type = PJFNK
  petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart'
  petsc_options_value = 'hypre boomeramg 50'
  line_search = 'none'

  nl_rel_tol = 1.0e-3
  nl_abs_tol = 1.0e-1
  l_tol = 1.0e-3
  l_max_its = 50
  nl_max_its = 25

  start_time = 0.0
  end_time = 48.0
  dt = 0.5
  dtmin = 1.0e-3
[]

[Outputs]
  exodus = true
  csv = true
  file_base = afsd_deposition_out
[]
