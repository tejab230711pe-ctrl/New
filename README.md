# Rotating Disk Friction Deposition (AFSD) — MOOSE Framework Simulation

## 1. Project Overview

This project provides a high-fidelity, multiphysics finite element simulation for **Rotating Disk Friction Deposition (Additive Friction Stir Deposition - AFSD)** of **AA5083 Aluminum Alloy**, converted from a legacy FreeFEM++ codebase ([`final.edp`](file:///home/teja/Videos/final.edp)) to the modern, parallel **MOOSE (Multiphysics Object Oriented Simulation Environment)** framework.

The simulation models the non-linear thermo-mechanical phenomena occurring during the deposition process:
- **Spindle rotation and frictional heat generation** at the rod-substrate interface.
- **Dynamic axial load servo control** (dwelling and plunging stages).
- **Temperature-dependent thermophysical and mechanical properties** for AA5083 alloy.
- **Solid-liquid phase change and latent heat release** using an apparent heat capacity (mushy zone) formulation.
- **Johnson-Cook viscoplasticity** (J2 Plasticity) with strain hardening, strain rate sensitivity, and thermal softening.
- **Mortar mechanical contact** between the rotating consumable rod and the substrate plate.
- **Arbitrary Lagrangian-Eulerian (ALE) mesh adaptation** to capture continuous material feed and rod consumption without mesh distortion.
- **Machine limit checks and thermodynamic energy balance validation**.

---

## 2. Complete File Locations & Directory Map

All codebase artifacts, source files, and input configurations are organized in the following locations:

### 2.1. Project Root Directory
* **Project Directory**: `/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6`
* **Workspace Directory**: `/home/teja/Videos`

### 2.2. Master File Index

| Component / Role | File Description | Absolute Path |
|---|---|---|
| **Original Reference** | Legacy FreeFEM++ script | [`/home/teja/Videos/final.edp`](file:///home/teja/Videos/final.edp) |
| **Build Configuration** | CMake configuration file | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/CMakeLists.txt`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/CMakeLists.txt) |
| **MOOSE Input File** | Complete physics input file | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/input/deposition.i`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/input/deposition.i) |
| **Material Properties (Header)** | AA5083 property UserObject header | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.h`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.h) |
| **Material Properties (Source)** | AA5083 property interpolation source | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.C`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.C) |
| **Mushy Zone Material (Header)** | Latent heat & effective $c_p, k$ header | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.h`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.h) |
| **Mushy Zone Material (Source)** | Latent heat & effective $c_p, k$ source | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.C`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.C) |
| **Friction Heat Source (Header)** | Interface friction heat kernel header | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.h`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.h) |
| **Friction Heat Source (Source)** | Interface friction heat kernel source | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.C`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.C) |
| **Normal Servo Preload (Header)** | Preload spring body force header | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.h`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.h) |
| **Normal Servo Preload (Source)** | Preload spring body force source | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.C`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.C) |
| **App Registration (Header)** | MOOSE Application header | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/RotatingDiskDepositionApp.h`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/RotatingDiskDepositionApp.h) |
| **App Registration (Source)** | MOOSE Application registry source | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/RotatingDiskDepositionApp.C`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/RotatingDiskDepositionApp.C) |
| **Documentation** | Workspace Documentation file | [`/home/teja/Videos/README.md`](file:///home/teja/Videos/README.md) |
| **Documentation (Artifact)** | Project Documentation file | [`/home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/README.md`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/README.md) |

---

## 3. Physics & Mathematical Formulation

### 3.1. Temperature-Dependent Material Properties (AA5083)
The simulation uses empirical data tables for AA5083 alloy, interpolated continuously as functions of temperature $T$ (in Kelvin):
- **Density $\rho(T)$** [$\text{kg/m}^3$]
- **Thermal Conductivity $k(T)$** [$\text{W/(m}\cdot\text{K)}$]
- **Specific Heat Capacity $c_p(T)$** [$\text{J/(kg}\cdot\text{K)}$]
- **Yield Stress $\sigma_y(T)$** [$\text{Pa}$]
- **Friction Coefficient $\mu(T)$** [dimensionless]

Beyond the liquidus temperature ($T_{\text{liq}} = 911.15\,\text{K}$), properties are smoothly clamped to prevent numerical singularities.

### 3.2. Mushy Zone & Latent Heat Formulation
Solidification and melting are handled via the **Apparent Heat Capacity Method**:
$$\text{Liquid Fraction } f(T) = \begin{cases} 
0, & T \le T_{\text{solidus}} \\
\frac{T - T_{\text{solidus}}}{T_{\text{liquidus}} - T_{\text{solidus}}}, & T_{\text{solidus}} < T < T_{\text{liquidus}} \\
1, & T \ge T_{\text{liquidus}}
\end{cases}$$

The effective thermal properties supplied to the transient heat conduction equation are:
$$c_{p,\text{eff}}(T) = c_p(T) + L_f \frac{df}{dT}$$
$$k_{\text{eff}}(T) = (1 - f) k(T) + f k_{\text{liquid}}$$
where $L_f$ is the latent heat of fusion ($3.9 \times 10^5\,\text{J/kg}$) and $k_{\text{liquid}}$ is the molten phase conductivity ($80.0\,\text{W/(m}\cdot\text{K)}$).

### 3.3. Johnson-Cook Viscoplasticity Law
Plastic deformation in the plasticized zone under high shear and temperature is governed by the Johnson-Cook model:
$$\sigma_{\text{flow}} = \left( A + B \varepsilon_p^n \right) \left[ 1 + C \ln\left(\frac{\dot{\varepsilon}_p}{\dot{\varepsilon}_0}\right) \right] \left[ 1 - \left(\frac{T - T_{\text{room}}}{T_{\text{melt}} - T_{\text{room}}}\right)^m \right]$$

| Parameter | Symbol | Value for AA5083 |
|---|---|---|
| Yield Stress parameter | $A$ | $255.21\,\text{MPa}$ |
| Hardening modulus | $B$ | $735.80\,\text{MPa}$ |
| Hardening exponent | $n$ | $1.075$ |
| Strain rate sensitivity | $C$ | $0.0028$ |
| Thermal softening exponent | $m$ | $0.654$ |
| Reference strain rate | $\dot{\varepsilon}_0$ | $1.0\,\text{s}^{-1}$ |

### 3.4. Frictional Heat Generation
Heat generation at the interface between the rotating consumable rod and the substrate is computed from frictional power dissipation:
$$\omega = \frac{2\pi \cdot \text{RPM}}{60} \quad [\text{rad/s}]$$
$$\text{Torque} = \frac{2}{3} \mu(T) \cdot P_{\text{contact}} \cdot \pi R^3$$
$$P_{\text{friction}} = \text{Torque} \cdot \omega$$
$$q_{\text{fric}} = \eta_{\text{gov}}(T) \cdot P_{\text{friction}}$$
where $P_{\text{contact}}$ is the coupled normal contact pressure, $R$ is the tool rod radius, and $\eta_{\text{gov}}(T) \in (0, 1]$ is the thermal governor efficiency factor.

### 3.5. Normal Servo / Preload Spring Force
To replicate the mechanical actuator during the dwell and plunging stages:
$$F_{\text{axial}}(t) = k_{\text{servo}} \cdot \text{ramp}(t) \cdot F_{\text{preload}}$$
where $\text{ramp}(t) = \min(1.0, t / t_{\text{ramp}})$ smoothly applies the axial force over the dwell ramp period.

### 3.6. Contact Mechanics & ALE Formulation
- **Mortar Contact**: Enforces normal non-penetration penalty contact between the bottom face of the rod and the top surface of the plate, outputting the contact pressure distribution.
- **ALE Mesh Modifier**: Dynamically displaces rod mesh coordinates along the $Z$-axis to account for material burn-off and continuous axial feed without mesh tangling.

---

## 4. C++ Source Classes & Implementation Details

1. **[`AA5083ThermalProperties`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.h)** (`UserObject`):
   - Implements piecewise linear interpolation for $T \in [-20^\circ\text{C}, 580^\circ\text{C}]$.
   - Supplies `rho(T)`, `k(T)`, `cp(T)`, `yieldStress(T)`, and `mu(T)` to all kernels and materials.

2. **[`MushyFraction`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.h)** (`Material`):
   - Calculates quadrature-point values of `mushy_fraction`, `dmush_dT`, `cp_eff`, and `k_eff`.
   - Directly feeds the effective conductivity and apparent heat capacity to the heat conduction equation.

3. **[`FrictionHeatSource`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.h)** (`Kernel`):
   - Couples the primary temperature variable `T` to the contact pressure `contact_pressure`.
   - Computes the residual contribution from rotational frictional shear dissipation.

4. **[`NormalServo`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.h)** (`Kernel`):
   - Couples displacement variable `Uz`.
   - Applies the time-dependent axial servo load in the negative $Z$ direction.

5. **[`RotatingDiskDepositionApp`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/RotatingDiskDepositionApp.h)** (`MooseApp`):
   - Registers all custom kernels, materials, and user objects with MOOSE's factory system.

---

## 5. Input File Specification ([`input/deposition.i`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/input/deposition.i))

The input file configures the complete execution pipeline:

- **`[GlobalParams]`**: Sets dimensions ($L_x = 150\,\text{mm}, L_y = 150\,\text{mm}, t_{\text{plate}} = 6\,\text{mm}, R_{\text{rod}} = 12.5\,\text{mm}, H_{\text{rod}} = 300\,\text{mm}$), process parameters ($\text{RPM} = 1200, F_{\text{preload}} = 5000\,\text{N}$), and mesh resolutions.
- **`[Mesh]`**: Two structured hexahedral blocks: `plate_mesh` and `rod_mesh`.
- **`[Variables]`**:
  - `T`: Temperature field ($K$).
  - `Uz`: Out-of-plane displacement ($m$).
  - `contact_pressure`: Contact normal pressure ($Pa$).
- **`[UserObject]`**: Instantiates `material_props` (`AA5083ThermalProperties`).
- **`[Material]`**: Instantiates `mushy_mat` (`MushyFraction`) and `jc_plasticity` (`J2Plasticity`).
- **`[Kernel]`**: Solves transient heat conduction (`HeatConduction`), friction heat (`FrictionHeatSource`), and axial loading (`NormalServo`).
- **`[Contact]`**: Mortar contact enforcement with penalty parameter.
- **`[MeshModifier]`**: `ALEMeshModifier` for mesh updates at `timestep_end`.
- **`[Executioner]`**: Transient time-stepper with time step $\Delta t = 0.25\,\text{s}$ and end time $t_{\text{final}} = 10.0\,\text{s}$.
- **`[Outputs]`**:
  - `output.e`: **Exodus II format** for 3D field visualization in ParaView.
  - CSV files matching the legacy FreeFEM schema.

---

## 6. Build & Compilation Instructions

### Prerequisites
- A working MOOSE installation (or MOOSE environment activated via `conda` / submodule).
- CMake $\ge 3.16$.
- Modern C++17 compatible compiler (`g++` or `clang++`).
- MPI library (`OpenMPI` or `MPICH`).

### Build Steps

```bash
# 1. Navigate to the project root directory
cd /home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6

# 2. Create and enter a build directory
mkdir -p build && cd build

# 3. Configure the build with CMake (specify MOOSE_DIR if not set in environment)
cmake .. -DMOOSE_DIR=$MOOSE_DIR

# 4. Compile the application executable in parallel
make -j$(nproc)
```

This will produce the executable: `RotatingDiskDepositionApp-opt` (or `RotatingDiskDepositionApp-devel`).

---

## 7. Running the Simulation

### Serial Execution
```bash
cd /home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/build
./RotatingDiskDepositionApp-opt -i ../input/deposition.i
```

### Parallel MPI Execution
```bash
mpirun -n 4 ./RotatingDiskDepositionApp-opt -i ../input/deposition.i
```

### Overriding Parameters from the Command Line
MOOSE allows overriding any variable defined in `[GlobalParams]` without modifying the `.i` file:
```bash
./RotatingDiskDepositionApp-opt -i ../input/deposition.i \
  GlobalParams/rpm=1500 \
  GlobalParams/dwellPreloadForce=6500.0 \
  GlobalParams/totalTime=25.0 \
  GlobalParams/dt=0.1
```

---

## 8. Output Files & Results Inspection

When executed, the simulation generates outputs in the run directory:

### 8.1. Generated CSV Files

| Output File | Location | Contents |
|---|---|---|
| `consumable_rod_history.csv` | [`/home/teja/Videos/consumable_rod_history.csv`](file:///home/teja/Videos/consumable_rod_history.csv) | Time-series of global metrics: Time, RPM, $T_{\text{max}}$, $T_{\text{avg}}$, axial feed rate, friction power, contact pressure. |
| `consumable_rod_snapshots.csv` | [`/home/teja/Videos/consumable_rod_snapshots.csv`](file:///home/teja/Videos/consumable_rod_snapshots.csv) | Detailed per-timestep snapshots of nodal state fields ($T, U_z, P_{\text{contact}}$). |
| `consumable_rod_spatial_frames.csv` | [`/home/teja/Videos/consumable_rod_spatial_frames.csv`](file:///home/teja/Videos/consumable_rod_spatial_frames.csv) | Geometric tracking data: rod center coordinates $(x, y)$, current rod height, and interface radius. |
| `consumable_rod_limit_violations.csv` | [`/home/teja/Videos/consumable_rod_limit_violations.csv`](file:///home/teja/Videos/consumable_rod_limit_violations.csv) | Safety logs flagging any exceeded machine thresholds (spindle limits, peak force, critical temp). |
| `heat_validation_summary.csv` | [`/home/teja/Videos/heat_validation_summary.csv`](file:///home/teja/Videos/heat_validation_summary.csv) | Energy conservation audit: $Q_{\text{fric}}$, $Q_{\text{latent}}$, and $Q_{\text{total}}$. |

### 8.2. 3D Field Visualization via Exodus (`output.e`)

The `output.e` Exodus file contains all spatial fields across time steps:
- **Temperature field $T(\mathbf{x}, t)$**: Visualize temperature contours, heat-affected zones (HAZ), and peak interface temperatures.
- **Displacement field $U_z(\mathbf{x}, t)$**: Observe rod compression, tool plunge, and substrate compliance.
- **Contact pressure $P_{\text{contact}}$**: Inspect pressure distribution across the circular friction footprint.
- **Equivalent Plastic Strain $\varepsilon_p$**: Assess shear deformation in the plasticized boundary layer.

#### Visualizing in ParaView:
1. Open **ParaView**:
   ```bash
   paraview output.e &
   ```
2. Click **Apply** in the Properties panel.
3. Select the variable from the top dropdown (`T`, `Uz`, `contact_pressure`, or `plastic_strain`).
4. (Optional) Apply filters:
   - **Warp By Vector**: Deform mesh with displacement fields.
   - **Clip / Slice**: Inspect cross-sectional temperature profiles through the center of the rod.
   - **Threshold**: Highlight regions above the solidus temperature ($T > T_{\text{solidus}}$).

---

## 9. Validation & Benchmark Comparison

To verify equivalence with the original FreeFEM++ results:

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot aspt

# Load datasets
moose_data = pd.read_csv('/home/teja/Videos/consumable_rod_history.csv')
freefem_data = pd.read_csv('/home/teja/Videos/freefem_history.csv')

# Plot comparison
plt.figure(figsize=(10, 6))
plt.plot(moose_data['time'], moose_data['T_max'], 'b-', label='MOOSE T_max')
plt.plot(freefem_data['time'], freefem_data['T_max'], 'r--', label='FreeFEM T_max')
plt.xlabel('Time (s)')
plt.ylabel('Maximum Temperature (K)')
plt.title('Thermal History Benchmark: MOOSE vs FreeFEM++')
plt.legend()
plt.grid(True)
plt.savefig('/home/teja/Videos/thermal_comparison.png', dpi=300)
plt.show()

# Energy balance check
heat_data = pd.read_csv('/home/teja/Videos/heat_validation_summary.csv')
q_diff = np.abs(heat_data['Q_total'] - (heat_data['Q_fric'] + heat_data['Q_latent']))
print(f"Max energy balance discrepancy: {q_diff.max():.4e} W")
```

---

## 10. Summary Table of Converted Features

| Feature | FreeFEM++ Implementation ([`final.edp`](file:///home/teja/Videos/final.edp)) | MOOSE Framework Equivalent |
|---|---|---|
| **Language** | FreeFEM domain-specific language | C++ (MOOSE Framework) + Input file ([`deposition.i`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/input/deposition.i)) |
| **Mesh Type** | 2D/3D surface and volume meshes | Hexahedral `GeneratedMesh` (plate & rod) |
| **Material Properties** | Interpolation macros / inline arrays | [`AA5083ThermalProperties`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/AA5083ThermalProperties.h) (`UserObject`) |
| **Phase Change** | Apparent heat capacity in weak form | [`MushyFraction`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/MushyFraction.h) (`Material`) |
| **Plasticity** | Johnson-Cook formulation in PDE | `J2Plasticity` with temperature-dependent yield |
| **Friction Heat** | Boundary flux integral | [`FrictionHeatSource`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/FrictionHeatSource.h) (`Kernel`) |
| **Axial Servo** | Penalty spring force term | [`NormalServo`](file:///home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/src/NormalServo.h) (`Kernel`) |
| **Contact** | Custom penalty interface formulation | `MortarContact` system |
| **Mesh Motion** | Manual coordinate re-meshing | `ALEMeshModifier` (`MeshModifier`) |
| **Outputs** | Formatted text CSV file writes | Built-in `CSV` outputs + `Exodus` (`output.e`) |
